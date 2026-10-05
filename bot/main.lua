-- Entry point. In FBNeo: Game > Lua Scripting > New Lua Script Window > run bot/main.lua
-- Netplay is opt-in: set ALLOW_NETPLAY = true only on an account clearly named as a bot
-- (e.g. "AI_..."), and tell opponents before the match.
-- Find our own folder so the bot works wherever it's unzipped.
local HERE = (debug.getinfo(1, "S").source:sub(2):match("^(.*[/\\])") or "bot/")
package.path = HERE .. "?.lua;" .. package.path
BOT_DATA_DIR = HERE .. "../data/"
local M = require("memory")
local I = require("input")
local T = require("threats")
local B = require("brain")

local F_DEBUG = true
local ALLOW_NETPLAY = false
B.me  = 2   -- side the bot controls (2 = you play P1 against it)
B.opp = 3 - B.me

T.load()
local frame = 0

emu.registerbefore(function()
  if not ALLOW_NETPLAY and emu.isnetplay and emu.isnetplay() then return end
  local s = { M.read_player(1), M.read_player(2) }
  B.step(s)
  I.apply(B.me, s[B.me].x < s[B.opp].x)
  frame = frame + 1
  if frame % 600 == 0 then T.save() end

  if F_DEBUG then
    local o = s[B.opp]
    gui.text(8, 40, string.format("opp anim %04X age %d  x %d y %d post %02X life %d/%d",
      o.anim, B.opp_anim_age, o.x, o.y, o.posture, s[1].life, s[2].life))
    local n = 0 for _ in pairs(T.db) do n = n + 1 end
    gui.text(8, 50, "learned threats: " .. n)
  end
end)

emu.registerexit(T.save)
