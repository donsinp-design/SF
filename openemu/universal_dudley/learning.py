from __future__ import annotations
import base64, json, time, shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import numpy as np

@dataclass
class EventContext:
    emulator: str
    player: int
    confidence: str
    frame: int
    action: str
    me_life: Optional[float]
    opp_life: Optional[float]
    dist: Optional[float]
    opp_anim: Optional[int] = None
    opp_posture: Optional[int] = None
    facing_right: Optional[bool] = None

class Learner:
    def __init__(self, saved_dir: Path):
        self.saved_dir = saved_dir
        saved_dir.mkdir(parents=True, exist_ok=True)
        self.json_path = saved_dir / "dudley_learning.json"
        self.txt_path = saved_dir / "dudley_learning.txt"
        self.data = {
            "version": 3,
            "hits_taken": 0,
            "whiffs": 0,
            "hits_landed": 0,
            "exact_threats": {},
            "visual_threats": [],
            "range": {}
        }
        if self.json_path.exists():
            try:
                old = json.loads(self.json_path.read_text())
                if isinstance(old, dict):
                    self.data.update(old)
            except Exception:
                pass
        if int(self.data.get("version",1))<3:
            # v2's whole-screen fingerprint and frame-difference health detector
            # poisoned visual memory with false hits. Preserve it for diagnosis,
            # then start the corrected local-opponent model cleanly.
            if self.json_path.exists():
                shutil.copy2(self.json_path,self.saved_dir/"dudley_learning.v2_poisoned_backup.json")
            if self.txt_path.exists():
                shutil.copy2(self.txt_path,self.saved_dir/"dudley_learning.v2_poisoned_backup.txt")
            self.data.update({"version":3,"hits_taken":0,"whiffs":0,"hits_landed":0,
                              "visual_threats":[],"range":{}})
            self.txt_path.write_text(
                "UNIVERSAL DUDLEY LEARNING LOG — VISUAL MODEL V3\n"
                "Old false-hit memory was backed up and reset.\n\n"
            )
        if not self.txt_path.exists():
            self.txt_path.write_text(
                "UNIVERSAL DUDLEY LEARNING LOG\n"
                "This file explains hits, whiffs, and corrections.\n\n"
            )

    def save(self):
        tmp = self.json_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, indent=2))
        tmp.replace(self.json_path)

    def _append(self, lines):
        with self.txt_path.open("a") as f:
            f.write("\n".join(str(x) for x in lines))
            f.write("\n\n")

    @staticmethod
    def encode_fp(fp: np.ndarray) -> str:
        q = np.clip(np.asarray(fp) * 255.0, 0, 255).astype(np.uint8)
        return base64.b64encode(q.tobytes()).decode("ascii")

    @staticmethod
    def decode_fp(text: str, size: int) -> np.ndarray:
        raw = base64.b64decode(text.encode("ascii"))
        arr = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) / 255.0
        if arr.size != size:
            raise ValueError("fingerprint size mismatch")
        return arr

    def range_allows(self, action: str, dist: Optional[float]) -> bool:
        if dist is None:
            return True
        r = self.data["range"].get(action, {})
        nearest_whiff = r.get("nearest_whiff")
        farthest_hit = r.get("farthest_hit")
        # Be conservative: once a whiff boundary is learned, stay 4 units inside it.
        if nearest_whiff is not None and dist >= nearest_whiff - 4:
            return False
        # If we only know successful reach, don't extend much beyond it.
        if farthest_hit is not None and r.get("attempts", 0) >= 4 and dist > farthest_hit + 4:
            return False
        return True

    def note_landed(self, ctx: EventContext):
        self.data["hits_landed"] += 1
        r = self.data["range"].setdefault(ctx.action, {"attempts":0})
        r["attempts"] = r.get("attempts", 0) + 1
        if ctx.dist is not None:
            r["farthest_hit"] = max(float(ctx.dist), float(r.get("farthest_hit", -1)))
        self.save()

    def note_whiff(self, ctx: EventContext):
        self.data["whiffs"] += 1
        r = self.data["range"].setdefault(ctx.action, {"attempts":0})
        r["attempts"] = r.get("attempts", 0) + 1
        if ctx.dist is not None:
            old = r.get("nearest_whiff")
            r["nearest_whiff"] = float(ctx.dist) if old is None else min(float(old), float(ctx.dist))
        self._append([
            f"WHIFF #{self.data['whiffs']}",
            f"emulator: {ctx.emulator}  player: P{ctx.player}  confidence: {ctx.confidence}",
            f"frame: {ctx.frame}  action: {ctx.action}",
            f"distance: {ctx.dist if ctx.dist is not None else 'visual/unknown'}",
            "ROOT CAUSE: ATTACK_OUT_OF_RANGE",
            "CORRECTION: shrink this action's learned usable range; do not repeat it from this far away.",
        ])
        self.save()

    def _root_cause(self, ctx: EventContext):
        a = (ctx.action or "").lower()
        if "block" in a or "guard" in a or "parry" in a:
            return ("DEFENCE_TIMING_FAILED",
                    "defend earlier/longer against this learned threat; prefer safe guard when precision is uncertain.")
        if any(k in a for k in ("hk","mp","lk","upper","super","attack","poke","pressure")):
            return ("ATTACKED_INTO_THREAT",
                    "penalise this offensive commitment and give the learned threat defensive priority.")
        if any(k in a for k in ("walk","dash","move","advance")):
            return ("MOVEMENT_EXPOSED",
                    "cancel movement and guard when this threat state appears.")
        return ("MISSED_DEFENCE",
                "reserve the next occurrence of this state for guard/parry instead of neutral.")

    def note_hit_taken(self, ctx: EventContext, exact_key=None, visual_fp=None,
                       hit_age=None, low=None, ranged=None):
        self.data["hits_taken"] += 1
        cause, correction = self._root_cause(ctx)
        if exact_key is not None:
            t = self.data["exact_threats"].setdefault(str(exact_key), {
                "seen": 0, "hit_age": hit_age if hit_age is not None else 3,
                "low": bool(low), "ranged": bool(ranged)
            })
            seen = int(t.get("seen", 0))
            if hit_age is not None:
                t["hit_age"] = round((float(t.get("hit_age", hit_age))*seen + hit_age) / (seen + 1), 2)
            t["low"] = bool(low) if low is not None else bool(t.get("low", False))
            t["ranged"] = bool(ranged) if ranged is not None else bool(t.get("ranged", False))
            t["seen"] = seen + 1

        if visual_fp is not None:
            encoded = self.encode_fp(visual_fp)
            item={
                "fp": encoded,
                "seen": 1,
                "low": True if low is None else bool(low),
                "ranged": bool(ranged),
                "dist":ctx.dist,
                "source": ctx.emulator,
                "created": time.time(),
            }
            # Merge nearly identical local poses instead of flooding memory.
            match,score=self.nearest_visual_threat(visual_fp,.025,ctx.dist)
            if match is not None:
                match["seen"]=int(match.get("seen",1))+1
            else:
                self.data["visual_threats"].append(item)
                self.data["visual_threats"] = self.data["visual_threats"][-120:]

        self._append([
            f"HIT TAKEN #{self.data['hits_taken']}",
            f"emulator: {ctx.emulator}  player: P{ctx.player}",
            f"confidence: {ctx.confidence}",
            f"frame: {ctx.frame}",
            f"Dudley previous action: {ctx.action}",
            f"life: {ctx.me_life}  opponent life: {ctx.opp_life}",
            f"distance: {ctx.dist if ctx.dist is not None else 'visual/estimated'}",
            f"opponent animation: {hex(ctx.opp_anim) if ctx.opp_anim is not None else 'visual'}",
            f"opponent posture: {hex(ctx.opp_posture) if ctx.opp_posture is not None else 'visual'}",
            f"ROOT CAUSE: {cause}",
            f"CORRECTION: {correction}",
            "LEARNING: this pre-hit state is now stored as a threat and gets defensive priority next time.",
        ])
        self.save()

    def exact_threat(self, key):
        return self.data["exact_threats"].get(str(key))

    def nearest_visual_threat(self, fp: np.ndarray, threshold: float, dist=None):
        items = self.data.get("visual_threats", [])
        if not items:
            return None, None
        flat = np.asarray(fp, dtype=np.float32).ravel()
        best = None
        best_d = None
        for t in items:
            td=t.get("dist")
            if dist is not None and td is not None and abs(float(dist)-float(td))>22:
                continue
            try:
                other = self.decode_fp(t["fp"], flat.size)
            except Exception:
                continue
            d = float(np.mean(np.abs(flat - other)))
            if best_d is None or d < best_d:
                best, best_d = t, d
        if best_d is not None and best_d <= threshold:
            return best, best_d
        return None, best_d
