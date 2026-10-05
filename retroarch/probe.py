"""Find how RetroArch exposes 3rd Strike's RAM. Run during a round, both players at full health.

    python3 probe.py

Prints RetroArch's raw answers, then the layout where both life bars read 160.
"""
import socket

from ra_link import RetroArch, CMD_PORT

P1_LIFE, P2_LIFE = 0x02068D0B, 0x020691A3


def ask(cmd):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1.0)
    s.sendto((cmd + "\n").encode(), ("127.0.0.1", CMD_PORT))
    try:
        return s.recvfrom(65536)[0].decode(errors="ignore").strip()
    except socket.timeout:
        return None


version = ask("VERSION")
print("VERSION ->", version)
if version is None:
    print("RetroArch is not answering on port %d. Check Network Commands is ON, then fully quit and reopen RetroArch." % CMD_PORT)
    raise SystemExit(1)
print("GET_STATUS ->", ask("GET_STATUS"))
for addr in (P1_LIFE, P1_LIFE - 0x02000000, 0):
    print("READ_CORE_MEMORY %x ->" % addr, ask("READ_CORE_MEMORY %x 4" % addr))

ra = RetroArch()
found = False
for offset in (0x0, 0x02000000):
    for swap in (False, True):
        ra.ram_offset, ra.swap32 = offset, swap
        a, b = ra.read(P1_LIFE, 1), ra.read(P2_LIFE, 1)
        print("offset=%#x swap32=%s -> P1 life %s, P2 life %s" % (offset, swap, a and a[0], b and b[0]))
        if a and b and a[0] == 160 and b[0] == 160:
            print("  ^ looks right:  python3 ra_bot.py --ram-offset %#x%s" % (offset, " --swap32" if swap else ""))
            found = True
if not found:
    print("\nNo layout matched. Send this whole output to whoever is helping you.")
