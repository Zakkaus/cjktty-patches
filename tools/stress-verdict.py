#!/usr/bin/env python3
"""Count real kernel findings, ignoring the shell's echo of the grep command."""
import re
import sys
from pathlib import Path

raw = Path(sys.argv[1]).read_bytes().decode("utf-8", "replace")
clean = re.sub(r'\x1b\][0-9;]*;[^\x1b]*\x1b\\|\x1b\[[0-9;?]*[A-Za-z]|\r', '', raw)


def between(a, b):
    out = []
    for seg in clean.split(a)[1:]:
        for line in seg.split(b)[0].splitlines():
            if line.strip() and 'grep -E' not in line and not line.lstrip().startswith('echo '):
                out.append(line)
    return out


bad = [l for l in between("BADSTART", "BADEND")
       if re.search(r'KASAN|BUG:|WARNING:|recursive locking', l)]
leak = [l for l in between("LEAKSTART", "LEAKEND") if 'unreferenced object' in l]
for l in bad[:8] + leak[:8]:
    print("  ", l[:140])
print(f"dmesg findings {len(bad)}, kmemleak objects {len(leak)}")
sys.exit(1 if (bad or leak) else 0)
