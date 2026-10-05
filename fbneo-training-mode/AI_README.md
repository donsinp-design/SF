# Dudley AI

This folder is effie's 3rd Strike training mode (https://github.com/effie3rd/3rd_training_lua, commit d0f8e55, GPL-3.0) with a Dudley AI added in `src/ai/dudley_ai.lua`. The AI loads from `fbneo-training-mode.lua` and `ai_training.lua`.

## Install (Fightcade)
1. Copy everything in this folder into `Fightcade/emulator/fbneo/fbneo-training-mode/` and overwrite the existing files.
2. In Fightcade, open the 3rd Strike lobby and press **Training**.
3. Pick your character. P2 picks Dudley (Super Art I) and plays as the AI.

To turn the AI off, set `enabled = false` at the top of `src/ai/dudley_ai.lua`. Other settings there: `super_art`, `aggression`, `hurt_margin`, `show_debug`.
