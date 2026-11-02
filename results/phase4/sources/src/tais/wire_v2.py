"""Stateful lossless health transport, explicit per-device continuity and recovery.

No ACKs, retries, implicit device IDs, timestamps scaling, or detector imports.
KEY payloads are intact v1 frames. Sender history is emitted envelopes only.
"""
from copy import deepcopy
from dataclasses import dataclass
import struct
import zlib
from . import wire_codec as v1

VERSION = 2
FIELDS = ('state', 'score', 'flags')
MAX_FRAME_BYTES = 85
MIN_FRAME_BYTES = 14
WireError = v1.WireError


def _id(value, bits, name):
    return v1._integer(value, 1, (1 << bits)-1, name)


def _pack(layout, control, device, session, sequence, payload):
    body = (b'TW'+bytes((VERSION,layout,control))+v1._uvar(device)
            +v1._uvar(session)+v1._uvar(sequence)+payload)
    return body+struct.pack('>I',zlib.crc32(body))


def _delta(envelope, previous, names):
    kind, time_data = v1._number(envelope['timestamp'], timestamp=True)
    control = kind << 6
    bitmap = 0
    values, changes = bytearray(), bytearray()
    for i,name in enumerate(names):
        kind,data = v1._number(envelope['values'][name])
        control |= kind << (i*2)
        control |= int(envelope['environment_active'][name]) << (4+i)
        values.extend(data)
        if name in envelope['health']:
            bitmap |= 1 << (6+i)
            now = envelope['health'][name]
            before = (previous or {}).get(name)
            for j,field in enumerate(FIELDS):
                if before is None or now[field] != before[field]:
                    bitmap |= 1 << (i*3+j)
                    value=now[field]
                    changes.extend(v1._uvar(value) if field=='flags' else
                                   bytes((v1.STATES.index(value) if field=='state' else value,)))
    return control, time_data+bytes((bitmap,))+values+changes


class Sender:
    """Encode/commit each local emission; delivery is never inferred.

    Caller must persist monotonically increasing session IDs across reboot.
    encode() advances only after validation; discarding its return is a loss.
    """
    def __init__(self, device_id=1, session_id=1, period=16, layout_id=1):
        self.device_id=_id(device_id,32,'device')
        self.session_id=_id(session_id,64,'session')
        self.names=v1.validate_layout(v1._layout(layout_id),layout_id)
        self.layout_id=layout_id
        self.period=v1._integer(period,1,65535,'period')
        self._seq=0
        self._previous=None
        self.last_accounting=None

    def restart(self, session_id):
        _id(session_id,64,'session')
        if session_id <= self.session_id:
            raise WireError('Restart requires a strictly greater persisted session ID')
        self.session_id=session_id
        self._seq=0
        self._previous=None
        self.last_accounting=None

    def encode(self, envelope):
        if self._seq >= 1 << 32:
            raise WireError('Sequence exhausted; allocate a fresh session, never wrap')
        full=v1.encode(envelope,self.layout_id)  # exact original contract validation
        control,delta=_delta(envelope,self._previous,self.names)
        hypothetical=_pack(self.layout_id,control,self.device_id,self.session_id,self._seq,delta)
        key=self._previous is None or self._seq % self.period == 0
        payload=full if key else delta
        frame=_pack(self.layout_id,0x80 if key else control,self.device_id,self.session_id,self._seq,payload)
        assert MIN_FRAME_BYTES <= len(frame) <= MAX_FRAME_BYTES
        self.last_accounting=dict(sequence=self._seq,session=self.session_id,keyframe=key,
                                  bytes=len(frame),outer_header_crc_bytes=len(frame)-len(payload),
                                  identity_sequence_bytes=len(v1._uvar(self.device_id))+len(v1._uvar(self.session_id))+len(v1._uvar(self._seq)),
                                  key_refresh_premium=len(frame)-len(hypothetical) if key else 0)
        self._previous=deepcopy(envelope['health'])
        self._seq+=1
        return frame


@dataclass(frozen=True)
class Parsed:
    device_id: int
    session_id: int
    sequence: int
    layout_id: int
    keyframe: bool
    base: dict
    present: tuple
    changes: dict
    self_contained: bool
    wire: bytes


