"""Continuous GateOnly sender and independent stateless-v1 local receiver.

No labels, trace object, future values, confirmation rule or Wire v2 lives here.
The transport is an in-process byte-frame simulator, not a radio or MQTT client.
"""
from collections import Counter, deque
from copy import deepcopy
from dataclasses import asdict
import json
import math

from .scheduler import Scheduler
from .wire_codec import (LAYOUTS, WireError, decode, encode,
                         envelope_from_record, validate_layout)


FLAG_NAMES = ((1, 'RANGE'), (2, 'STUCK'), (4, 'SPIKE'),
              (8, 'DRIFT'), (16, 'MISSING'))


def flags_text(flags):
    names = [name for bit, name in FLAG_NAMES if flags & bit]
    unknown = flags & ~31
    if unknown:
        names.append(hex(unknown))
    return '|'.join(names) or 'NONE'


def timestamp(value):
    """Validate source time in seconds against the C11 millisecond range.

    Reject booleans, nonfinite values and negatives; ordering is checked by push()."""
    if (type(value) not in (int, float) or not math.isfinite(value)
            or value < 0 or not math.isfinite(value * 1000)
            or round(value * 1000) > (1 << 64) - 1):
        raise ValueError('timestamp must be nonnegative seconds within C11 uint64 milliseconds')
    return value


