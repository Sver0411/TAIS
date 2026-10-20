#!/usr/bin/env python3
"""Independent v1 consumer: one hex-encoded byte frame per stdin line.

Hex/newline is an inspection harness representation, not the wire protocol.
No sender envelopes, labels, scheduler or transmission IDs are accepted.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from tais.core_stream import CoreReceiver
from tais.wire_codec import LAYOUTS


def main():
    """Consume inspection hex lines into a fresh receiver and exclusively write outputs.

    Invalid hex text is counted separately from invalid binary frames. No
    sender journal or truth is available to reconstruct omitted transitions."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--layout', type=int, choices=LAYOUTS, default=1)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args();a.out.mkdir(parents=True, exist_ok=False)
    receiver = CoreReceiver(a.layout);bad_text = 0
    with (a.out/'received.jsonl').open('x') as f:
        for line, text in enumerate(sys.stdin, 1):
            if not text.strip():continue
            try:
                frame = bytes.fromhex(text.strip())
            except ValueError:
                bad_text += 1;entry = dict(line=line,status='invalid_hex',envelope=None)
            else:
                entry = dict(line=line,frame_bytes=len(frame),**receiver.receive(frame))
            output = json.dumps(entry, sort_keys=True, allow_nan=False)
            f.write(output+'\n');f.flush();print(output, flush=True)
    summary = dict(receiver=dict(receiver.counts),invalid_text_lines=bad_text,
                   latest=receiver.latest,wire_version=1,layout_id=a.layout,
                   scope='independent local consumer; hex framing is inspection only')
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')


if __name__ == '__main__':main()
