#!/usr/bin/env python3
"""
Event-driven watcher for ~/JobSearch/JDs/ using macOS kqueue.
Blocks at the kernel level until a file is created/removed in JDs/,
then spawns auto_resume.py to process any unprocessed JDs.
No polling. No StartInterval. Zero CPU between events.
"""

import datetime
import os
import select
import subprocess
import time
from pathlib import Path

HOME       = Path.home()
JDS_DIR    = HOME / "JobSearch/JDs"
SCRIPT     = HOME / ".claude/skills/resume-builder/scripts/auto_resume.py"
LOG        = HOME / ".claude/skills/resume-builder/scripts/auto_resume.log"
CLAUDE_BIN = "/Applications/c11.app/Contents/Resources/bin/claude"


def log(msg):
    ts   = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [watcher] {msg}\n"
    with LOG.open("a") as f:
        f.write(line)
    print(line, end="", flush=True)


def trigger():
    log("JDs directory changed — spawning auto_resume.py")
    env = os.environ.copy()
    env["HOME"] = str(HOME)
    claude_dir = str(Path(CLAUDE_BIN).parent)
    env["PATH"] = f"{claude_dir}:{env.get('PATH', '/usr/local/bin:/usr/bin:/bin')}"
    subprocess.Popen(["python3", str(SCRIPT)], env=env)


def watch():
    kq     = select.kqueue()
    dir_fd = os.open(str(JDS_DIR), os.O_RDONLY)

    # kqueue vnode constants — use raw values for cross-Python-version safety
    EVFILT_VNODE = -4
    EV_ADD       = 0x0001
    EV_CLEAR     = 0x0020
    NOTE_WRITE   = 0x0002
    NOTE_EXTEND  = 0x0004

    ev = select.kevent(
        dir_fd,
        filter=EVFILT_VNODE,
        flags=EV_ADD | EV_CLEAR,
        fflags=NOTE_WRITE | NOTE_EXTEND,
    )
    kq.control([ev], 0)
    log(f"Watching {JDS_DIR}")

    while True:
        events = kq.control(None, 1, None)  # blocks until kernel event
        if events:
            time.sleep(2)   # let the file finish writing before processing
            trigger()


if __name__ == "__main__":
    watch()
