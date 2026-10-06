"""Learns the opponent's moves from the screen alone, while playing.

Every time the opponent starts moving near Dudley it snapshots their pose a
couple of frames in (the backend's opponent fingerprint) and then watches what
happens: did Dudley get hit, how many frames later, and what was he holding?
Similar poses are grouped into one "move". Per move it learns:

  reach   - hit rate by distance; a move that never connects from a distance
            is a bait there and gets ignored or whiff-punished
  timing  - frames from start to hit, so the low parry can be timed
  height  - getting hit through a crouching block means overhead: stand-block it
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

DIST_BUCKET = 24  # pixels per distance bucket


class Move:
    def __init__(self, fp, data=None):
        self.fp = np.asarray(fp, dtype=np.float32)
        d = data or {}
        self.seen = d.get("seen", 0)
        self.hits = d.get("hits", {})          # bucket -> [hits, seen]
        self.delays = d.get("delays", [])      # frames from start to hit
        self.delays_by_dist = d.get("delays_by_dist", {})  # bucket -> delays (fireballs take longer from further)
        self.through_low_block = d.get("through_low_block", 0)
        self.blocked_low = d.get("blocked_low", 0)

    def to_json(self):
        return {"fp": self.fp.tolist(), "seen": self.seen, "hits": self.hits, "delays": self.delays[-30:], "delays_by_dist": {k: v[-10:] for k, v in self.delays_by_dist.items()},
                "through_low_block": self.through_low_block, "blocked_low": self.blocked_low}

    def hit_rate(self, dist):
        b = str(int(dist // DIST_BUCKET))
        h, n = self.hits.get(b, [0, 0])
        return (h / n) if n else None, n

    def delay(self, dist=None):
        if dist is not None:
            b = self.delays_by_dist.get(str(int(dist // DIST_BUCKET)))
            if b:
                return float(np.median(b))
        return float(np.median(self.delays)) if self.delays else None

    def overhead(self):
        return self.through_low_block >= 2 and self.through_low_block > self.blocked_low


class MoveMemory:
    def __init__(self, path: Path, match_distance=0.08):
        self.path = path
        self.match_distance = match_distance
        self.moves: list[Move] = []
        if path.exists():
            try:
                for m in json.loads(path.read_text()):
                    self.moves.append(Move(m["fp"], m))
            except Exception:
                self.moves = []
        self.event = None
        self.dirty = 0

    def save(self):
        self.path.write_text(json.dumps([m.to_json() for m in self.moves]))

    def match(self, fp):
        if fp is None or not self.moves:
            return None
        v = np.asarray(fp, dtype=np.float32).ravel()
        best, best_d = None, 1e9
        for m in self.moves:
            if m.fp.size != v.size:
                continue
            d = float(np.mean(np.abs(m.fp.ravel() - v)))
            if d < best_d:
                best, best_d = m, d
        return best if best_d <= self.match_distance else None

    # ---- event tracking -------------------------------------------------
    def start(self, frame, dist):
        if self.event is None:
            self.event = {"start": frame, "dist": dist, "move": None, "hit": None, "keys_at_hit": None, "guarded": False}

    def note_keys(self, keys):
        # Holding back means we were blocking: a move that "didn't hit" then
        # proves nothing (it may have been blocked), so it can't count as a miss.
        if self.event is not None and "BACK" in set(keys or ()):
            self.event["guarded"] = True

    def identify(self, fp):
        """Called a couple of frames into the event with the opponent's pose."""
        e = self.event
        if e is None or e["move"] is not None or fp is None:
            return None
        m = self.match(fp)
        if m is None:
            m = Move(np.asarray(fp, dtype=np.float32))
            self.moves.append(m)
        e["move"] = m
        return m

    def note_damage(self, frame, held_keys):
        e = self.event
        if e is not None and e["hit"] is None:
            e["hit"] = frame - e["start"]
            e["keys_at_hit"] = set(held_keys or ())

    def finish_if_due(self, frame, held_keys_now, window=45):
        """Close the event after `window` frames and fold the outcome into the move."""
        e = self.event
        if e is None or frame - e["start"] < window:
            return
        self.event = None
        m = e["move"]
        if m is None:
            return
        m.seen += 1
        b = str(int((e["dist"] or 0) // DIST_BUCKET))
        h, n = m.hits.get(b, [0, 0])
        hit = e["hit"] is not None
        if hit or not e["guarded"]:
            m.hits[b] = [h + (1 if hit else 0), n + 1]
        if hit:
            m.delays.append(e["hit"])
            m.delays_by_dist.setdefault(b, []).append(e["hit"])
            # hit while crouch-blocking or low-parrying: it must hit high (overhead)
            if "DOWN" in (e["keys_at_hit"] or set()):
                m.through_low_block += 1
        elif {"DOWN", "BACK"} <= set(held_keys_now or ()):
            m.blocked_low += 1
        self.dirty += 1
        if self.dirty >= 5:
            self.save()
            self.dirty = 0
