"""Versioned, stateless, lossless upload envelopes; no scheduling dependencies.

Custom application format. A CRC is accidental-error detection, not a MAC.
Integers retain their type; finite floats retain all IEEE754 binary64 bits.
The explicit registry is shared configuration, not per-frame string metadata.
"""
from collections.abc import Mapping
import json
import math
import struct
from types import MappingProxyType
import zlib

VERSION = 1
MAGIC = b"TW"
LAYOUTS = MappingProxyType({1: ("temperature", "humidity"),
                          2: ("temperature",), 3: ("humidity",)})
STATES = ("HEALTHY", "DEGRADED", "FAULT")
MAX_FRAME_BYTES = 56
MIN_FRAME_BYTES = 13


class WireError(ValueError):
    """Invalid input or frame; nothing is truncated, repaired or ignored."""


def _layout(layout_id):
    if type(layout_id) is not int or layout_id not in LAYOUTS:
        raise WireError("Unknown layout ID")
    return LAYOUTS[layout_id]


def validate_layout(channels, layout_id=1):
    """Validate exact configured channel identity/order against the registry."""
    names = _layout(layout_id)
    if tuple(channels) != names:
        raise WireError("Configured channel identity/order does not match layout")
    return names


def layout_descriptor(layout_id=1):
    """Optional provisioning description; not transmitted by this codec."""
    return json.dumps({"version": VERSION, "layout_id": layout_id,
                       "channels": _layout(layout_id)}, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _integer(value, low, high, field):
    if type(value) is not int or not low <= value <= high:
        raise WireError(f"{field} must be an integer in [{low}, {high}]")
    return value


def _uvar(value):
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return out


def _map(value, allowed, exact, field):
    if not isinstance(value, Mapping):
        raise WireError(f"{field} must be a mapping")
    keys = set(value)
    if not keys <= set(allowed) or (exact and keys != set(allowed)):
        raise WireError(f"Unexpected or missing {field} keys")
    return value


def _number(value, timestamp=False):
    """Encode null, binary64 or signed ZigZag integer while preserving numeric type.

    Timestamp integers are unsigned and retain caller units; this codec never
    rescales seconds to milliseconds. Booleans and nonfinite floats are rejected."""
    if type(value) is int:
        if timestamp:
            _integer(value, 0, (1 << 64)-1, "timestamp")
            return 0, _uvar(value)
        _integer(value, -(1 << 63), (1 << 63)-1, "measurement")
        return 2, _uvar((value << 1) ^ (value >> 63))
    if type(value) is float and math.isfinite(value) and (not timestamp or value >= 0):
        return 1, struct.pack(">d", value)
    if value is None and not timestamp:
        return 0, b""
    raise WireError("Expected a supported finite number (or null measurement)")


def encode(envelope, layout_id=1):
    """Encode the complete four-field envelope as an independent v1 byte frame.

    Channel order is provisioned by layout_id. Values and event booleans must
    cover every channel; health may omit channels, distinctly from a null
    measurement. Invalid types, ranges or schema raise WireError. len(return)
    is the measured application byte cost, excluding real network overhead."""
    names = _layout(layout_id)
    _map(envelope, ("timestamp", "values", "environment_active", "health"), True, "envelope")
    values = _map(envelope["values"], names, True, "values")
    active = _map(envelope["environment_active"], names, True, "environment_active")
    health = _map(envelope["health"], names, False, "health")
    time_kind, time_data = _number(envelope["timestamp"], timestamp=True)
    # Two type bits per value; independent masks retain event and health presence.
    kinds = active_mask = health_mask = 0
    value_data = bytearray()
    health_data = bytearray()
    for i, name in enumerate(names):
        kind, data = _number(values[name])
        kinds |= kind << (2*i)
        value_data.extend(data)
        if type(active[name]) is not bool:
            raise WireError("environment_active must contain exact booleans")
        active_mask |= int(active[name]) << i
        if name in health:
            h = _map(health[name], ("state", "score", "flags"), True, "health entry")
            if type(h["state"]) is not str or h["state"] not in STATES:
                raise WireError("Unknown health state")
            score = _integer(h["score"], 0, 100, "health score")
            flags = _integer(h["flags"], 0, (1 << 32)-1, "health flags")
            health_mask |= 1 << i
            health_data.extend((STATES.index(h["state"]), score))
            health_data.extend(_uvar(flags))
    body = (MAGIC + bytes((VERSION, layout_id, time_kind)) + time_data
            + bytes((kinds, active_mask, health_mask)) + value_data + health_data)
    frame = body + struct.pack(">I", zlib.crc32(body))
    assert MIN_FRAME_BYTES <= len(frame) <= MAX_FRAME_BYTES
    return frame


class _Reader:
    def __init__(self, body):
        self.body = body
        self.pos = 0

    def take(self, count):
        if self.pos + count > len(self.body):
            raise WireError("Truncated frame field")
        out = self.body[self.pos:self.pos+count]
        self.pos += count
        return out

    def byte(self):
        return self.take(1)[0]

    def varint(self, bits):
        """Read a bounded canonical unsigned base-128 integer or raise WireError.

        Reject redundant high zero groups so one integer has one wire encoding."""
        value = 0
        for i in range((bits+6)//7):
            byte = self.byte()
            value |= (byte & 127) << (i*7)
            if not byte & 128:
                if value >= 1 << bits or (i and byte == 0):
                    raise WireError("Out-of-range or noncanonical varint")
                return value
        raise WireError("Overlong varint")

    def floating(self):
        value = struct.unpack(">d", self.take(8))[0]
        if not math.isfinite(value):
            raise WireError("Nonfinite on-wire float; use explicit null")
        return value


def decode(frame, expected_layout_id=1):
    """Validate framing, schema and CRC, then return a complete business object.

    No previous frame or sender object is needed. Reject unknown layouts,
    noncanonical integers, truncation and trailing data with WireError. A valid
    later snapshot restores only its current state; the format has no sequence
    numbers, retransmission or mechanism to reconstruct lost event history."""
    _layout(expected_layout_id)
    if not isinstance(frame, (bytes, bytearray, memoryview)):
        raise WireError("Frame must be bytes-like")
    length = frame.nbytes if isinstance(frame, memoryview) else len(frame)
    if not MIN_FRAME_BYTES <= length <= MAX_FRAME_BYTES:
        raise WireError("Invalid frame length")
    frame = bytes(frame)
    body, crc = frame[:-4], frame[-4:]
    if struct.pack(">I", zlib.crc32(body)) != crc:
        raise WireError("CRC mismatch")
    reader = _Reader(body)
    if reader.take(2) != MAGIC:
        raise WireError("Invalid magic")
    if reader.byte() != VERSION:
        raise WireError("Unsupported wire version")
    layout_id = reader.byte()
    names = _layout(layout_id)
    if layout_id != expected_layout_id:
        raise WireError("Frame/config layout mismatch")
    time_kind = reader.byte()
    if time_kind == 0:
        timestamp = reader.varint(64)
    elif time_kind == 1:
        timestamp = reader.floating()
        if timestamp < 0:
            raise WireError("Negative timestamp")
    else:
        raise WireError("Invalid timestamp kind")
    kinds, active, present = reader.byte(), reader.byte(), reader.byte()
    if kinds >> (2*len(names)) or (active | present) >> len(names):
        raise WireError("Reserved mask bits set")
    values, health = {}, {}
    for i, name in enumerate(names):
        kind = (kinds >> (2*i)) & 3
        if kind == 0:
            values[name] = None
        elif kind == 1:
            values[name] = reader.floating()
        elif kind == 2:
            unsigned = reader.varint(64)
            values[name] = (unsigned >> 1) ^ -(unsigned & 1)
        else:
            raise WireError("Invalid measurement kind")
    for i, name in enumerate(names):
        if present & (1 << i):
            state, score = reader.byte(), reader.byte()
            if state >= len(STATES) or score > 100:
                raise WireError("Invalid health state/score")
            health[name] = {"state": STATES[state], "score": score, "flags": reader.varint(32)}
    if reader.pos != len(body):
        raise WireError("Trailing data")
    return {"timestamp": timestamp, "values": values,
            "environment_active": {n: bool(active & (1 << i)) for i, n in enumerate(names)},
            "health": health}


def envelope_from_record(record, layout_id=1):
    """Rebuild exactly replay.py's sent envelope, not its internal Decision log.

    Only here do nonfinite sampled values become JSON-null semantics, as in
    the original replay. encode() itself rejects nonfinite semantic values.
    """
    names = _layout(layout_id)
    raw = _map(record["values"], names, True, "record values")
    values = {}
    for name in names:
        v = raw[name]
        if v is not None and type(v) not in (int, float):
            raise WireError("Invalid sampled measurement type")
        if type(v) is int:
            _integer(v, -(1 << 63), (1 << 63)-1, "sampled measurement")
        values[name] = v if v is not None and math.isfinite(v) else None
    return {"timestamp": record["timestamp"], "values": values,
            "environment_active": dict(record["active"]),
            "health": {n: dict(h) for n, h in record["health"].items()}}
