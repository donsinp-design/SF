-- Launcher: effie's 3rd_training.lua with the Dudley AI controlling P2.
-- Run from Game > Lua Scripting, or just press "Training" in Fightcade (fbneo-training-mode.lua loads the AI too).
local ai = require("src.ai.dudley_ai")
ai.install()
require("src.data.game_data").is_fightcade = true
require("3rd_training")
