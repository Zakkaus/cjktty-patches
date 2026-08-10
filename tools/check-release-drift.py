#!/usr/bin/env python3
"""Check current kernel.org releases against the newest patch in each series."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any
import urllib.request
from urllib.parse import urlparse


RELEASES_URL = "https://www.kernel.org/releases.json"
ACTIVE_MONIKERS = {"mainline", "stable", "longterm"}
PATCH_RE = re.compile(
    r"^v(?P<major>[0-9]+)\.x/cjktty-"
    r"(?P<version>[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:-rc[0-9]+)?)\.patch$"
)
VERSION_RE = re.compile(
    r"^(?P<major>[0-9]+)\.(?P<minor>[0-9]+)"
    r"(?:\.(?P<point>[0-9]+))?(?:-rc(?P<rc>[0-9]+))?$"
)


class CheckError(RuntimeError):
    """An operational failure, rather than patch drift."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    env_tarballs = os.environ.get("CJKTTY_TARBALLS")
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--releases-file",
        type=Path,
        help="read releases.json from this path instead of kernel.org",
    )
    source.add_argument(
        "--releases-url",
        default=RELEASES_URL,
        help=f"release feed URL (default: {RELEASES_URL})",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="patch repository root (default: parent of tools)",
    )
    parser.add_argument(
        "--tarball-dir",
        type=Path,
        default=Path(env_tarballs) if env_tarballs else None,
        help="kernel tarball cache (default: CJKTTY_TARBALLS or scratch directory)",
    )
    parser.add_argument(
        "--scratch-dir",
        type=Path,
        default=Path(os.environ.get("CJKTTY_LAB", tempfile.gettempdir())),
        help="parent for temporary extracted trees (default: CJKTTY_LAB or system temp)",
    )
    parser.add_argument("--report", type=Path, help="also write the full Markdown report")
    parser.add_argument(
        "--issue-report",
        type=Path,
        help="write a Markdown body containing only drifted series",
    )
    parser.add_argument("--json", type=Path, help="write machine-readable results")
    return parser.parse_args()


def version_parts(version: str) -> tuple[int, int, int, int]:
    match = VERSION_RE.fullmatch(version)
    if not match:
        raise CheckError(f"unsupported kernel version: {version}")
    major = int(match.group("major"))
    minor = int(match.group("minor"))
    rc = match.group("rc")
    if rc is not None:
        return major, minor, 0, int(rc)
    return major, minor, 1, int(match.group("point") or 0)


def series_of(version: str) -> str:
    major, minor, _, _ = version_parts(version)
    return f"{major}.{minor}"


