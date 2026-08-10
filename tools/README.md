# tools

Maintenance and test scripts for the patch collection. They need `gcc`, `cpio`,
`patch`, `qemu-system-x86_64` with KVM, and OVMF firmware. Kernel trees and test
artifacts go to `$CJKTTY_LAB`, which defaults to `../lab`.

## test-patch.sh

```
tools/test-patch.sh 6.18.43
tools/test-patch.sh 7.0 v7.x/cjktty-7.0.patch
tools/test-patch.sh 6.18.44 cjktty-font-unifont-15.1.04.patch v6.x/cjktty-code-6.18.patch
```

Downloads the kernel if needed, then runs three checks. A patch is only finished
when all three pass:

1. **applies** — `patch -p1 --fuzz=0`, no fuzzy matching allowed.
2. **builds** — a full `bzImage` with the framebuffer console and
   `CONFIG_FONT_CJK_16x16` enabled.
3. **renders** — boots under OVMF and checks the screenshot.

The third check is not an ioctl. cjktty leaves `vc_font` at the base 256-glyph
font and draws CJK from its own buffer, so the console keeps reporting
`8x16 charcount=256` whether or not the patch works. `check-console.py` instead
compares two different CJK cells on screen: real glyphs differ and carry ink,
missing ones are the same empty box.

When patch paths are given, the test applies all of them from left to right.
This lets a split font-and-code pair go through the same build and boot checks as
a monolithic patch.

`CONFIG_FONT_CJK_32x32` stays off during the test. The base patch ships an empty
`font_cjk_32x32.h`, so enabling it spends 8 MiB on a blank font.

## make-testvm.sh, make-boot-testvm.sh and test-system.sh

```
tools/make-testvm.sh            # once: builds lab/testvm/base.img from a stage3
tools/test-system.sh 6.18.43
tools/test-system.sh 6.18.44 cjktty-font-unifont-15.1.04.patch v6.x/cjktty-code-6.18.patch

tools/make-boot-testvm.sh       # once: adds an ESP, GRUB and dracut
tools/test-system.sh --bootloader 6.18.43
```

`test-patch.sh` stops at an initramfs, which never reaches the paths this patch
changes. `test-system.sh` boots a stage3 systemd userland from disk and drives
the rest over the serial port: systemd to `running`, `systemd-vconsole-setup`
reloading the font, `setfont`, `chvt`, the framebuffer handover from efifb to
virtio-gpu, console rotation, an fbcon unbind and rebind, `dmesg` free of oops
and call traces, and `systemctl poweroff`.

Rotation and the rebind are there because they are the only way to reach the two
pieces of code this collection changes most. `fbcon_rotate_font_utf()` runs under
rotation and nowhere else, and porting to a new kernel rewrites it more often than
anything else in the patch; `fbcon_release()` frees both font buffers and a normal
shutdown does not reach it. Both are triggered at runtime, so neither costs a
second boot: `/sys/class/graphics/fbcon/rotate_all` and
`/sys/class/vtconsole/vtcon*/bind`.

The default path keeps the kernel out of the image. It is passed with `-kernel`
and the disk is a qcow2 overlay on the base, so swapping kernels costs one build
and no install, and a run cannot damage the base image.

The optional `--bootloader` path uses a separate partitioned base image. It
builds and installs the kernel modules into an overlay, invokes the image's
`installkernel`, requires dracut to produce a non-empty initramfs and requires
GRUB's generated configuration to name both files. The verification boot then
receives neither `-kernel` nor `-append`; OVMF starts GRUB from the ESP and GRUB
supplies the kernel command line. The serial driver distinguishes GRUB not
starting from GRUB starting but failing to hand off to Linux, and the guest
confirms that it unpacked an initramfs before the normal system test continues.

Three screenshots come out of each run: `login.ppm` is the getty screen,
`rotated.ppm` is the CJK line drawn while the console is turned ninety degrees,
and `console.ppm` is the CJK line after the DRM handover. `check-console.py`
checks the last two.

Every step is an assertion, not a screenshot for a human to squint at. The bind
loop ends in `[ $n -gt 0 ]` because a loop that matches no console exits 0 and
the release path would go unrun; the run then confirms from `dmesg` that the
console really left the framebuffer driver.

Like `test-patch.sh`, `test-system.sh` applies any explicitly named patches from
left to right.

## split-patch.py

```
tools/split-patch.py <source-patch> <font-output> <code-output>
tools/test-split-patch.sh
```

Splits a monolithic patch by complete file stanza. Every hunk for a path matching
`lib/fonts/font_cjk_<width>x<height>.h` goes to the font output; every other hunk
goes to the code output. File metadata stays with its stanza, so the empty
`font_cjk_32x32.h` is retained in the font output even though it has no
`---`/`+++` pair.

