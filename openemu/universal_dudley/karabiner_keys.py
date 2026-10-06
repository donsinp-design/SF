"""Press keys through Karabiner's virtual HID keyboard.

OpenEmu ignores keys sent by other programs but accepts real keyboards, and
macOS treats Karabiner's virtual keyboard as real hardware. Karabiner only
accepts commands from root, so the small kbd_bridge helper runs under sudo.
"""
from __future__ import annotations
import atexit
import select
import subprocess
import time
from pathlib import Path

DAEMON = ("/Library/Application Support/org.pqrs/Karabiner-DriverKit-VirtualHIDDevice/Applications/"
          "Karabiner-VirtualHIDDevice-Daemon.app/Contents/MacOS/Karabiner-VirtualHIDDevice-Daemon")
BRIDGE = Path(__file__).resolve().parent.parent / "karabiner_bridge" / "kbd_bridge"

# HID keyboard usage IDs
USAGE = {chr(ord("a") + i): 0x04 + i for i in range(26)}
USAGE.update({"1": 0x1E, "2": 0x1F, "3": 0x20, "4": 0x21, "5": 0x22, "6": 0x23, "7": 0x24, "8": 0x25,
              "9": 0x26, "0": 0x27, "return": 0x28, "enter": 0x28, "escape": 0x29, "tab": 0x2B,
              "space": 0x2C, "-": 0x2D, "=": 0x2E, "[": 0x2F, "]": 0x30, ";": 0x33, ",": 0x36,
              ".": 0x37, "/": 0x38, "right": 0x4F, "left": 0x50, "down": 0x51, "up": 0x52})


class KarabinerKeys:
    def __init__(self):
        if not BRIDGE.exists():
            raise RuntimeError("The Karabiner key bridge isn't built yet. Double-click setup_karabiner.command first.")
        if not Path(DAEMON).exists():
            raise RuntimeError("Karabiner's virtual keyboard driver isn't installed. Run setup_karabiner.command first.")
        # a bridge left over from a crashed run can keep keys held down
        subprocess.call(["sudo", "killall", "kbd_bridge"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if subprocess.call(["pgrep", "-f", "Karabiner-VirtualHIDDevice-Daemon"], stdout=subprocess.DEVNULL) != 0:
            print("Starting Karabiner's virtual keyboard daemon (may ask for your Mac password)...")
            subprocess.call(["sudo", "-b", DAEMON], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
        self.proc = subprocess.Popen(["sudo", str(BRIDGE)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     text=True, bufsize=1)
        deadline = time.time() + 15
        while time.time() < deadline:
            r, _, _ = select.select([self.proc.stdout], [], [], 0.5)
            if r and "READY" in self.proc.stdout.readline():
                print("Karabiner virtual keyboard connected.")
                atexit.register(self.close)
                return
            if self.proc.poll() is not None:
                break
        raise RuntimeError("Karabiner's virtual keyboard didn't come up. In System Settings > Privacy & Security, "
                           "allow the Karabiner system extension, restart, and try again.")

    def hold(self, keys):
        usages = []
        for k in keys:
            u = USAGE.get(str(k).lower())
            if u is None:
                raise KeyError(f"No HID usage for key {k!r}")
            usages.append(str(u))
        self.proc.stdin.write("k " + " ".join(usages) + "\n")
        self.proc.stdin.flush()

    def close(self):
        try:
            self.proc.stdin.write("q\n")
            self.proc.stdin.flush()
            self.proc.wait(timeout=2)
        except Exception:
            self.proc.kill()
