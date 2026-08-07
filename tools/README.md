# tools

Maintenance and test scripts for the patch collection. They need `gcc`, `cpio`,
`patch`, `qemu-system-x86_64` with KVM, and OVMF firmware. Kernel trees and test
artifacts go to `$CJKTTY_LAB`, which defaults to `../lab`.

## test-patch.sh

```
tools/test-patch.sh 6.18.43
tools/test-patch.sh 7.0 v7.x/cjktty-7.0.patch
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

`CONFIG_FONT_CJK_32x32` stays off during the test. The base patch ships an empty
`font_cjk_32x32.h`, so enabling it spends 8 MiB on a blank font.

## make-testvm.sh and test-system.sh

```
tools/make-testvm.sh            # once: builds lab/testvm/base.img from a stage3
tools/test-system.sh 6.18.43
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

The kernel never goes into the image. It is passed with `-kernel` and the disk
is a qcow2 overlay on the base, so swapping kernels costs one build and no
install, and a run cannot damage the base image.

Three screenshots come out of each run: `login.ppm` is the getty screen,
`rotated.ppm` is the CJK line drawn while the console is turned ninety degrees,
and `console.ppm` is the CJK line after the DRM handover. `check-console.py`
checks the last two.

Every step is an assertion, not a screenshot for a human to squint at. The bind
loop ends in `[ $n -gt 0 ]` because a loop that matches no console exits 0 and
the release path would go unrun; the run then confirms from `dmesg` that the
console really left the framebuffer driver.

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
