from __future__ import annotations
from collections import deque
from dataclasses import dataclass
import random
import numpy as np
from .learning import EventContext

@dataclass
class Snapshot:
    frame: int
    me_life: float | None
    opp_life: float | None
    dist: float | None
    opp_anim: int | None
    opp_posture: int | None
    fp: np.ndarray | None
    action: str
    facing_right: bool

class Brain:
    def __init__(self, player, learner, emulator, aggression=0.38, visual_threshold=0.105):
        self.player = player
        self.learner = learner
        self.emulator = emulator
        self.aggression = aggression
        self.visual_threshold = visual_threshold
        self.queue = deque()
        self.history = deque(maxlen=18)
        self.last_state = None
        self.last_action = "idle"
        self.action_started = 0
        self.pending_attack = None
        self.defend_until = -1
        self.anim_key = None
        self.anim_age = 0
        self.last_threat_response = -999

    def _ctx(self, state):
        return EventContext(
            emulator=self.emulator,
            player=self.player,
            confidence=state.get("confidence", "UNKNOWN"),
            frame=state["frame"],
            action=self.last_action,
            me_life=state.get("me_life"),
            opp_life=state.get("opp_life"),
            dist=state.get("dist"),
            opp_anim=state.get("opp_anim"),
            opp_posture=state.get("opp_posture"),
            facing_right=state.get("facing_right"),
        )

    def _q(self, action, frames):
        self.queue.clear()
        for f in frames:
            self.queue.append(tuple(f))
        self.last_action = action
        self.action_started = self.last_state["frame"] if self.last_state else 0

    def _guard(self, state, low=True, frames=10):
        # down-back blocks sweeps and fireballs. For exact mode this is intentionally
        # safer than gambling on a parry until timing has been learned.
        keys = ("DOWN", "BACK") if low else ("BACK",)
        self._q("guard learned threat", [keys] * frames)
        self.defend_until = state["frame"] + frames

    def _poke_hk(self, state):
        if not self.learner.range_allows("HK", state.get("dist")):
            return False
        self._q("HK poke", [("HK",), (), (), (), (), ()])
        self.pending_attack = {
            "action":"HK", "frame":state["frame"], "opp_life":state.get("opp_life"),
            "dist":state.get("dist"), "timeout":state["frame"]+18
        }
        return True

    def _low_poke(self, state):
        if not self.learner.range_allows("2LK", state.get("dist")):
            return False
        self._q("2LK poke", [("DOWN","LK"), (), (), (), ()])
        self.pending_attack = {
            "action":"2LK", "frame":state["frame"], "opp_life":state.get("opp_life"),
            "dist":state.get("dist"), "timeout":state["frame"]+16
        }
        return True

    def _jet_upper(self, state):
        self._q("anti-air Jet Upper", [("FORWARD",), ("DOWN",), ("DOWN","FORWARD","HP"), (), (), ()])

    @staticmethod
    def _jet_motion(button="HP"):
        return [("FORWARD",),("DOWN",),("DOWN","FORWARD",button),(),(),()]

    def _close_combo(self, state):
        # 2LK, 2LK into HP Jet Upper. Visual mode cannot guarantee the confirm,
        # but this is an actual offensive string rather than a lone poke.
        seq=[("DOWN","LK"),(),(),(),("DOWN","LK"),(),()]+self._jet_motion("HP")
        self._q("combo: 2LK 2LK xx HP Jet Upper",seq)
        self.pending_attack={"action":"close combo","frame":state["frame"],
                             "opp_life":state.get("opp_life"),"dist":state.get("dist"),
                             "timeout":state["frame"]+32}

    def _mid_combo(self, state):
        seq=[("MP",),()]+self._jet_motion("HP")
        self._q("combo: MP xx HP Jet Upper",seq)
        self.pending_attack={"action":"mid combo","frame":state["frame"],
                             "opp_life":state.get("opp_life"),"dist":state.get("dist"),
                             "timeout":state["frame"]+26}

    def _parry_punish(self, state):
        seq=[("FORWARD",),(),()]+[("MP",),()]+self._jet_motion("HP")
        self._q("parry attempt > MP xx HP Jet Upper",seq)
        self.pending_attack={"action":"parry punish","frame":state["frame"],
                             "opp_life":state.get("opp_life"),"dist":state.get("dist"),
                             "timeout":state["frame"]+30}

    def _guard_then_punish(self, state, frames=16):
        # Visual mode can't see attack height, and a forward (high) parry loses to
        # sweeps. Hold down-back, which blocks sweeps, lows, mids and fireballs.
        # If the guard held (no damage) their move is usually still recovering,
        # so punish with 2LK 2LK xx Jet Upper when close.
        self._q("guard (down-back)", [("DOWN","BACK")] * frames)
        self.defend_until = state["frame"] + frames
        self.punish_check = {"frame": state["frame"] + frames, "life": state.get("me_life")}

    def preempt(self, state):
        """Called every frame before the queue advances: drop walking/neutral
        movement the moment the opponent starts moving near us."""
        if self.emulator == "retroarch" or not self.queue:
            return
        if not (self.last_action.startswith("walk") or "neutral" in self.last_action):
            return
        d = state.get("dist"); motion = float(state.get("opp_motion") or 0.0)
        if d is not None and d < 130 and motion > .045:
            self.queue.clear()
            self._guard_then_punish(state)

    def _walk(self, toward):
        self._q("walk in" if toward else "walk out", [(("FORWARD",) if toward else ("BACK",))] * 3)

    def _learn_from_damage(self, state):
        if self.last_state is None:
            return
        ml = state.get("me_life")
        old = self.last_state.get("me_life")
        if ml is None or old is None or ml >= old - 0.2:
            return
        # A simultaneous visual drop in both bars is a screen/HUD transition,
        # not evidence that Dudley was hit.
        ol=state.get("opp_life")
        old_ol=self.last_state.get("opp_life")
        if ol is not None and old_ol is not None and ol<old_ol-.2:
            return

        # Use a pre-hit snapshot so the bot learns what led into the hit, not only hit-stop.
        snap = self.history[-5] if len(self.history) >= 5 else (self.history[0] if self.history else None)
        if snap is None:
            return
        exact_key = snap.opp_anim if state.get("exact") and snap.opp_anim is not None else None
        low = bool((snap.opp_posture or 0) in (0x20, 0x22, 0x24))
        ranged = bool(snap.dist is not None and snap.dist > 125)
        # In visual mode default to low guard because down-back safely covers the user's
        # two concrete failures: sweeps and fireballs.
        if not state.get("exact"):
            low = True
        ctx = EventContext(
            emulator=self.emulator, player=self.player,
            confidence=state.get("confidence","UNKNOWN"),
            frame=state["frame"], action=snap.action,
            me_life=ml, opp_life=state.get("opp_life"), dist=snap.dist,
            opp_anim=snap.opp_anim, opp_posture=snap.opp_posture,
            facing_right=snap.facing_right
        )
        self.learner.note_hit_taken(
            ctx, exact_key=exact_key,
            visual_fp=snap.fp if not state.get("exact") else None,
            hit_age=self.anim_age, low=low, ranged=ranged
        )
        # Immediate correction: stop whatever we were doing and guard.
        self.queue.clear()
        self._guard(state, low=True, frames=12)

    def _learn_attack_result(self, state):
        p = self.pending_attack
        if not p:
            return
        ol = state.get("opp_life")
        if p["opp_life"] is not None and ol is not None and ol < p["opp_life"] - 0.2:
            ctx = self._ctx(state)
            ctx.action = p["action"]
            ctx.dist = p["dist"]
            self.learner.note_landed(ctx)
            self.pending_attack = None
        elif state["frame"] >= p["timeout"]:
            ctx = self._ctx(state)
            ctx.action = p["action"]
            ctx.dist = p["dist"]
            self.learner.note_whiff(ctx)
            self.pending_attack = None

    def _threat_now(self, state):
        if state.get("exact") and state.get("opp_anim") is not None:
            t = self.learner.exact_threat(state["opp_anim"])
            if t:
                hit_age = float(t.get("hit_age", 3))
                if self.anim_age >= max(0, hit_age - 3):
                    return t, 0.0
        fp = state.get("fp")
        if fp is not None:
            return self.learner.nearest_visual_threat(fp,self.visual_threshold,state.get("dist"))
        return None, None

    def observe(self, state):
        # Animation age in exact mode.
        key = state.get("opp_anim")
        if key is not None and key == self.anim_key:
            self.anim_age += 1
        else:
            self.anim_key = key
            self.anim_age = 0

        self._learn_from_damage(state)
        self._learn_attack_result(state)

        self.history.append(Snapshot(
            frame=state["frame"], me_life=state.get("me_life"),
            opp_life=state.get("opp_life"), dist=state.get("dist"),
            opp_anim=state.get("opp_anim"), opp_posture=state.get("opp_posture"),
            fp=state.get("fp").copy() if state.get("fp") is not None else None,
            action=self.last_action, facing_right=bool(state.get("facing_right", True))
        ))
        self.last_state = state

    def decide(self, state):
        self.preempt(state)
        if self.queue:
            return
        pc = getattr(self, "punish_check", None)
        if pc and state["frame"] >= pc["frame"]:
            self.punish_check = None
            ml = state.get("me_life")
            held = pc["life"] is None or ml is None or ml >= pc["life"] - 0.2
            d = state.get("dist")
            if held and d is not None and d < 70:
                self._close_combo(state)
                self.last_action = "punish after block: 2LK 2LK xx HP Jet Upper"
                return

        threat, score = self._threat_now(state)
        if threat is not None and state["frame"]-self.last_threat_response>18:
            self.last_threat_response=state["frame"]
            if state.get("exact") and state.get("dist") is not None and state["dist"]<112 and random.random()<.62:
                self._parry_punish(state)
            else:
                self._guard_then_punish(state, frames=16)
            return

        d = state.get("dist")
        opp_y = state.get("opp_y")
        motion=float(state.get("opp_motion") or 0.0)

        # A strong nearby motion burst is the visual backend's best attack-start
        # signal: attempt a forward parry and immediately punish.
        if not state.get("exact") and d is not None and d<130 and motion>.045:
            self._guard_then_punish(state, frames=16)
            return

        # Exact mode can anti-air by position.
        if state.get("exact") and opp_y is not None and 35 < opp_y < 95 and d is not None and d < 95:
            self._jet_upper(state)
            return

        if d is not None:
            if d > 125:
                # Far away: approach slowly, but visual mode stays conservative.
                if random.random() < self.aggression * 0.45:
                    self._walk(True)
                else:
                    self._q("neutral guard", [("DOWN","BACK")] * 3)
                return
            if d < 55:
                if motion < .03 and random.random()<self.aggression:
                    self._close_combo(state)
                else:
                    self._q("close guard", [("DOWN","BACK")] * 2)
                return
            if 55 <= d <= 108 and motion < .03 and random.random()<self.aggression*.70:
                self._mid_combo(state)
                return

        # Visual-only neutral: do much less random swinging than the old bot.
        if random.random()<0.38:
            self._q("neutral guard", [("DOWN","BACK")] * 2)
        else:
            self._walk(True)

    def next_keys(self):
        if not self.queue:
            return ()
        return self.queue.popleft()
