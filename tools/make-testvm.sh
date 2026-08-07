#!/bin/bash
# Build the base image the system test boots.
#
# Usage: tools/make-testvm.sh [--force]
#
# One ext4 image holding a Gentoo systemd userland, built once and reused. The
# kernel is never installed into it: test-system.sh passes the kernel on the
# QEMU command line and gives each run its own qcow2 overlay, so swapping
# kernels costs nothing and no run can damage the base.
set -uo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
lab=${CJKTTY_LAB:-$(cd "$repo/.." && pwd)/lab}
mirror=${GENTOO_MIRROR:-https://distfiles.gentoo.org}
size=${IMAGE_SIZE:-6G}

base="$lab/testvm/base.img"
root="$lab/testvm/root"

die() { echo "$*" >&2; exit 1; }
step() { printf '\n== %s\n' "$*"; }

[ "${1:-}" = "--force" ] && rm -rf "$lab/testvm"
[ -f "$base" ] && { echo "$base already exists; pass --force to rebuild"; exit 0; }

for tool in curl tar mkfs.ext4 sudo; do
	command -v "$tool" >/dev/null || die "$tool is not installed"
done

mkdir -p "$lab/testvm"

step "stage3"
pointer="$lab/testvm/latest-stage3.txt"
curl -fsS -o "$pointer" \
	"$mirror/releases/amd64/autobuilds/latest-stage3-amd64-systemd.txt" ||
	die "cannot fetch the stage3 pointer"
# The pointer is PGP clearsigned, so pick the path out rather than the first line.
relative=$(grep -oE '[0-9]{8}T[0-9]{6}Z/stage3-amd64-systemd-[^ ]+\.tar\.xz' "$pointer" | head -1)
[ -n "$relative" ] || die "the stage3 pointer is empty"
tarball="$lab/testvm/$(basename "$relative")"
[ -f "$tarball" ] ||
	curl -fL# -o "$tarball" "$mirror/releases/amd64/autobuilds/$relative" ||
	die "cannot download the stage3"

step "unpack"
sudo rm -rf "$root"
sudo mkdir -p "$root"
sudo tar -xpf "$tarball" -C "$root" --xattrs-include='*.*' --numeric-owner ||
	die "cannot unpack the stage3"

step "configure"
# Root logs in on the serial port with no password: the test drives the machine
# over ttyS0 and nothing here is ever exposed off the host.
sudo sed -i 's|^root:[^:]*:|root::|' "$root/etc/shadow"
echo cjktty-test | sudo tee "$root/etc/hostname" >/dev/null
printf '/dev/vda / ext4 defaults,noatime 0 1\n' | sudo tee "$root/etc/fstab" >/dev/null
sudo ln -sf /usr/lib/systemd/system/serial-getty@.service \
	"$root/etc/systemd/system/getty.target.wants/serial-getty@ttyS0.service"
sudo mkdir -p "$root/etc/systemd/system/serial-getty@ttyS0.service.d"
printf '[Service]\nExecStart=\nExecStart=-/sbin/agetty -o "-p -- \\\\u" --autologin root --keep-baud 115200,57600,38400,9600 %%I $TERM\n' |
	sudo tee "$root/etc/systemd/system/serial-getty@ttyS0.service.d/autologin.conf" >/dev/null
# The patch only has 8x16 and 16x32 glyphs, so let systemd-vconsole-setup run
# with a size it supports rather than whatever the stage3 defaults to.
printf 'FONT=LatArCyrHeb-16\nKEYMAP=us\n' | sudo tee "$root/etc/vconsole.conf" >/dev/null

step "image"
sudo mkfs.ext4 -q -F -L cjktty-test -d "$root" "$base" "$size" ||
	die "cannot build the image"
sudo chown "$(id -u):$(id -g)" "$base"
sudo rm -rf "$root"

echo
echo "base image: $base ($(du -h "$base" | cut -f1))"
echo "now run: tools/test-system.sh <kernel-version>"
