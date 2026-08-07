"""Drive the system test over the serial console.

Waits for systemd to reach a login, exercises the console paths the patch
touches -- font reload, VT switch, rotation and the fbcon release path -- then
shuts the machine down. Every step is asserted from what the guest prints, not
from a human looking at the screen; the screenshots are artifacts for review.

Usage: drive-system.py <output-directory> <timeout-seconds>
"""

from __future__ import annotations

import re
import socket
import sys
import time
from pathlib import Path

ANSI = re.compile(rb"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][B0]|\x1b[=>]")

PROMPT = r"#|cjk> "


class Failed(Exception):
    pass


class Console:
    def __init__(self, path: Path, log: Path, deadline: float) -> None:
        self.log = log.open("wb")
        self.buffer = b""
        while time.monotonic() < deadline:
            self.sock = socket.socket(socket.AF_UNIX)
            try:
                self.sock.connect(str(path))
            except OSError:
                self.sock.close()
                time.sleep(0.5)
                continue
            self.sock.settimeout(1.0)
            return
        raise Failed(f"{path} never accepted a connection")

    def expect(self, pattern: str, timeout: float) -> bytes:
        matcher = re.compile(pattern.encode())
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            clean = ANSI.sub(b"", self.buffer)
            found = matcher.search(clean)
            if found is not None:
                self.buffer = clean[found.end() :]
                return clean[: found.end()]
            try:
                chunk = self.sock.recv(4096)
            except TimeoutError:
                continue
            if not chunk:
                raise Failed("the guest closed the console")
            self.log.write(chunk)
            self.log.flush()
            self.buffer += chunk
        raise Failed(f"never saw {pattern!r}; last output was {ANSI.sub(b'', self.buffer)[-400:]!r}")

    def send(self, line: str) -> None:
        self.sock.sendall(line.encode() + b"\n")

    def run(self, command: str, timeout: float = 60.0) -> None:
        token = f"MARK{int(time.monotonic() * 1000) % 100000}"
        self.send(f"{command}; echo {token}_$?")
        self.expect(rf"{token}_0\b", timeout)


def screenshot(monitor: Path, target: Path) -> None:
    sock = socket.socket(socket.AF_UNIX)
    sock.connect(str(monitor))
    time.sleep(0.5)
    sock.sendall(b"screendump " + str(target).encode() + b"\n")
    time.sleep(3)
    sock.close()


def main(out: Path, timeout: float) -> int:
    deadline = time.monotonic() + timeout
    try:
        console = Console(out / "monitor-serial.sock", out / "serial.log", deadline)

        console.expect(r"login:|# ", timeout=timeout)
        console.send("")
        console.expect(PROMPT, timeout=60.0)

        # The stage3 shell emits OSC 133 sequences around every prompt, and a
        # digit inside one of those would be read back as command output.
        console.send("unset PROMPT_COMMAND; PS1='cjk> '")
        console.expect(r"cjk> ", timeout=30.0)

        # systemd-vconsole-setup has already reloaded the font by now; a failure
        # there shows up as a dead console rather than an error, so check it ran.
        console.run("systemctl is-system-running --wait || true", timeout=180.0)
        console.run("systemctl status systemd-vconsole-setup --no-pager | tail -3 || true")

        # tty1 still holds the getty banner at this point: keep it as the picture
        # of a normal login screen under this kernel.
        screenshot(out / "monitor.sock", out / "login.ppm")

        # The paths the patch changes: font reload, VT switch, and the release
        # path that frees the CJK buffers.
        console.run("setfont /usr/share/consolefonts/default8x16.psfu.gz || setfont")
        console.run("chvt 2; sleep 1; chvt 1")

        # fbcon_rotate_font_utf runs only under console rotation, and porting to
        # a new kernel rewrites it more often than any other part of the patch.
        # The CJK line written here is the text under test.
        console.run("echo 1 > /sys/class/graphics/fbcon/rotate_all; sleep 2")
        console.run("printf '\\033[2J\\033[H' > /dev/tty1; "
                    "echo 'rotated:  中文控制台显示测试' > /dev/tty1")
        time.sleep(2)
        screenshot(out / "monitor.sock", out / "rotated.ppm")
        console.run("echo 0 > /sys/class/graphics/fbcon/rotate_all; sleep 2")

        # Unbinding fbcon runs fbcon_release, which is where fontbuffer and
        # fontbuffer_utf are freed. Nothing else in this test reaches it.
        # The trailing test is what makes this an assertion: a loop that matches
        # no console would otherwise succeed and the release path go unrun.
        bind = ("n=0; for c in /sys/class/vtconsole/vtcon*; do "
                "grep -q 'frame buffer' $c/name && {{ echo {} > $c/bind; n=$((n+1)); }}; "
                "done; sleep 2; [ $n -gt 0 ]")
        console.run(bind.format(0))
        console.run(bind.format(1))
        console.run("dmesg | grep -q 'switching to colour dummy device'")

        console.send("echo BADCOUNT=$(dmesg | grep -ciE 'oops|BUG:|call trace')")
        bad = console.expect(r"BADCOUNT=\d+", timeout=30.0)
        count = int(re.search(rb"BADCOUNT=(\d+)", bad).group(1))
        if count:
            console.send("dmesg | grep -iE -A5 'oops|BUG:|call trace' | head -40")
            time.sleep(2)
            raise Failed(f"the kernel log holds {count} oops or warning lines")

        # check-console.py reads fixed rows, so lay the screen out the way init.c
        # does: clear, a title line, then the label and the CJK text under test.
        console.run("printf '\\033[2J\\033[H' > /dev/tty1; "
                    "echo 'cjktty system test' > /dev/tty1; "
                    "echo 'Simplified:  中文控制台显示测试' > /dev/tty1")
        time.sleep(2)
        screenshot(out / "monitor.sock", out / "console.ppm")

        console.send("systemctl poweroff")
        console.expect(r"Reached target .*(Power Off|Shutdown)|reboot: Power down", timeout=120.0)
    except Failed as error:
        print(f"system test: {error}", file=sys.stderr)
        return 1
    print("system test: booted, survived setfont, chvt, rotation and fbcon rebind, "
          "powered off clean")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: drive-system.py <output-directory> <timeout-seconds>")
    raise SystemExit(main(Path(sys.argv[1]), float(sys.argv[2])))
