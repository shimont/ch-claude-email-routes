#!/usr/bin/env python3
"""Assemble a routine prompt from policy fragments.

  render.py <routine>      print the assembled prompt (paste target)
  render.py --verify       assert every routine reproduces routines/*.prompt.txt byte-for-byte

--verify is the safety property of this repo: the fragment split is only ever a
relocation of text, never an edit. Any intended change to a routine shows up as a
fragment diff AND a matching change to the routines/*.prompt.txt baseline, so a
migration bug can never hide inside a behaviour change.
"""
import json, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFESTS = {p.stem.split('-', 1)[1].replace('daily-email', 'daily')
             .replace('4h-triage', 'triage').replace('deep-sent-scan', 'deep'): p
             for p in sorted((ROOT / 'policy').glob('*.json'))}


def render(routine):
    man = json.loads(MANIFESTS[routine].read_text())
    return ''.join((ROOT / 'policy' / 'fragments' / f'{k}.txt').read_text()
                   for k in man['fragments']), man


def verify():
    ok = True
    for routine, path in sorted(MANIFESTS.items()):
        out, man = render(routine)
        baseline = (ROOT / man['source_of_truth']).read_text()
        match = out == baseline
        ok &= match
        print(f"  {routine:7s} {len(out):6d} ch  "
              f"{'OK  matches ' + man['source_of_truth'] if match else 'MISMATCH'}")
    print('\nall routines reproduce their baseline byte-for-byte' if ok
          else '\nFAILED - fragments do not reproduce the baseline')
    return 0 if ok else 1


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] == '--verify':
        sys.exit(verify())
    text, _ = render(sys.argv[1])
    sys.stdout.write(text)
