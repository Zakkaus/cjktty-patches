#!/bin/bash
# Port a cjktty patch to a new kernel and regenerate it.
#
# Usage: tools/port.sh <new-version> <base-patch>
#
#   tools/port.sh 6.19 v6.x/cjktty-6.18.patch
#
# Applies the base patch with fuzz allowed, leaves the tree and any .rej files
# for hand fixing, and prints what to do next. Run it again with --finish once
# the rejects are resolved to write the new patch.
set -uo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
lab=${CJKTTY_LAB:-$(cd "$repo/.." && pwd)/lab}

die() { echo "$*" >&2; exit 1; }

finish=0
[ "${1:-}" = "--finish" ] && { finish=1; shift; }
[ $# -ge 1 ] || die "usage: $0 [--finish] <new-version> [base-patch]"

version=$1
series=${version%%.*}
minor=$(echo "$version" | cut -d. -f2)
base=${2:-}
pristine="$lab/linux-$version"
work="$lab/port-$version"
target="$repo/v$series.x/cjktty-$version.patch"

if [ "$finish" = 1 ]; then
	[ -d "$work" ] || die "no port in progress for $version"
	[ -z "$(find "$work" -name '*.rej' -print -quit)" ] ||
		die "unresolved rejects remain: $(find "$work" -name '*.rej' | tr '\n' ' ')"
	[ -n "$base" ] || base=$(cat "$work/.cjktty-base")
	find "$work" -name '*.orig' -delete
	bash "$repo/tools/regen.sh" "$pristine" "$work" "$base" "$target" || die "regeneration failed"
	echo "wrote $target"
	echo "now run: tools/test-patch.sh $version"
	exit 0
fi

[ -n "$base" ] && [ -f "$base" ] || die "give the base patch to port from"
base=$(cd "$(dirname "$base")" && pwd)/$(basename "$base")

if [ ! -d "$pristine" ]; then
	tarball="$lab/linux-$version.tar.xz"
	[ -f "$tarball" ] ||
		curl -fL# -o "$tarball" \
			"https://cdn.kernel.org/pub/linux/kernel/v$series.x/linux-$version.tar.xz" ||
		die "cannot download linux-$version"
	tar -xf "$tarball" -C "$lab" || die "cannot unpack $tarball"
fi

rm -rf "$work"
cp -a "$pristine" "$work"
echo "$base" > "$work/.cjktty-base"

patch -d "$work" -p1 --forward < "$base" > "$lab/port-$version.log" 2>&1
rejects=$(find "$work" -name '*.rej' | sort)

grep -E 'FAILED|Hunk #' "$lab/port-$version.log" | tail -20
echo
if [ -z "$rejects" ]; then
	echo "every hunk applied; run: $0 --finish $version"
else
	echo "rejects to fix by hand:"
	echo "$rejects" | sed 's/^/  /'
	echo
	echo "edit the files under $work, delete each .rej once resolved, then run:"
	echo "  $0 --finish $version"
fi
