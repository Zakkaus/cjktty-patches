#!/bin/bash
# Boot a patched kernel on a full systemd userland and exercise the console.
#
# Usage: tools/test-system.sh <kernel-version> [patch-file ...]
#
# test-patch.sh stops at an initramfs, which never touches the paths this patch
# actually changes: the framebuffer handover from efifb to a DRM driver, a font
# reload by systemd-vconsole-setup, a console resize, and shutdown. This runs a
# real system through all of them.
#
# The kernel is passed on the command line and the disk is a throwaway overlay
# on the base image, so swapping kernels needs no install step.
set -uo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
lab=${CJKTTY_LAB:-$(cd "$repo/.." && pwd)/lab}
ovmf_code=${OVMF_CODE:-/usr/share/edk2-ovmf/OVMF_CODE_4M.qcow2}
ovmf_vars=${OVMF_VARS:-/usr/share/edk2-ovmf/OVMF_VARS.fd}
jobs=${JOBS:-$(nproc)}
boot_timeout=${BOOT_TIMEOUT:-300}

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

base="$lab/testvm/base.img"
[ -f "$base" ] || die "no base image; run tools/make-testvm.sh first"

pristine="$lab/linux-$version"
tree="$lab/system-$version"
out="$lab/out-system-$version"
mkdir -p "$out"

step "kernel source $version"
if [ ! -d "$pristine" ]; then
	tarball="$lab/linux-$version.tar.xz"
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
# virtio-blk and ext4 are built in so the machine needs no initramfs, and
# virtio-gpu is built in so DRM takes the framebuffer over from efifb during
# boot. That handover is the point of this test. It has to be the only display
# adapter, or screendump captures the unused one.
"$tree/scripts/config" --file "$tree/.config" \
	-e CONFIG_FB -e CONFIG_FB_EFI -e CONFIG_SYSFB_SIMPLEFB \
	-e CONFIG_DRM -e CONFIG_DRM_VIRTIO_GPU -e CONFIG_DRM_FBDEV_EMULATION \
	-e CONFIG_FRAMEBUFFER_CONSOLE -e CONFIG_FRAMEBUFFER_CONSOLE_DETECT_PRIMARY \
	-e CONFIG_FRAMEBUFFER_CONSOLE_ROTATION -e CONFIG_CONSOLE_TRANSLATIONS \
	-e CONFIG_FONTS -e CONFIG_FONT_CJK_16x16 -d CONFIG_FONT_CJK_32x32 \
	-e CONFIG_VIRTIO -e CONFIG_VIRTIO_PCI -e CONFIG_VIRTIO_BLK \
	-e CONFIG_EXT4_FS -e CONFIG_DEVTMPFS -e CONFIG_DEVTMPFS_MOUNT \
	-e CONFIG_SERIAL_8250 -e CONFIG_SERIAL_8250_CONSOLE \
	-e CONFIG_CGROUPS -e CONFIG_INOTIFY_USER -e CONFIG_SIGNALFD -e CONFIG_TIMERFD \
	-e CONFIG_EPOLL -e CONFIG_TMPFS -e CONFIG_TMPFS_POSIX_ACL \
	-e CONFIG_AUTOFS_FS -e CONFIG_NET_NS -e CONFIG_PROC_FS -e CONFIG_SYSFS ||
	die "scripts/config failed"
make -C "$tree" -s olddefconfig >/dev/null || die "olddefconfig failed"

step "build"
make -C "$tree" -j"$jobs" bzImage > "$out/build.log" 2>&1 || {
	tail -20 "$out/build.log"
	die "kernel build failed, see $out/build.log"
}
echo "built with $(grep -c 'warning:' "$out/build.log") warnings"

step "boot"
overlay="$out/disk.qcow2"
rm -f "$overlay" "$out/serial.log" "$out/console.ppm" "$out/rotated.ppm" \
	"$out/login.ppm" "$out/monitor.sock"
qemu-img create -q -f qcow2 -F raw -b "$base" "$overlay" >/dev/null ||
	die "cannot create the overlay"
cp -f "$ovmf_vars" "$out/OVMF_VARS.fd"

qemu-system-x86_64 -enable-kvm -m 2G -smp 2 -machine q35 \
	-drive "if=pflash,format=qcow2,readonly=on,file=$ovmf_code" \
	-drive "if=pflash,format=raw,file=$out/OVMF_VARS.fd" \
	-drive "file=$overlay,format=qcow2,if=virtio" \
	-kernel "$tree/arch/x86/boot/bzImage" \
	-append 'root=/dev/vda rw console=tty0 console=ttyS0,115200' \
	-vga virtio -display none \
	-serial "unix:$out/monitor-serial.sock,server,nowait" \
	-monitor "unix:$out/monitor.sock,server,nowait" >/dev/null 2>&1 &
qemu=$!

python3 "$repo/tools/drive-system.py" "$out" "$boot_timeout"
result=$?

kill $qemu 2>/dev/null
wait $qemu 2>/dev/null
[ $result -eq 0 ] || die "$version: the system test failed; see $out/serial.log"

step "console"
[ -s "$out/login.ppm" ] || die "no login screenshot was captured"
[ -s "$out/console.ppm" ] || die "no console screenshot was captured"
[ -s "$out/rotated.ppm" ] || die "no rotated screenshot was captured"
python3 "$repo/tools/check-console.py" "$out/console.ppm" ||
	die "$version: the console did not render CJK after the DRM handover"
python3 "$repo/tools/check-console.py" --rotated "$out/rotated.ppm" ||
	die "$version: the console drew nothing under rotation"

echo
echo "$version: PASS (full system: DRM handover, setfont, chvt, rotation, fbcon rebind)"
echo "screenshots: $out/login.ppm, $out/rotated.ppm and $out/console.ppm"
echo "artifacts in $out"
rm -rf "$tree"
