# 3rd Strike reaction bot (FBNeo Lua)

A bot that learns your attacks as you play, parries them on reaction, predicts your habits, and punishes whiffs.
By default it runs offline only. To use it on netplay, set `ALLOW_NETPLAY = true` in `bot/main.lua`, play on an account clearly named as a bot (e.g. `AI_...`), and tell your opponent before each match.

## Run
1. Open `sfiii3n` in FBNeo (or Fightcade's FBNeo in offline/training).
2. Go to Game → Lua Scripting, and run `bot/main.lua` with the repo root as the working directory.
3. The bot plays P2 (change `B.me` in `main.lua` to switch sides).

## How it works
- `ai_memory.lua` reads position, animation ID, posture and life from RAM. **Check these addresses with the debug overlay first.**
- `ai_threats.lua` records the animation and frame that hit it each time it gets hit. On the next sighting it parries 2 frames early. If the parry fails it switches between high and low. What it learns is saved to `data/threats.lua`.
- `ai_predictor.lua` is an order-3 n-gram model of your move choices.
- `ai_brain.lua` acts in this order: parry → anti-air → whiff punish → poke. Edit `PUNISH`/`POKE`/`ANTIAIR` for your character.

It starts out knowing nothing and gets stronger the more you hit it.

## Dudley
`bot/ai_dudley.lua` holds the bot's character plan: it auto-picks Dudley with Super Art II (Rolling Thunder), pokes with cr.MK, anti-airs with Jet Upper, and cancels cr.MK into super on punishes. Up close it does cr.LK ×2 and only goes into super if that hit (a hit-confirm), mixed with throws. `B.AGGRESSION` in `ai_brain.lua` sets how much it rushes in.

**Keep what it has learned:** that lives in `data/threats.lua`. When updating, replace only the `bot` folder and leave `data` alone.
