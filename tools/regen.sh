#!/bin/bash
# Regenerate a cjktty patch from a patched tree.
#
# The file list comes from `diff --git` lines, not from `+++`: upstream creates
# lib/fonts/font_cjk_32x32.h as an empty placeholder, and git emits no ---/+++
# pair for an empty new file. Missing it breaks the build with
# CONFIG_FONT_CJK_32x32=y.
#
# Usage: regen.sh <pristine-tree> <patched-tree> <source-patch> <output>
set -u

src=$1
work=$2
source_patch=$3
out=$4

: > "$out"
grep '^diff --git a/' "$source_patch" | sed 's|^diff --git a/||;s| b/.*||' | sort -u |
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
