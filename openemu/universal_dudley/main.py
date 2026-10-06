from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path

from .learning import Learner
from .brain import Brain
from .retroarch_backend import RetroArchBackend
from .visual_backend import VisualMacBackend

def load_cfg(root):
    return json.loads((root/"config.json").read_text())

def make_backend(args,cfg):
    if args.emulator=="retroarch":
        return RetroArchBackend(player=args.player,swap=args.swap)
    return VisualMacBackend(args.emulator,args.player,cfg["apps"][args.emulator],cfg["visual"])

def main():
    ap=argparse.ArgumentParser(description="Universal Dudley AI")
    ap.add_argument("--emulator",choices=("retroarch","openemu"),required=True)
    ap.add_argument("--player",type=int,choices=(1,2),required=True)
    ap.add_argument("--swap",type=int,choices=(1,2,4),default=4)
    ap.add_argument("--aggression",type=float,default=None)
    args=ap.parse_args()

    root=Path(__file__).resolve().parent.parent
    cfg=load_cfg(root)
    learner=Learner(root/"saved")
    try:
        backend=make_backend(args,cfg)
    except RuntimeError as exc:
        print()
        print("BOT DID NOT START")
        print("-----------------")
        print(exc)
        print()
        return 2
    brain=Brain(args.player,learner,args.emulator,
                aggression=float(args.aggression if args.aggression is not None else cfg["aggression"]),
                visual_threshold=float(cfg["visual"]["threat_distance"]))

    print()
    print("UNIVERSAL DUDLEY AI")
    print("-------------------")
    print("Emulator:",args.emulator)
    print("Taking over: P%d"%args.player)
    print("State mode:","EXACT RAM" if backend.exact else "VISUAL LEARNING")
    print("Learning log:", learner.txt_path)
    print("Machine memory:", learner.json_path)
    print()
    if not backend.exact:
        print("VISUAL mode: keep the game window visible and grant Screen Recording + Accessibility.")
        print("Map the emulator keys to the defaults in config.json.")
    else:
        print("RetroArch: Network Commands + Network RetroPad must be enabled.")
    print("Ctrl+C stops the bot and releases all buttons.")
    print()

    target_fps=max(1,float(cfg["fps"]))
    frame_time=1.0/target_fps
    next_tick=time.perf_counter()
    measured_at=next_tick
    measured_frames=0
    misses=0
    try:
        while True:
            start=time.perf_counter()
            st=backend.read_state()
            if st is None:
                # no game window: send nothing
                misses+=1
                if misses%120==1: print("Waiting for readable game state...")
                backend.release_all()
                time.sleep(0.05)
                continue
            misses=0
            brain.observe(st)
            brain.decide(st)
            keys=brain.next_keys()
            backend.set_logical(keys,bool(st.get("facing_right",True)))
            measured_frames+=1

            if st["frame"]%60==0:
                now=time.perf_counter()
                actual_fps=measured_frames/max(0.001,now-measured_at)
                measured_at,measured_frames=now,0
                print(f"frame {st['frame']} ({actual_fps:.1f} fps) | {brain.last_action} | "
                      f"life {st.get('me_life')} vs {st.get('opp_life')} | "
                      f"dist {round(st.get('dist') or 0,1)} | "
                      f"hits taken {learner.data['hits_taken']} | whiffs {learner.data['whiffs']}")
            # Absolute cadence avoids accumulating the small drift caused by
            # capture/analysis time. At 60 this attempts one read per game frame.
            next_tick+=frame_time
            now=time.perf_counter()
            if next_tick<now-frame_time:
                next_tick=now
            if next_tick>now:
                time.sleep(next_tick-now)
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        backend.close()
        learner.save()
        brain.moves.save()

    return 0

if __name__=="__main__":
    raise SystemExit(main())