The source file list is the ordered union of `diff --git a/` and `--- a/`
headers. Both forms are required: current patches use plain `---` headers for
most files, while an empty new file can have only a `diff --git` header.

Apply the shared font patch before the code patch for the target kernel:

```
patch -d linux -p1 --fuzz=0 < cjktty-font-unifont-15.1.04.patch
patch -d linux -p1 --fuzz=0 < v6.x/cjktty-code-6.18.patch
```

## Naming a split patch

The font patch carries the Unifont release it was generated from, because a
published filename is frozen: five ebuilds in `gentoo-zh/overlay` fetch patches
by raw URL, so a font update adds `cjktty-font-unifont-<version>.patch` beside
the old one rather than replacing it. `tools/gen-font.py` produces that data, so
the name is checkable rather than a label.

A code patch needs no version of its own. It lives under `v<major>.x/` and its
filename already names the kernel.

## port.sh

```
tools/port.sh 6.19 v6.x/cjktty-6.18.patch
# fix the .rej files it lists
tools/port.sh --finish 6.19
tools/test-patch.sh 6.19
```

Applies the nearest existing patch to a new kernel, leaves the tree and rejects
for hand fixing, then regenerates the patch. Neighbouring versions usually differ
only in line offsets; a reject means upstream changed a struct field, a function's
visibility, or the order of an allocation.

## regen.sh

```
tools/regen.sh <pristine-tree> <patched-tree> <source-patch> <output>
```

Writes a patch from the difference between two trees. The file list comes from
the source patch's `diff --git` lines, not from `+++`: git emits no `---`/`+++`
pair for an empty new file, and `font_cjk_32x32.h` is empty. Every stanza gets
its own `diff --git` header so `patch` cannot attach a `new file mode` to the
file that follows.

Prefer editing a patch in place over regenerating it. A regenerated 12 MB file
hides a two-line change from review.

## gen-font.py

```
tools/gen-font.py --size 16 --base-font linux/lib/fonts/font_8x16.c \
  unifont-15.1.04.hex > font_cjk_16x16.h
tools/gen-font.py --size 32 --base-font linux/lib/fonts/font_ter16x32.c \
  unifont-15.1.04.hex > font_cjk_32x32.h
```

Generates the two-cell BMP layout used by cjktty. The first 256 halfwidth
glyphs come from the named Linux base font; `font_ter16x32.c` is derived from
Terminus. Remaining glyphs come from the official GNU Unifont `.hex` release.
The script determines halfwidth versus fullwidth from each hex payload, not the
codepoint, and doubles both axes for 32x32 output. Use
`font/precompiled/unifont-<version>.hex` from the project's
[official release tarball](https://unifoundry.com/pub/unifont/). Both current
arrays match Unifont 15.1.04; later whole-font updates superseded the 13.0.06
source named by the first 32x32 changelog entry.

Pass `--compare` with a generated header or a cjktty patch to verify the data
without writing the generated array:

```
tools/gen-font.py --size 16 --base-font linux/lib/fonts/font_8x16.c \
  --compare v6.x/cjktty-6.18.patch unifont-15.1.04.hex
```

## check-console.py

```
tools/check-console.py console.ppm
tools/check-console.py --rotated rotated.ppm
```

Used by both test scripts; run it directly to re-check a saved screenshot.

The default mode compares two adjacent CJK cells at a known row. `--rotated`
cannot use fixed rows, so it measures the bounding box of the lit pixels and
requires it to be taller than wide. Ink alone would not do: a console that
ignored the rotation still shows a horizontal line with the same amount of ink.

## drive-system.py and init.c

`drive-system.py` is the serial driver `test-system.sh` runs; every command it
sends is checked for exit status, and a numeric result is read back inside a
unique marker because the stage3 shell wraps its prompt in OSC 133 sequences.
`init.c` is the initramfs init for `test-patch.sh`: it mounts devtmpfs itself,
since `CONFIG_DEVTMPFS_MOUNT` applies only to a real root, then prints the CJK
lines the screenshot is taken of.

## test-stress.sh

`tools/test-stress.sh <version> [patch ...]` builds the patch with KASAN,
kmemleak, lockdep and `DEBUG_ATOMIC_SLEEP`, then cycles `setfont`, `chvt`,
console rotation, an fbcon unbind and rebind, a console resize and a burst of
CJK output. `test-system.sh` performs each of those once; a leak on the release
path or a lock taken in the wrong order only appears when they repeat.

The verdict comes from `tools/stress-verdict.py`, which strips the shell's own
echo of the grep command before counting. Counting the raw serial log reports
the pattern itself as a finding.

Proven to fail: removing one `kvfree(par->fontbuffer_utf)` from
`fbcon_release()` makes kmemleak report `unreferenced object` of 2,097,152
bytes, exactly the 16x16 font buffer, and the script exits 1.

The guest needs 4 GiB because KASAN roughly triples the kernel's memory use.
