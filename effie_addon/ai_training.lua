-- Launcher: effie's 3rd_training.lua with the Dudley AI controlling P2.
-- Put this file (and src/ai/) in the same folder as effie's 3rd_training.lua,
-- then run THIS file from Game > Lua Scripting instead of 3rd_training.lua.
local ai = require("src.ai.dudley_ai")
ai.install()
dofile("3rd_training.lua")