def parse(frame):
    """Verify structure/integrity without accessing or mutating receiver state."""
    if not isinstance(frame,(bytes,bytearray,memoryview)):
        raise WireError('Frame must be bytes-like')
    length=frame.nbytes if isinstance(frame,memoryview) else len(frame)
    if not MIN_FRAME_BYTES <= length <= MAX_FRAME_BYTES:
        raise WireError('Invalid v2 frame length')
    frame=bytes(frame);body,crc=frame[:-4],frame[-4:]
    if struct.pack('>I',zlib.crc32(body))!=crc:
        raise WireError('V2 CRC mismatch')
    r=v1._Reader(body)
    if r.take(2)!=b'TW' or r.byte()!=VERSION:
        raise WireError('Unknown wire magic/version')
    layout=r.byte();names=v1._layout(layout);control=r.byte()
    device=_id(r.varint(32),32,'device');session=_id(r.varint(64),64,'session');sequence=r.varint(32)
    key=bool(control & 0x80)
    if key:
        if control!=0x80:
            raise WireError('Reserved KEY control bits')
        base=v1.decode(r.take(len(body)-r.pos),expected_layout_id=layout)
        changes=deepcopy(base['health']);present=tuple(n for n in names if n in changes)
        independent=True
    else:
        if len(names)==1 and control & (0b1100|0b100000):
            raise WireError('Unused measurement/event control bits')
        timestamp=r.floating() if control & 0x40 else r.varint(64)
        if timestamp < 0:
            raise WireError('Negative timestamp')
        bitmap=r.byte();allowed=sum((7<<(3*i))|(1<<(6+i)) for i in range(len(names)))
        if bitmap & ~allowed:
            raise WireError('Reserved health bits')
        values={}
        for i,name in enumerate(names):
            kind=(control >> (i*2)) & 3
            if kind==0:values[name]=None
            elif kind==1:values[name]=r.floating()
            elif kind==2:
                number=r.varint(64);values[name]=(number>>1)^-(number&1)
            else:raise WireError('Invalid measurement kind')
        changes={};present=[];independent=True
        for i,name in enumerate(names):
            fields=(bitmap>>(i*3))&7
            if not bitmap & (1<<(6+i)):
                if fields:raise WireError('Changed fields for an absent health channel')
                continue
            present.append(name);changes[name]={};independent &= fields==7
            for j,field in enumerate(FIELDS):
                if fields & (1<<j):
                    value=r.varint(32) if field=='flags' else r.byte()
                    if field=='state':
                        if value>=len(v1.STATES):raise WireError('Invalid health state')
                        value=v1.STATES[value]
                    if field=='score' and value>100:raise WireError('Invalid health score')
                    changes[name][field]=value
        base={'timestamp':timestamp,'values':values,
              'environment_active':{n:bool(control&(1<<(4+i))) for i,n in enumerate(names)},'health':None}
    if r.pos!=len(body):raise WireError('Trailing v2 bytes')
    return Parsed(device,session,sequence,layout,key,base,tuple(present),changes,bool(independent),frame)


@dataclass(frozen=True)
class Received:
    status: str
    device_id: int
    session_id: int
    sequence: int
    keyframe: bool
    envelope: dict | None = None
    gap: int = 0
    recovered: bool = False
    new_session: bool = False


@dataclass
class _Cache:
    session: int
    highest: int = -1
    applied: int | None = None
    health: dict | None = None
    last_wire: bytes | None = None
    synced: bool = False


class Receiver:
    """Fail-closed stream cache, bounded by explicitly provisioned devices.

    A reset erases volatile high-water marks too; it is not anti-replay security.
    """
    def __init__(self, layouts=None):
        self.layouts=dict({1:1} if layouts is None else layouts)
        if not self.layouts:raise WireError('At least one provisioned device is required')
        for device,layout in self.layouts.items():
            _id(device,32,'device');v1._layout(layout)
        self._cache={}

    def reset(self):
        self._cache.clear()

    def receive(self, wire):
        p=parse(wire)  # corruption/config rejection cannot poison a known stream
        if p.device_id not in self.layouts or p.layout_id!=self.layouts[p.device_id]:
            raise WireError('Unprovisioned device or frame/config layout mismatch')
        cache=self._cache.get(p.device_id)
        def result(status,**kw):
            return Received(status,p.device_id,p.session_id,p.sequence,p.keyframe,**kw)
        if cache is not None and p.session_id < cache.session:
            return result('STALE_SESSION')
        new=cache is None or p.session_id > cache.session
        was_known=cache is not None
        if new:
            cache=_Cache(p.session_id);self._cache[p.device_id]=cache
        if p.sequence < cache.highest:
            return result('STALE')
        if p.sequence==cache.highest:
            if p.wire==cache.last_wire:return result('DUPLICATE')
            cache.synced=False;cache.health=None;cache.applied=None
            return result('CONFLICT')
        gap=p.sequence-cache.highest-1
        usable=cache.synced and cache.applied==p.sequence-1 and gap==0
        had_dependency_loss=not usable and (cache.highest>=0 or p.sequence>0 or was_known)
        cache.highest=p.sequence;cache.last_wire=p.wire
        if not usable:
            cache.synced=False;cache.health=None;cache.applied=None
        if not p.self_contained and not usable:
            return result('WAIT_KEYFRAME',gap=gap,new_session=new)
        health={}
        for name in p.present:
            previous={} if p.self_contained else (cache.health or {}).get(name,{})
            h={**previous,**p.changes[name]}
            if set(h)!=set(FIELDS):
                cache.synced=False;cache.health=None;cache.applied=None
                raise WireError('New health entry must supply all fields')
            health[name]=h
        envelope={**p.base,'health':health}
        # A fully reconstructed business object must meet the original v1 schema.
        v1.encode(envelope,p.layout_id)
        cache.health=deepcopy(health);cache.applied=p.sequence;cache.synced=True
        return result('KEYFRAME' if p.keyframe else 'DELTA',envelope=envelope,
                      gap=gap,recovered=had_dependency_loss,new_session=new)
