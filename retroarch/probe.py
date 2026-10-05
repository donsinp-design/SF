"""Work out how RetroArch's FBNeo core stores 3rd Strike's RAM.

    python3 probe.py

Start a round with both players at full health, run this, then follow the prompt.
"""
from ra_link import RetroArch

P1_LIFE, P2_LIFE = 0x02068D0B, 0x020691A3

ra = RetroArch()
if ra.read_raw(P1_LIFE - 0x02000000, 1) is None:
    print("RetroArch didn't return memory. Check Network Commands is ON and a game is running.")
    raise SystemExit(1)

def lives():
    out = {}
    for w in (1, 2, 4):
        ra.swap = w
        a, b = ra.read(P1_LIFE, 1), ra.read(P2_LIFE, 1)
        out[w] = (a[0] if a else None, b[0] if b else None)
    return out

def window():
    return ra.read_raw(P1_LIFE - 0x02000000 - 0x40, 0x80)

before_win = window()
before = lives()
print("At full health:", before)
input("Now let P1 take one hit (any attack), then press Enter here... ")
after = lives()
after_win = window()
print("After the hit: ", after)

best = [w for w in (1, 2, 4) if before[w][0] == 160 and after[w][0] is not None and after[w][0] < 160
        and before[w][1] == 160]
if best:
    print("\nFound it. Run the bot with:\n    python3 ra_bot.py --swap %d" % best[0])
else:
    print("\nNo layout matched. Bytes near P1's life that changed (RetroArch address: before -> after):")
    if before_win and after_win:
        for i, (x, y) in enumerate(zip(before_win, after_win)):
            if x != y:
                print("    %#x: %d -> %d" % (P1_LIFE - 0x02000000 - 0x40 + i, x, y))
    print("Send this output to whoever is helping you.")
