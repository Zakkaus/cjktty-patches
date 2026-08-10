#!/bin/bash
# Boot a patched kernel on a full systemd userland and exercise the console.
#
# Usage: tools/test-system.sh [--bootloader] [--cjk32] <kernel-version> [patch-file ...]
#
# test-patch.sh stops at an initramfs, which never touches the paths this patch
# actually changes: the framebuffer handover from efifb to a DRM driver, a font
# reload by systemd-vconsole-setup, a console resize, and shutdown. This runs a
# real system through all of them.
#
# The default fast path passes the kernel on the QEMU command line. The optional
# bootloader path installs the kernel and modules into a throwaway overlay with
# installkernel, then boots the overlay through GRUB and a dracut initramfs.
set -uo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
lab=${CJKTTY_LAB:-$(cd "$repo/.." && pwd)/lab}
ovmf_code=${OVMF_CODE:-/usr/share/edk2-ovmf/OVMF_CODE_4M.qcow2}
ovmf_vars=${OVMF_VARS:-/usr/share/edk2-ovmf/OVMF_VARS.fd}
jobs=${JOBS:-$(nproc)}
boot_timeout=${BOOT_TIMEOUT:-300}

die() { echo "$*" >&2; exit 1; }
step() { printf '\n== %s\n' "$*"; }

cjk32=0
if [ "${1:-}" = "--cjk32" ]; then
	cjk32=1
	shift
fi

bootloader=0
if [ "${1:-}" = "--bootloader" ]; then
	bootloader=1
	shift