class CoreSender:
    """One source tick at a time; skip values until the unchanged policy is due."""

    def __init__(self, cfg, layout_id=1):
        self.names = validate_layout(cfg['channels'], layout_id)
        self.layout_id = layout_id
        self.scheduler = Scheduler(deepcopy(cfg), confirmation=False, multiplier=1.0)
        self.next_sample = 0
        self.last_source = -1
        self.last_sample = None
        self.last_upload = None
        self.last_frame_bytes = 0
        self.counts = Counter(source_rows=0, samples=0, uploads=0, binary_bytes=0)
        self.health_counts = Counter()
        self._open = dict.fromkeys(self.names, False)
        self._sent = dict.fromkeys(self.names, False)

    def push(self, row):
        """Consume one strictly increasing source row; return None before sampling is due.

        Only timestamps are read on skipped rows. On a sampled row, update health
        and event state, then optionally encode a complete Binary v1 snapshot.
        The result contains the local record, first-upload reports and optional
        frame/envelope; these local reports do not prove receiver delivery.
        Sparse inputs use the first row at or after the deadline, without filling.
        Invalid time or unsupported measurement types raise ValueError."""
        t = timestamp(row['timestamp'])
        if t <= self.last_source:
            raise ValueError('source timestamps must strictly increase; no sorting or filling')
        self.last_source = t
        self.counts['source_rows'] += 1
        if t < self.next_sample - 1e-9:
            return None
        values = {n: row[n] for n in self.names}
        for value in values.values():
            if value is not None and (type(value) not in (int, float)
                                      or type(value) is int and not -(1 << 63) <= value < (1 << 63)):
                raise ValueError('measurement must be a number or null within the v1 integer range')
        d = self.scheduler.update(t, values)
        # Preserve the original replay record and the exact envelope adapter.
        record = {"timestamp": t, "values": values, "payload_bytes": 0, **asdict(d)}
        reports = []
        for name in self.names:
            if d.active[name]:
                if not self._open[name]:
                    self._open[name] = True
                    self._sent[name] = False
                if d.upload and not self._sent[name]:
                    reports.append(dict(channel=name, start_s=t, end_s=t,
                                        event_type='detected'))
                    self._sent[name] = True
            else:
                self._open[name] = False
        self.next_sample = t + d.interval
        self.counts['samples'] += 1
        for name, health in d.health.items():
            self.health_counts[name + ':' + health['state']] += 1
        self.last_sample = record
        frame = None
        envelope = None
        if d.upload:
            envelope = envelope_from_record(record, self.layout_id)
            frame = encode(envelope, self.layout_id)
            record['payload_bytes'] = len(json.dumps(
                envelope, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
            self.counts['uploads'] += 1
            self.counts['binary_bytes'] += len(frame)
            self.last_frame_bytes = len(frame)
            self.last_upload = t
        return dict(record=record, reports=reports, envelope=envelope, frame=frame)

    def close(self):
        """Release owned C health contexts; safe to call repeatedly."""
        for trust in self.scheduler.trust.values():
            trust.close()


class CoreReceiver:
    """Knows only provisioned layout + received bytes. Never holds guessed data."""

    def __init__(self, layout_id=1):
        validate_layout(LAYOUTS.get(layout_id, ()), layout_id)
        self.layout_id = layout_id
        self.latest = None
        self._latest_frame = None
        self.counts = Counter(received=0, received_bytes=0, decoded=0, updates=0,
                              corrupt=0, out_of_order=0, duplicate=0, conflict=0)
        self.timeline = deque(maxlen=12)

    def receive(self, frame):
        """Decode a frame and apply it only if its timestamp advances receiver state.

        Return status, decoded envelope and sampled state transitions. Invalid
        frames produce an error result; stale, duplicate or conflicting frames
        never roll back latest. A new snapshot restores current state only,
        not intermediate events lost in transit. Score-only changes are retained
        in latest but are not entries in the bounded transition timeline."""
        self.counts['received'] += 1
        self.counts['received_bytes'] += len(frame)
        try:
            envelope = decode(frame, expected_layout_id=self.layout_id)
        except WireError as error:
            self.counts['corrupt'] += 1
            return dict(status='invalid', error=str(error), envelope=None, transitions=[])
        self.counts['decoded'] += 1
        t = envelope['timestamp']
        previous = self.latest
        if previous is not None and t <= previous['timestamp']:
            status = ('out_of_order' if t < previous['timestamp'] else
                      'duplicate' if bytes(frame) == self._latest_frame else 'conflict')
            self.counts[status] += 1
            return dict(status=status, envelope=envelope, transitions=[])
        changes = []
        for name, health in envelope['health'].items():
            old = previous['health'].get(name) if previous else None
            if (old is None or (old['state'], old['flags']) != (health['state'], health['flags'])
                    or previous['environment_active'][name] != envelope['environment_active'][name]):
                change = dict(timestamp=t, channel=name, state=health['state'],
                              flags=health['flags'], flags_text=flags_text(health['flags']),
                              event_active=envelope['environment_active'][name],
                              recovery=bool(old and (old['flags'] or old['state'] != 'HEALTHY')
                                            and health['state'] == 'HEALTHY' and not health['flags']))
                changes.append(change)
                self.timeline.append(change)
        self.latest = envelope
        self._latest_frame = bytes(frame)
        self.counts['updates'] += 1
        return dict(status='updated', envelope=envelope, transitions=changes)


class LocalLink:
    """Deterministic controlled frame failures; no feedback to sender decisions.

    Harness IDs are journal metadata, not v1 fields or receiver sequence numbers.
    Pair reversal delays one frame until the next; EOF flush releases an odd tail.
    """

    def __init__(self, receiver, emit, drop_every=0, corrupt_every=0, reorder_pairs=False):
        if any(type(x) is not int or x < 0 for x in (drop_every, corrupt_every)):
            raise ValueError('link periods must be nonnegative integers')
        self.receiver, self.emit = receiver, emit
        self.drop_every, self.corrupt_every = drop_every, corrupt_every
        self.reorder_pairs = reorder_pairs
        self.counts = Counter(sent=0, sent_bytes=0, dropped=0, altered=0)
        self.pending = None

    def _deliver(self, item):
        tx_id, frame = item
        outcome = self.receiver.receive(frame)
        self.emit(dict(kind='rx', harness_tx_id=tx_id, frame_bytes=len(frame), **outcome))

    def send(self, frame):
        """Count an emission and apply configured loss, corruption or pair reversal.

        Deliveries call the receiver and emit journal records synchronously.
        There is no acknowledgement, retry or feedback into the sampling policy."""
        self.counts['sent'] += 1
        self.counts['sent_bytes'] += len(frame)
        tx_id = self.counts['sent']
        if self.drop_every and tx_id % self.drop_every == 0:
            self.counts['dropped'] += 1
            self.emit(dict(kind='link_drop', harness_tx_id=tx_id))
            return
        if self.corrupt_every and tx_id % self.corrupt_every == 0:
            frame = bytes([frame[0] ^ 1]) + frame[1:]
            self.counts['altered'] += 1
            self.emit(dict(kind='link_corrupt', harness_tx_id=tx_id))
        item = tx_id, frame
        if not self.reorder_pairs:
            self._deliver(item)
        elif self.pending is None:
            self.pending = item
        else:
            self._deliver(item)
            self._deliver(self.pending)
            self.pending = None

    def flush(self):
        """Deliver the held tail frame after pair reversal at end of input."""
        if self.pending is not None:
            self._deliver(self.pending)
            self.pending = None


def render(sender, receiver, label):
    """Bounded terminal dashboard; retained full history is the external journal."""
    s = sender.last_sample
    if s is None:
        return label + '\nWaiting for first sample.\n'
    r = receiver.latest
    lines = ['TAIS CORE | GateOnly | Stateless Binary v1 | ' + label,
             f"SOURCE clock={sender.last_source}s rows={sender.counts['source_rows']} | "
             f"SENDER sampled={s['timestamp']}s next_due={sender.next_sample}s",
             f"samples={sender.counts['samples']} uploads={sender.counts['uploads']} "
             f"sample_upload={s['upload']} sample_frame={sender.last_frame_bytes if s['upload'] else 0}B "
             f"last_tx={sender.last_upload}s last_frame={sender.last_frame_bytes}B "
             f"total_application_bytes={sender.counts['binary_bytes']}",
             'SENDER (local state; not automatically known by receiver):']
    for name, h in s['health'].items():
        lines.append(f"  {name}: value={s['values'][name]} {h['state']} score={h['score']} "
                     f"flags={h['flags']}({flags_text(h['flags'])}) event={s['active'][name]}")
    lines.append(f"RECEIVER decoded={receiver.counts['decoded']} invalid={receiver.counts['corrupt']} "
                 f"stale_frames={receiver.counts['out_of_order']} duplicate={receiver.counts['duplicate']}")
    if r:
        lines.append(f"  latest_received_sample={r['timestamp']}s age={sender.last_source-r['timestamp']}s "
                     '(no filling of dropped frames)')
        for name, h in r['health'].items():
            lines.append(f"  {name}: value={r['values'][name]} {h['state']} score={h['score']} "
                         f"flags={h['flags']}({flags_text(h['flags'])}) event={r['environment_active'][name]}")
    else:
        lines.append('  NO RECEIVED STATE')
    lines.append('RECEIVED HEALTH TIMELINE (suspected faults/recovery, last 12; full JSONL on disk):')
    for e in receiver.timeline:
        lines.append(f"  {e['timestamp']}s {e['channel']} {e['state']} {e['flags_text']} event={e['event_active']}"
                     + (' RECOVERED' if e['recovery'] else ''))
    return '\n'.join(lines) + '\n'
