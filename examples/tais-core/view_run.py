#!/usr/bin/env python3
"""View an actual journal's received timeline; never re-run or infer a policy."""
import argparse
from collections import deque
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--tail', type=int, default=50)
    a = p.parse_args()
    if a.tail < 1:
        p.error('tail must be positive')
    lines = deque(maxlen=a.tail)
    with (a.run/'journal.jsonl').open() as f:
        for text in f:
            e = json.loads(text)
            if e['kind'] == 'rx':
                for c in e['transitions']:
                    lines.append(f"{c['timestamp']:>8}s {c['channel']:<12} {c['state']:<8} "
                                 f"score={e['envelope']['health'][c['channel']]['score']} "
                                 f"flags={c['flags_text']} event={c['event_active']}"
                                 + (' RECOVERED' if c['recovery'] else ''))
                if e['status'] != 'updated':
                    lines.append(f"RX {e['status']} harness_tx={e['harness_tx_id']}")
            elif e['kind'] in ('link_drop', 'link_corrupt', 'error'):
                lines.append(json.dumps(e))
    print(json.loads((a.run/'manifest.json').read_text())['input_label'])
    print('\n'.join(lines))
    print((a.run/'summary.json').read_text(), end='')


if __name__ == '__main__':
    main()
