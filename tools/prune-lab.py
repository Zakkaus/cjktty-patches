#!/usr/bin/env python3
"""Remove kernel trees and tarballs that a newer release of the same series replaced."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

# Every name the test tools leave in the lab, keyed to the kernel version it belongs to.
ARTIFACT = re.compile(
    r"^(?:linux|test|system|initramfs|out|out-system|out-system-openrc|out-stress|port)-"
    r"(?P<version>\d+\.\d+(?:\.\d+)?(?:-rc\d+)?)"
    r"(?:\.tar\.(?:xz|gz))?$"
)
VERSION = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?(?:-rc(\d+))?$")


@dataclass(frozen=True)
class Artifact:
    path: Path
    version: str


def version_key(version: str) -> tuple[int, int, int, int]:
    match = VERSION.match(version)
    if match is None:
        raise ValueError(f"not a kernel version: {version}")
    major, minor, patch, rc = match.groups()
    # A release candidate sorts before the release it precedes.
    return (int(major), int(minor), int(patch or 0), int(rc) if rc else sys.maxsize)


def series(version: str) -> str:
    return ".".join(version.split("-")[0].split(".")[:2])


def collect(lab: Path) -> list[Artifact]:
    found = []
    for entry in sorted(lab.iterdir()):
        match = ARTIFACT.match(entry.name)
        if match:
            found.append(Artifact(entry, match.group("version")))
    return found


def stale(artifacts: list[Artifact], dropped_series: set[str]) -> list[Artifact]:
    newest: dict[str, str] = {}
    for artifact in artifacts:
        name = series(artifact.version)
        if name not in newest or version_key(artifact.version) > version_key(newest[name]):
            newest[name] = artifact.version
    return [
        artifact
        for artifact in artifacts
        if series(artifact.version) in dropped_series
        or newest[series(artifact.version)] != artifact.version
    ]


def remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def main() -> int:
    default_lab = Path(os.environ.get("CJKTTY_LAB", Path(__file__).resolve().parents[2] / "lab"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", type=Path, default=default_lab)
    parser.add_argument(
        "--drop-series",
        default="",
        help="comma-separated series to remove entirely, such as 7.1,7.2",
    )
    parser.add_argument("-n", "--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.lab.is_dir():
        print(f"prune-lab: {args.lab} is not a directory", file=sys.stderr)
        return 2
    dropped = {name for name in args.drop_series.split(",") if name}
    for artifact in stale(collect(args.lab), dropped):
        print(f"{'would remove' if args.dry_run else 'remove'} {artifact.path}")
        if not args.dry_run:
            remove(artifact.path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
