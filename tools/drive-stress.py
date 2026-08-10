#!/usr/bin/env python3
"""Drive a KASAN kernel through the paths cjktty changes and read dmesg after."""
import re
import socket
import sys
import time
from pathlib import Path

PROMPT = r"cjk> "


class Failed(Exception):
    pass


class Console:
    def __init__(self, path, log, deadline):
        self.sock = socket.socket(socket.AF_UNIX)
        while True:
            try:
                self.sock.connect(str(path))
                break
            except OSError:
                if time.time() > deadline:
                    raise Failed(f"cannot connect to {path}")
                time.sleep(0.5)
        self.sock.settimeout(1.0)
        self.buf = b""
        self.log = open(log, "ab")

    def expect(self, pattern, timeout):
        end = time.time() + timeout
        rx = re.compile(pattern.encode())
        while True:
            m = rx.search(self.buf)
            if m:
                self.buf = self.buf[m.end():]
                return m.group(0)
            if time.time() > end:
                raise Failed(f"timeout waiting for {pattern!r}; tail={self.buf[-400:]!r}")
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                raise Failed("the guest closed the serial connection")
            self.buf += chunk
            self.log.write(chunk)
            self.log.flush()

    def send(self, line):
        self.sock.sendall(line.encode() + b"\n")

    def run(self, command, timeout=120.0):
        token = f"OK{int(time.time() * 1000) % 100000}"
        self.send(f"{command}; echo {token}_$?")
        out = self.expect(rf"{token}_\d+\b", timeout)
        code = int(out.decode().rsplit("_", 1)[1])
        if code != 0:
            raise Failed(f"`{command}` exited {code}")


def main(out_dir, timeout):
    out = Path(out_dir)
    deadline = time.time() + timeout
    con = Console(out / "serial.sock", out / "serial.log", deadline)
    con.expect(r"login:", timeout=timeout)
    # the stage3 prompt carries colour escapes, so match on our own PS1 instead
    time.sleep(5)
    con.send("export PS1='cjk> '")
    con.expect(PROMPT, timeout=60.0)
    con.send("")
    con.expect(PROMPT, timeout=30.0)

    con.run("mount -t debugfs none /sys/kernel/debug 2>/dev/null; true")
    con.run("dmesg -n 7")

    # every loop below hits a path this patch changed
    con.run("for i in 1 2 3 4 5 6 7 8; do setfont; setfont /usr/share/consolefonts/*.psf* 2>/dev/null || true; done", 300)
    con.run("for i in $(seq 1 20); do chvt 2; chvt 3; chvt 1; done", 300)
    con.run("for r in 0 1 2 3 0 1 2 3; do echo $r > /sys/class/graphics/fbcon/rotate_all; done", 300)
    con.run("for i in 1 2 3; do for c in /sys/class/vtconsole/vtcon*; do "
            "grep -q 'frame buffer' $c/name && { echo 0 > $c/bind; sleep 1; echo 1 > $c/bind; sleep 1; }; done; done", 300)
    con.run("for i in $(seq 1 60); do printf '\\u4e2d\\u6587\\u63a7\\u5236\\u53f0\\u663e\\u793a\\u6d4b\\u8bd5 %s\\n' $i; done > /dev/tty1", 120)
    con.run("for s in '80 25' '100 30' '80 25'; do stty -F /dev/tty1 cols ${s% *} rows ${s#* } 2>/dev/null || true; done")

    con.run("sync; sleep 2")
    # kmemleak needs two scans separated by a grace period
    con.run("echo scan > /sys/kernel/debug/kmemleak 2>/dev/null || true", 300)
    con.run("sleep 15")
    con.run("echo scan > /sys/kernel/debug/kmemleak 2>/dev/null || true", 300)

    con.send("echo LEAKSTART; cat /sys/kernel/debug/kmemleak 2>/dev/null | head -60; echo LEAKEND")
    con.expect(r"LEAKEND", timeout=120.0)
    con.send("echo BADSTART; dmesg | grep -E 'KASAN|BUG:|WARNING:|possible recursive locking|INFO: trying to register' | head -40; echo BADEND")
    con.expect(r"BADEND", timeout=120.0)
    con.run("systemctl poweroff --no-block || poweroff -f", 30)
    try:
        con.expect(r"reboot: Power down|Power Off", timeout=180.0)
    except Failed:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1], float(sys.argv[2])))
    except Failed as e:
        print(f"stress driver failed: {e}", file=sys.stderr)
        sys.exit(1)
