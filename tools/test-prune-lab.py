#!/usr/bin/env python3
"""Exercise prune-lab.py against a fixture lab directory."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile


SCRIPT = Path(__file__).resolve().parent / "prune-lab.py"
DIRECTORIES = [
    "linux-6.12.117", "linux-6.12.119", "test-6.12.117", "out-6.12.117",
    "linux-7.3.5", "linux-7.3.6", "system-7.3.5", "out-system-7.3.6", "port-7.3.6",
    "linux-7.4-rc3", "linux-7.4-rc4", "linux-7.4",
    "linux-7.2.9", "testvm", "initramfs-6.12.117", "out-system-openrc-6.12.119",
]
FILES = [
    "linux-6.12.117.tar.xz", "linux-6.12.119.tar.xz",
    "linux-7.4-rc4.tar.gz", "linux-7.2.9.tar.xz", "build-disk.qcow2",
]
KEPT = {
    "linux-6.12.119", "linux-6.12.119.tar.xz",
    "linux-7.3.6", "out-system-7.3.6", "port-7.3.6", "out-system-openrc-6.12.119",
    "linux-7.4", "testvm", "build-disk.qcow2",
}


def build(lab: Path) -> None:
    for name in DIRECTORIES:
        (lab / name).mkdir()
        (lab / name / "Makefile").write_text("")
    for name in FILES:
        (lab / name).write_text("")


def run(lab: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--lab", str(lab), *extra],
        capture_output=True, text=True, check=False,
    )


def main() -> int:
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        lab = Path(tmp)
        build(lab)
        before = {entry.name for entry in lab.iterdir()}
        dry = run(lab, "--dry-run", "--drop-series", "7.2")
        if dry.returncode != 0 or {entry.name for entry in lab.iterdir()} != before:
            failures.append(f"--dry-run changed the lab or failed: {dry.stderr}")
        result = run(lab, "--drop-series", "7.2")
        left = {entry.name for entry in lab.iterdir()}
        if result.returncode != 0:
            failures.append(f"prune failed: {result.stderr}")
        if left != KEPT:
            failures.append(
                f"unexpected result: kept extra {sorted(left - KEPT)}, removed {sorted(KEPT - left)}"
            )
    missing = run(Path("/nonexistent-cjktty-lab"))
    if missing.returncode != 2:
        failures.append(f"a missing lab exited {missing.returncode}, expected 2")
    for failure in failures:
        print(failure, file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
