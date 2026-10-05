"""Find how RetroArch exposes 3rd Strike's RAM. Run during a round, both players at full health.

    python3 probe.py

It tries common layouts and prints the one where both life bars read 160 (full health).
Copy the suggested --ram-offset / --swap32 into ra_bot.py's command line.
"""
from ra_link import RetroArch

P1_LIFE, P2_LIFE = 0x02068D0B, 0x020691A3

ra = RetroArch()
if ra.read_raw(0, 1) is None:
    print("No answer from RetroArch. Turn on Settings > Network > Network Commands, then restart content.")
    raise SystemExit(1)

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
    print("\nNo layout matched. The FBNeo core may not expose CPS3 RAM to RetroArch;"
          " send this output to whoever is helping you.")
