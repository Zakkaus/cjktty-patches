#!/usr/bin/env python3
"""The one fbcon bind assertion both console drivers run in the guest."""

from __future__ import annotations

#: Every framebuffer console sysfs directory.
VTCONSOLE_GLOB = "/sys/class/vtconsole/vtcon*"


def rebind_command(value: int, glob: str = VTCONSOLE_GLOB, settle: int = 2) -> str:
    """Write `value` to every framebuffer console's bind and prove it took.

    A loop matching no console exits 0 and a failed write leaves the console
    attached, so the count and the read-back are both required: without them a
    run can report success having never reached fbcon_release().
    """
    return (
        f"n=0; failed=0; for c in {glob}; do "
        "grep -q 'frame buffer' $c/name || continue; "
        f"echo {value} > $c/bind || failed=1; "
        f'[ "$(cat $c/bind)" = {value} ] && n=$((n+1)) || failed=1; '
        f"done; sleep {settle}; [ $n -gt 0 ] && [ $failed -eq 0 ]"
    )
