# 3rd Strike reaction bot (FBNeo Lua)

A bot that learns your attacks as you play, parries them on reaction, predicts your habits, and punishes whiffs.
It runs **offline only** (training mode, vs CPU, or you vs the bot). It turns itself off during netplay.

## Run
1. Open `sfiii3n` in FBNeo (or Fightcade's FBNeo in offline/training).
2. Go to Game → Lua Scripting, and run `bot/main.lua` with the repo root as the working directory.
3. The bot plays P2 (change `B.me` in `main.lua` to switch sides).

## How it works
- `memory.lua` reads position, animation ID, posture and life from RAM. **Check these addresses with the debug overlay first.**
- `threats.lua` records the animation and frame that hit it each time it gets hit. On the next sighting it parries 2 frames early. If the parry fails it switches between high and low. What it learns is saved to `data/threats.lua`.
- `predictor.lua` is an order-3 n-gram model of your move choices.
- `brain.lua` acts in this order: parry → anti-air → whiff punish → poke. Edit `PUNISH`/`POKE`/`ANTIAIR` for your character.

It starts out knowing nothing and gets stronger the more you hit it.
