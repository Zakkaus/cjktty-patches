#!/bin/bash
# Apply a cjktty patch, build the kernel, boot it and check the console font.
#
# Usage: tools/test-patch.sh <kernel-version> [patch-file ...]
#
#   tools/test-patch.sh 6.18.43
#   tools/test-patch.sh 7.0 v7.x/cjktty-7.0.patch
#   tools/test-patch.sh 6.18.44 cjktty-font-unifont-15.1.04.patch cjktty-code-6.18.patch
#
# A patch passes only when all three succeed: it applies with no fuzz, the
# kernel builds, and the booted console reports the CJK font. Artifacts stay in
# $CJKTTY_LAB for inspection.
set -uo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
lab=${CJKTTY_LAB:-$(cd "$repo/.." && pwd)/lab}
ovmf_code=${OVMF_CODE:-/usr/share/edk2-ovmf/OVMF_CODE_4M.qcow2}
ovmf_vars=${OVMF_VARS:-/usr/share/edk2-ovmf/OVMF_VARS.fd}
jobs=${JOBS:-$(nproc)}
boot_timeout=${BOOT_TIMEOUT:-120}

die() { echo "$*" >&2; exit 1; }
step() { printf '\n== %s\n' "$*"; }

[ $# -ge 1 ] || die "usage: $0 <kernel-version> [patch-file ...]"
version=$1
series=${version%%.*}
minor=$(echo "$version" | cut -d. -f2)
shift

patch_files=("$@")
if [ ${#patch_files[@]} -eq 0 ]; then
	for candidate in "$repo/v$series.x/cjktty-$version.patch" \
			 "$repo/v$series.x/cjktty-$series.$minor.patch"; do
		[ -f "$candidate" ] && { patch_files=("$candidate"); break; }
	done
fi
[ ${#patch_files[@]} -gt 0 ] || die "no patch for $version"
for patch_file in "${patch_files[@]}"; do
	[ -f "$patch_file" ] || die "patch not found: $patch_file"
done

for tool in gcc cpio qemu-system-x86_64 patch; do
	command -v "$tool" >/dev/null || die "$tool is not installed"
done
[ -f "$ovmf_code" ] || die "OVMF firmware not found at $ovmf_code; set OVMF_CODE"

mkdir -p "$lab"
tarball="$lab/linux-$version.tar.xz"
pristine="$lab/linux-$version"
tree="$lab/test-$version"
out="$lab/out-$version"
mkdir -p "$out"

step "kernel source $version"
if [ ! -d "$pristine" ]; then
	[ -f "$tarball" ] ||
		curl -fL# -o "$tarball" \
			"https://cdn.kernel.org/pub/linux/kernel/v$series.x/linux-$version.tar.xz" ||
		die "cannot download linux-$version"
	tar -xf "$tarball" -C "$lab" || die "cannot unpack $tarball"
fi

patch_names=()
for patch_file in "${patch_files[@]}"; do
	patch_names+=("$(basename "$patch_file")")
done
step "apply ${patch_names[*]}"
rm -rf "$tree"
cp -a "$pristine" "$tree"
for patch_file in "${patch_files[@]}"; do
	patch -d "$tree" -p1 --fuzz=0 --silent < "$patch_file" ||
		die "$(basename "$patch_file") does not apply to $version with fuzz=0"
done
find "$tree" -name '*.orig' -delete

step "configure"
make -C "$tree" -s x86_64_defconfig >/dev/null || die "defconfig failed"
# FB_EFI drives the framebuffer under OVMF. Without a framebuffer console the
# kernel falls back to vgacon, whose font holds 512 glyphs and cannot show CJK.
# FONT_CJK_32x32 stays off: the base patch ships an empty font_cjk_32x32.h, so
# it would cost 8 MiB for a blank font.
"$tree/scripts/config" --file "$tree/.config" \
	-e CONFIG_FB -e CONFIG_FB_EFI -e CONFIG_FB_SIMPLE -e CONFIG_SYSFB_SIMPLEFB \
	-e CONFIG_DRM_FBDEV_EMULATION -e CONFIG_FRAMEBUFFER_CONSOLE \
	-e CONFIG_FRAMEBUFFER_CONSOLE_ROTATION -e CONFIG_CONSOLE_TRANSLATIONS \
	-e CONFIG_FONTS -e CONFIG_FONT_CJK_16x16 -d CONFIG_FONT_CJK_32x32 \
	-e CONFIG_BLK_DEV_INITRD -e CONFIG_DEVTMPFS -e CONFIG_DEVTMPFS_MOUNT \
	-e CONFIG_SERIAL_8250 -e CONFIG_SERIAL_8250_CONSOLE || die "scripts/config failed"
make -C "$tree" -s olddefconfig >/dev/null || die "olddefconfig failed"
grep -q '^CONFIG_FONT_CJK_16x16=y' "$tree/.config" ||
	die "CONFIG_FONT_CJK_16x16 did not enable; the patch may not touch lib/fonts"

step "build"
make -C "$tree" -j"$jobs" bzImage > "$out/build.log" 2>&1 || {
	tail -20 "$out/build.log"
	die "kernel build failed, see $out/build.log"
}
warnings=$(grep -c 'warning:' "$out/build.log")
echo "built with $warnings warnings"

step "initramfs"
initdir="$lab/initramfs-$version"
rm -rf "$initdir"
mkdir -p "$initdir"/{proc,sys,dev}
gcc -static -Os -o "$initdir/init" "$repo/tools/init.c" 2>/dev/null || die "cannot build init"
strip "$initdir/init"
(cd "$initdir" && find . | cpio -o -H newc --quiet | gzip -1 > "$out/initramfs.gz") ||
	die "cannot pack initramfs"

step "boot"
cp -f "$ovmf_vars" "$out/OVMF_VARS.fd"
rm -f "$out/serial.log" "$out/console.ppm" "$out/monitor.sock"
qemu-system-x86_64 -enable-kvm -m 2G -smp 2 -machine q35 \
	-drive "if=pflash,format=qcow2,readonly=on,file=$ovmf_code" \
	-drive "if=pflash,format=raw,file=$out/OVMF_VARS.fd" \
	-kernel "$tree/arch/x86/boot/bzImage" -initrd "$out/initramfs.gz" \
	-append 'console=tty0 console=ttyS0,115200 rdinit=/init' \
	-vga std -display none \
	-serial "file:$out/serial.log" \
	-monitor "unix:$out/monitor.sock,server,nowait" >/dev/null 2>&1 &
qemu=$!

deadline=$((SECONDS + boot_timeout))
while [ $SECONDS -lt $deadline ]; do
	grep -q 'CJKTTY-BOOTED' "$out/serial.log" 2>/dev/null && break
	kill -0 $qemu 2>/dev/null || break
	sleep 2
done

if [ -S "$out/monitor.sock" ]; then
	printf 'screendump %s\n' "$out/console.ppm" |
		timeout 20 socat - "unix-connect:$out/monitor.sock" >/dev/null 2>&1 ||
		python3 -c "
import socket, sys, time
s = socket.socket(socket.AF_UNIX)
s.connect(sys.argv[1])
time.sleep(0.5)
s.sendall(b'screendump ' + sys.argv[2].encode() + b'\n')
time.sleep(3)
" "$out/monitor.sock" "$out/console.ppm" 2>/dev/null
fi
kill $qemu 2>/dev/null
wait $qemu 2>/dev/null

grep -q 'CJKTTY-BOOTED' "$out/serial.log" 2>/dev/null ||
	die "the guest never reached the test; see $out/serial.log"
grep -o 'vc-font: .*' "$out/serial.log" | head -1

step "console"
[ -s "$out/console.ppm" ] || die "no screenshot was captured; see $out/serial.log"
python3 "$repo/tools/check-console.py" "$out/console.ppm" ||
	die "$version: the console did not render CJK; see $out/console.ppm"

echo
echo "$version: PASS (applies with fuzz=0, builds, renders CJK on the console)"
echo "artifacts in $out"
rm -rf "$tree"
