#!/bin/bash
# Regenerate a cjktty patch from a patched tree.
#
# The file list is the union of `diff --git` and `--- a/` lines. Neither alone
# is enough: an empty new file such as lib/fonts/font_cjk_32x32.h carries no
# ---/+++ pair, and the older patches in this collection are plain diff output
# with a single `diff --git` line for the whole file.
#
# Usage: regen.sh <pristine-tree> <patched-tree> <source-patch> <output>
set -u

src=$1
work=$2
source_patch=$3
out=$4

: > "$out"
{
	grep '^diff --git a/' "$source_patch" | sed 's|^diff --git a/||;s| b/.*||'
	grep '^--- a/' "$source_patch" | sed 's|^--- a/||;s|[[:space:]].*||'
} | sort -u |
while read -r f; do
	old="$src/$f"
	if [ ! -f "$old" ] && [ ! -s "$work/$f" ]; then
		printf 'diff --git a/%s b/%s\nnew file mode 100644\nindex 0000000..e69de29\n' "$f" "$f" >> "$out"
		continue
	fi
	[ -f "$old" ] || old=/dev/null
	# Every stanza needs its own git header, otherwise patch attaches the
	# `new file mode` above to the next file it sees.
	printf 'diff --git a/%s b/%s\n' "$f" "$f" >> "$out"
	diff -up --label "a/$f" --label "b/$f" "$old" "$work/$f" >> "$out"
done

# diff exits 1 when files differ, which is the normal case here.
exit 0