def read_feed(path: Path | None, url: str) -> tuple[dict[str, Any], str]:
    if path is not None:
        try:
            return json.loads(path.read_text()), str(path)
        except (OSError, json.JSONDecodeError) as error:
            raise CheckError(f"cannot read release feed {path}: {error}") from error

    request = urllib.request.Request(url, headers={"User-Agent": "cjktty-release-drift"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response), url
    except (OSError, json.JSONDecodeError) as error:
        raise CheckError(f"cannot read release feed {url}: {error}") from error


def current_releases(feed: dict[str, Any]) -> dict[str, dict[str, Any]]:
    releases = feed.get("releases")
    if not isinstance(releases, list):
        raise CheckError("release feed has no releases array")

    current: dict[str, dict[str, Any]] = {}
    for release in releases:
        if not isinstance(release, dict):
            continue
        moniker = release.get("moniker")
        version = release.get("version")
        source = release.get("source")
        if (
            moniker not in ACTIVE_MONIKERS
            or release.get("iseol") is True
            or not isinstance(version, str)
            or not isinstance(source, str)
        ):
            continue
        series = series_of(version)
        previous = current.get(series)
        if previous is None or version_parts(version) > version_parts(previous["version"]):
            current[series] = release
    return current


def newest_patches(repo: Path) -> dict[str, tuple[str, Path]]:
    newest: dict[str, tuple[str, Path]] = {}
    for path in repo.glob("v[0-9]*.x/cjktty-*.patch"):
        relative = path.relative_to(repo).as_posix()
        match = PATCH_RE.fullmatch(relative)
        if not match:
            continue
        version = match.group("version")
        series = series_of(version)
        previous = newest.get(series)
        if previous is None or version_parts(version) > version_parts(previous[0]):
            newest[series] = (version, path)
    return newest


def download_tarball(source: str, tarball_dir: Path) -> Path:
    name = Path(urlparse(source).path).name
    if not name.startswith("linux-") or ".tar." not in name:
        raise CheckError(f"release source is not a kernel tarball: {source}")
    tarball = tarball_dir / name
    if tarball.is_file():
        return tarball

    partial = tarball.with_name(f"{tarball.name}.part.{os.getpid()}")
    request = urllib.request.Request(source, headers={"User-Agent": "cjktty-release-drift"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output)
        partial.replace(tarball)
    except OSError as error:
        partial.unlink(missing_ok=True)
        raise CheckError(f"cannot download {source}: {error}") from error
    return tarball


def apply_status(
    release: dict[str, Any], patch_path: Path, tarball_dir: Path, scratch_dir: Path
) -> tuple[str, str]:
    tarball = download_tarball(release["source"], tarball_dir)
    work = Path(tempfile.mkdtemp(prefix="release-drift.", dir=scratch_dir))
    tree = work / "linux"
    tree.mkdir()
    try:
        extracted = subprocess.run(
            ["tar", "-xf", str(tarball), "-C", str(tree), "--strip-components=1"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if extracted.returncode != 0:
            detail = extracted.stdout.strip()[-1000:]
            raise CheckError(f"cannot extract {tarball}: {detail}")

        with patch_path.open("rb") as patch_input:
            applied = subprocess.run(
                [
                    "patch",
                    "-d",
                    str(tree),
                    "-p1",
                    "--fuzz=0",
                    "--dry-run",
                    "--silent",
                    "--batch",
                    "--forward",
                ],
                stdin=patch_input,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        if applied.returncode == 0:
            return "applies", ""
        return "drifted", applied.stdout.strip()[-1000:]
    except OSError as error:
        raise CheckError(str(error)) from error
    finally:
        shutil.rmtree(work)


def markdown_report(results: list[dict[str, Any]], source: str) -> str:
    lines = [
        "# Kernel release patch status",
        "",
        f"Release feed: `{source}`",
        "",
        (
            "Watched series are the active, non-EOL kernel.org mainline, stable, and "
            "longterm series for which this repository has a monolithic patch. The "
            "newest versioned patch filename in each series is checked; archived series "
            "and split `cjktty-code-*` patches are not checked."
        ),
        "",
        "| Series | Channel | Current release | Newest patch | Apply status |",
        "|---|---|---|---|---|",
    ]
    for result in results:
        status = {
            "applies": "APPLIES",
            "drifted": "DRIFTED (reported only)" if result["rc"] else "DRIFTED",
            "error": "ERROR",
        }[result["status"]]
        lines.append(
            f"| {result['series']} | {result['moniker']} | {result['release']} | "
            f"`{result['patch']}` | {status} |"
        )

    applies = sum(result["status"] == "applies" for result in results)
    drifted = sum(result["status"] == "drifted" for result in results)
    errors = sum(result["status"] == "error" for result in results)
    lines.extend(
        [
            "",
            f"Summary: {applies} apply, {drifted} drifted, {errors} errors.",
            "",
            (
                "This is an application-only check using `patch -p1 --fuzz=0 "
                "--dry-run`. Applying is not the same as building the kernel or "
                "rendering CJK on a booted console."
            ),
            "",
            (
                "A drifted release candidate is reported but does not make the command "
                "fail. Drift in a stable or longterm series does."
            ),
        ]
    )
    error_results = [result for result in results if result["status"] == "error"]
    if error_results:
        lines.extend(["", "## Operational errors", ""])
        for result in error_results:
            detail = result["detail"].replace("\n", " ")
            lines.append(f"- {result['series']} ({result['release']}): {detail}")
    return "\n".join(lines) + "\n"


def issue_report(results: list[dict[str, Any]]) -> str:
    drifted = [result for result in results if result["status"] == "drifted"]
    lines = ["<!-- cjktty-release-drift -->", "# Kernel patch drift", ""]
    if drifted:
        lines.extend(
            [
                "These active kernel series no longer accept their newest patch:",
                "",
                "| Series | Channel | Current release | Patch | Workflow result |",
                "|---|---|---|---|---|",
            ]
        )
        for result in drifted:
            workflow = "reported only" if result["rc"] else "failure"
            lines.append(
                f"| {result['series']} | {result['moniker']} | {result['release']} | "
                f"`{result['patch']}` | {workflow} |"
            )
    else:
        lines.append("No watched kernel series is currently drifted.")
    lines.extend(
        [
            "",
            (
                "The check uses the active, non-EOL mainline, stable, and longterm "
                "entries in [kernel.org's released-versions feed]"
                "(https://www.kernel.org/releases.json). It checks the newest "
                "monolithic patch filename carried for each matching series."
            ),
            "",
            (
                "This only runs `patch -p1 --fuzz=0 --dry-run`. Applying is not the "
                "same as building the kernel or rendering CJK on a booted console."
            ),
            "",
            (
                "Release-candidate drift is expected to move and is reported without "
                "turning the workflow red."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_text(path: Path | None, content: str) -> None:
    if path is not None:
        path.write_text(content)


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    scratch_dir = args.scratch_dir.resolve()
    tarball_dir = (args.tarball_dir or scratch_dir / "tarballs").resolve()
    if not repo.is_dir():
        raise CheckError(f"repository does not exist: {repo}")
    scratch_dir.mkdir(parents=True, exist_ok=True)
    tarball_dir.mkdir(parents=True, exist_ok=True)

    feed, feed_source = read_feed(args.releases_file, args.releases_url)
    releases = current_releases(feed)
    patches = newest_patches(repo)
    watched = sorted(releases.keys() & patches.keys(), key=version_parts, reverse=True)
    if not watched:
        raise CheckError("no active kernel.org series has a monolithic repository patch")

    results: list[dict[str, Any]] = []
    for index, series in enumerate(watched, 1):
        release = releases[series]
        _, patch_path = patches[series]
        relative_patch = patch_path.relative_to(repo).as_posix()
        print(
            f"[{index}/{len(watched)}] {series}: {relative_patch} -> {release['version']}",
            file=sys.stderr,
            flush=True,
        )
        try:
            status, detail = apply_status(release, patch_path, tarball_dir, scratch_dir)
        except CheckError as error:
            status, detail = "error", str(error)
        results.append(
            {
                "series": series,
                "moniker": release["moniker"],
                "release": release["version"],
                "source": release["source"],
                "patch": relative_patch,
                "status": status,
                "rc": release["moniker"] == "mainline" and "-rc" in release["version"],
                "detail": detail,
            }
        )

    error_count = sum(result["status"] == "error" for result in results)
    blocking_drift_count = sum(
        result["status"] == "drifted" and not result["rc"] for result in results
    )
    rc_drift_count = sum(
        result["status"] == "drifted" and result["rc"] for result in results
    )
    exit_code = 2 if error_count else 1 if blocking_drift_count else 0
    payload = {
        "feed": feed_source,
        "selection": (
            "active non-EOL mainline, stable, and longterm series with "
            "monolithic patches"
        ),
        "results": results,
        "summary": {
            "watched_count": len(results),
            "apply_count": sum(result["status"] == "applies" for result in results),
            "drift_count": blocking_drift_count + rc_drift_count,
            "blocking_drift_count": blocking_drift_count,
            "rc_drift_count": rc_drift_count,
            "error_count": error_count,
            "exit_code": exit_code,
        },
    }
    report = markdown_report(results, feed_source)
    print(report, end="")
    write_text(args.report, report)
    write_text(args.issue_report, issue_report(results))
    if args.json is not None:
        args.json.write_text(json.dumps(payload, indent=2) + "\n")
    return exit_code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