fi
[ $# -ge 1 ] || die "usage: $0 [--bootloader] [--cjk32] <kernel-version> [patch-file ...]"
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

if [ $bootloader -eq 1 ]; then
	base="$lab/boot-testvm/base.img"
	base_builder=make-boot-testvm.sh
else
	base="$lab/testvm/base.img"
	base_builder=make-testvm.sh
fi
[ -f "$base" ] || die "no base image; run tools/$base_builder first"

pristine="$lab/linux-$version"
tree="$lab/system-$version"
if [ $bootloader -eq 1 ]; then
	out="$lab/out-system-boot-$version"
else
	out="$lab/out-system-$version"
fi
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
if [ "$cjk32" = 1 ]; then
	patch -d "$tree" -p1 --fuzz=0 --silent < "$repo/cjktty-add-cjk32x32-font-data.patch" ||
		die "the 32x32 font data patch does not apply to $version"
fi
find "$tree" -name '*.orig' -delete

step "configure"
make -C "$tree" -s x86_64_defconfig >/dev/null || die "defconfig failed"
# virtio-blk and ext4 are built in so the fast path needs no initramfs. The
# bootloader path still generates and loads one to exercise the installed boot
# chain. virtio-gpu is built in so DRM takes the framebuffer over from efifb.
# It has to be the only display adapter, or screendump captures the unused one.
"$tree/scripts/config" --file "$tree/.config" \
	-e CONFIG_FB -e CONFIG_FB_EFI -e CONFIG_SYSFB_SIMPLEFB \
	-e CONFIG_DRM -e CONFIG_DRM_VIRTIO_GPU -e CONFIG_DRM_FBDEV_EMULATION \
	-e CONFIG_FRAMEBUFFER_CONSOLE -e CONFIG_FRAMEBUFFER_CONSOLE_DETECT_PRIMARY \
	-e CONFIG_FRAMEBUFFER_CONSOLE_ROTATION -e CONFIG_CONSOLE_TRANSLATIONS \
	-e CONFIG_FONTS \
	-e CONFIG_VIRTIO -e CONFIG_VIRTIO_PCI -e CONFIG_VIRTIO_BLK \
	-e CONFIG_EXT4_FS -e CONFIG_DEVTMPFS -e CONFIG_DEVTMPFS_MOUNT \
	-e CONFIG_SERIAL_8250 -e CONFIG_SERIAL_8250_CONSOLE \
	-e CONFIG_CGROUPS -e CONFIG_INOTIFY_USER -e CONFIG_SIGNALFD -e CONFIG_TIMERFD \
	-e CONFIG_EPOLL -e CONFIG_TMPFS -e CONFIG_TMPFS_POSIX_ACL \
	-e CONFIG_AUTOFS_FS -e CONFIG_NET_NS -e CONFIG_PROC_FS -e CONFIG_SYSFS ||
	die "scripts/config failed"
if [ $bootloader -eq 1 ]; then
	"$tree/scripts/config" --file "$tree/.config" \
		-e CONFIG_BLK_DEV_INITRD -e CONFIG_RD_GZIP \
		-e CONFIG_EFI -e CONFIG_EFI_STUB -e CONFIG_EFI_PARTITION \
		-e CONFIG_VFAT_FS -e CONFIG_NLS_CODEPAGE_437 -e CONFIG_NLS_ISO8859_1 ||
		die "scripts/config failed for the bootloader path"
fi
# scripts/config exits 0 without touching these symbols, so rewrite the line
# outright; olddefconfig keeps what it finds here.
set_option() {
	# defconfig omits a symbol whose default is n, so absence is normal here;
	# the assertion after olddefconfig is what proves the symbol exists.
	local name=$1 value=$2 file=$tree/.config
	sed -i "/^CONFIG_$name=/d; /^# CONFIG_$name is not set/d" "$file"
	if [ "$value" = n ]; then
		echo "# CONFIG_$name is not set" >> "$file"
	else
		echo "CONFIG_$name=$value" >> "$file"
	fi
}
if [ "$cjk32" = 1 ]; then
	# ter16x32 becomes the base font, so the console cell doubles in both axes
	set_option FONT_CJK_16x16 n
	set_option FONT_CJK_32x32 y
	set_option FONT_TER16x32 y
	# fbcon picks the first registered font, so 8x16 has to go or the console
	# stays 8x16 and the 32x32 path is never reached
	set_option FONT_8x16 n
else
	set_option FONT_CJK_16x16 y
	set_option FONT_CJK_32x32 n
fi
make -C "$tree" -s olddefconfig >/dev/null || die "olddefconfig failed"

step "build"
build_targets=(bzImage)
[ $bootloader -eq 1 ] && build_targets+=(modules)
make -C "$tree" -j"$jobs" "${build_targets[@]}" > "$out/build.log" 2>&1 || {
	tail -20 "$out/build.log"
	die "kernel build failed, see $out/build.log"
}
echo "built with $(grep -c 'warning:' "$out/build.log") warnings"

if [ $bootloader -eq 1 ]; then
	step "overlay"
else
	step "boot"
fi
overlay="$out/disk.qcow2"
rm -f "$overlay" "$out/serial.log" "$out/console.ppm" "$out/rotated.ppm" \
	"$out/login.ppm" "$out/monitor.sock" "$out/monitor-serial.sock" "$out/qemu.log"
qemu-img create -q -f qcow2 -F raw -b "$base" "$overlay" >/dev/null ||
	die "cannot create the overlay"

if [ $bootloader -eq 1 ]; then
	step "install"
	staging="$out/staging"
	staging_image="$out/staging.img"
	install_out="$out/install-vm"
	rm -rf "$staging" "$staging_image" "$install_out"
	mkdir -p "$staging" "$install_out"
	install_serial_socket="$lab/.cjktty-$version-install.sock"
	rm -f "$install_serial_socket"
	make -C "$tree" modules_install INSTALL_MOD_PATH="$staging" \
		> "$out/modules-install.log" 2>&1 || die "modules_install failed"
	kernel_release=$(make -s -C "$tree" kernelrelease) || die "cannot read the kernel release"
	install -Dm0644 "$tree/arch/x86/boot/bzImage" "$staging/kernel/bzImage"
	install -m0644 "$tree/System.map" "$staging/kernel/System.map"
	cp "$tree/arch/x86/boot/bzImage" "$out/bzImage"
	staging_size=$(( $(du -sm "$staging" | cut -f1) + 256 ))
	truncate -s "${staging_size}M" "$staging_image"
	mkfs.ext4 -q -F -L cjktty-staging -d "$staging" "$staging_image" ||
		die "cannot build the kernel staging filesystem"
	cp -f "$ovmf_vars" "$install_out/OVMF_VARS.fd"
	qemu-system-x86_64 -enable-kvm -m 2G -smp 2 -machine q35 \
		-drive "if=pflash,format=qcow2,readonly=on,file=$ovmf_code" \
		-drive "if=pflash,format=raw,file=$install_out/OVMF_VARS.fd" \
		-drive "file=$overlay,format=qcow2,if=virtio" \
		-drive "file=$staging_image,format=raw,if=virtio" \
		-kernel "$tree/arch/x86/boot/bzImage" \
		-append 'root=/dev/vda2 rw console=tty0 console=ttyS0,115200' \
		-vga virtio -display none \
		-serial "unix:$install_serial_socket,server,nowait" \
		-monitor none > "$install_out/qemu.log" 2>&1 &
	install_qemu=$!
	CJKTTY_SERIAL_SOCKET="$install_serial_socket" \
		python3 "$repo/tools/drive-system.py" "$install_out" "$boot_timeout" \
		--install "$kernel_release"
	install_result=$?
	kill $install_qemu 2>/dev/null
	wait $install_qemu 2>/dev/null
	[ $install_result -eq 0 ] ||
		die "$version: installkernel failed in the guest; see $install_out/serial.log"
	rm -rf "$staging" "$staging_image"
	step "boot"
fi

cp -f "$ovmf_vars" "$out/OVMF_VARS.fd"
serial_socket="$lab/.cjktty-$version-serial.sock"
monitor_socket="$lab/.cjktty-$version-monitor.sock"
rm -f "$serial_socket" "$monitor_socket"

qemu_args=(
	-enable-kvm -m 2G -smp 2 -machine q35
	-drive "if=pflash,format=qcow2,readonly=on,file=$ovmf_code"
	-drive "if=pflash,format=raw,file=$out/OVMF_VARS.fd"
	-drive "file=$overlay,format=qcow2,if=virtio"
	-vga virtio -display none
	-serial "unix:$serial_socket,server,nowait"
	-monitor "unix:$monitor_socket,server,nowait"
)
if [ $bootloader -eq 1 ]; then
	qemu_args+=(-boot order=c)
else
	qemu_args+=(
		-kernel "$tree/arch/x86/boot/bzImage"
		-append 'root=/dev/vda rw console=tty0 console=ttyS0,115200'
	)
fi
qemu-system-x86_64 "${qemu_args[@]}" > "$out/qemu.log" 2>&1 &
qemu=$!

driver_args=("$out" "$boot_timeout")
[ $bootloader -eq 1 ] && driver_args+=(--bootloader "$kernel_release")
test_font=
[ "$cjk32" = 1 ] && test_font=/usr/share/consolefonts/latarcyrheb-sun32.psfu.gz
CJKTTY_SERIAL_SOCKET="$serial_socket" CJKTTY_MONITOR_SOCKET="$monitor_socket" \
	CJKTTY_TEST_FONT="$test_font" \
	python3 "$repo/tools/drive-system.py" "${driver_args[@]}"
result=$?

kill $qemu 2>/dev/null
wait $qemu 2>/dev/null
[ $result -eq 0 ] || die "$version: the system test failed; see $out/serial.log"

step "console"
[ -s "$out/login.ppm" ] || die "no login screenshot was captured"
[ -s "$out/console.ppm" ] || die "no console screenshot was captured"
[ -s "$out/rotated.ppm" ] || die "no rotated screenshot was captured"
cell=8x16
[ "$cjk32" = 1 ] && cell=16x32
python3 "$repo/tools/check-console.py" --cell "$cell" "$out/console.ppm" ||
	die "$version: the console did not render CJK after the DRM handover"
python3 "$repo/tools/check-console.py" --rotated --cell "$cell" "$out/rotated.ppm" ||
	die "$version: the console did not render CJK under rotation"

echo
if [ $bootloader -eq 1 ]; then
	echo "$version: PASS (GRUB, installkernel, dracut initramfs, full system test)"
else
	echo "$version: PASS (full system: DRM handover, setfont, chvt, rotation, fbcon rebind)"
fi
echo "screenshots: $out/login.ppm, $out/rotated.ppm and $out/console.ppm"
echo "artifacts in $out"
rm -rf "$tree"
