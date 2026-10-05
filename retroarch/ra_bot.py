"""Dudley reaction bot for 3rd Strike on RetroArch (FBNeo core). Offline only.

Same brain as bot/ (learns your attacks, parries them, footsies, whiff punishes),
ported to Python because RetroArch has no Lua. It reads game memory and presses
P2's buttons over RetroArch's local network interface, so it is a frame or two
behind the Lua version: a built-in latency experiment.
"""
import argparse
import json
import os
import random
import time

from ra_link import RetroArch

# --- game memory (sfiii3nr1, same as bot/ai_memory.lua) ---------------------
P_BASE = {1: 0x02068C6C, 2: 0x02069104}
OFF_FLIP, OFF_X, OFF_Y, OFF_LIFE, OFF_POSTURE, OFF_ANIM = 0x0A, 0x64, 0x68, 0x9F, 0x20E, 0x202
READ_LEN = 0x210

# FBNeo's RetroPad layout for 6-button CPS3 games (change if your remap differs)
BUTTONS = {"LP": "Y", "MP": "X", "HP": "L", "LK": "B", "MK": "A", "HK": "R"}
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "threats.json")


def s16(b, o):
    v = (b[o] << 8) | b[o + 1]
    return v - 0x10000 if v & 0x8000 else v


def read_player(ra, n):
    b = ra.read(P_BASE[n], READ_LEN)
    if b is None:
        return None
    return {"x": s16(b, OFF_X), "y": s16(b, OFF_Y), "life": b[OFF_LIFE], "posture": b[OFF_POSTURE],
            "anim": (b[OFF_ANIM] << 8) | b[OFF_ANIM + 1]}


# --- inputs -----------------------------------------------------------------
def frame(d=5, *btn):
    return (d, btn)


def hold(d, n, *btn):
    return [frame(d, *btn)] * n


SUPER = [frame(2), frame(3), frame(6), frame(2), frame(3), frame(6, "HP"), frame(5, "MP"), frame(5, "LP")]
JET_UPPER = [frame(6), frame(2), frame(3, "HP")]
PUNISH = hold(5, 2, "HK") + hold(5, 3) + [frame(6), frame(2), frame(3, "HP")]
POKE = hold(5, 2, "HK")
CONFIRM = hold(2, 2, "LK") + hold(2, 3)


def parry(low):
    return [frame(5), frame(2 if low else 6), frame(5)]


def dir_buttons(d, facing_right):
    fwd, back = ("RIGHT", "LEFT") if facing_right else ("LEFT", "RIGHT")
    return {1: ["DOWN", back], 2: ["DOWN"], 3: ["DOWN", fwd], 4: [back], 5: [], 6: [fwd],
            7: ["UP", back], 8: ["UP"], 9: ["UP", fwd]}[d]


# --- brain (port of bot/ai_brain.lua) ----------------------------------------
class Brain:
    def __init__(self, me, delay_frames, aggression):
        self.me, self.opp = me, 3 - me
        self.queue, self.prev, self.age, self.pending, self.confirm = [], None, 0, None, None
        self.delay, self.history, self.aggression = delay_frames, [], aggression
        self.threats = json.load(open(DATA_FILE)) if os.path.exists(DATA_FILE) else {}

    def save(self):
        json.dump(self.threats, open(DATA_FILE, "w"), indent=1)

    def step(self, live):
        self.history.append(live)
        s = self.history[max(0, len(self.history) - 1 - self.delay)]
        self.history = self.history[-(self.delay + 1):]
        me, op = s[self.me], s[self.opp]
        dist = abs(me["x"] - op["x"])
        key = "%04X" % op["anim"]

        self.age = self.age + 1 if self.prev and self.prev[self.opp]["anim"] == op["anim"] else 0
        if self.prev and me["life"] < self.prev[self.me]["life"]:
            t = self.threats.get(key)
            if self.pending and self.pending == key and t:
                t["low"] = not t["low"]          # parried the wrong height
            elif t:
                t["hit"] = round((t["hit"] * t["seen"] + self.age) / (t["seen"] + 1))
                t["dist"], t["seen"] = max(t["dist"], dist), t["seen"] + 1
            else:
                self.threats[key] = {"hit": self.age, "low": op["posture"] == 0x20, "dist": dist, "seen": 1}
            self.pending = None
        if self.confirm and self.prev and op["life"] < self.confirm:
            self.queue = list(SUPER)
            self.confirm = None
        self.prev = s
        if self.queue:
            return

        t = self.threats.get(key)
        if t and dist <= t["dist"] + 24 and self.age == t["hit"] - 2:
            self.queue, self.pending = parry(t["low"]), key
        elif 40 < op["y"] < 90 and dist < 90:
            self.queue = list(JET_UPPER)
        elif t and self.age > t["hit"] + 2 and dist < t["dist"] + 30:
            self.queue = list(PUNISH)
        elif dist < 60 and random.random() < self.aggression * 0.25:
            self.queue, self.confirm = list(CONFIRM), op["life"]
        else:
            reach = max([110] + [v["dist"] for v in self.threats.values()]) + 6
            if dist > reach + 8:
                self.queue = hold(6, 2)
            elif dist < reach - 8:
                self.queue = hold(4, 2)
            elif dist <= 110 and random.random() < 0.15:
                self.queue = list(POKE)

    def next_input(self, facing_right):
        if not self.queue:
            return []
        d, btns = self.queue.pop(0)
        return dir_buttons(d, facing_right) + [BUTTONS[b] for b in btns]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--player", type=int, default=2)
    ap.add_argument("--swap", type=int, default=4, choices=(1, 2, 4), help="byte layout found by probe.py")
    ap.add_argument("--delay", type=int, default=0, help="simulated extra lag in frames")
    ap.add_argument("--aggression", type=float, default=0.6)
    args = ap.parse_args()

    ra = RetroArch(player=args.player, swap=args.swap)
    brain = Brain(args.player, args.delay, args.aggression)
    print("Running. Ctrl+C to stop. Learned threats:", len(brain.threats))
    frame_time, last_save = 1 / 60, time.time()
    try:
        while True:
            t0 = time.perf_counter()
            p = {1: read_player(ra, 1), 2: read_player(ra, 2)}
            in_round = p[1] and p[2] and p[1]["life"] <= 160 and p[2]["life"] <= 160
            if in_round:
                brain.step(p)
                me, op = p[args.player], p[3 - args.player]
                ra.set_buttons(brain.next_input(me["x"] < op["x"]))
            else:
                brain.queue, brain.prev = [], None
                ra.release_all()
            if time.time() - last_save > 10:
                brain.save()
                last_save = time.time()
            time.sleep(max(0, frame_time - (time.perf_counter() - t0)))
    except KeyboardInterrupt:
        pass
    finally:
        ra.release_all()
        brain.save()


if __name__ == "__main__":
    main()
