-- Entry point. In FBNeo: Game > Lua Scripting > New Lua Script Window > run bot/main.lua
-- Offline only (training mode / vs CPU / you vs bot). Disabled while netplay is active.
package.path = "bot/?.lua;" .. package.path
local M = require("memory")
local I = require("input")
local T = require("threats")
local B = require("brain")

local F_DEBUG = true
B.me  = 2   -- side the bot controls (2 = you play P1 against it)
B.opp = 3 - B.me

T.load()
local frame = 0

emu.registerbefore(function()
  if emu.isnetplay and emu.isnetplay() then return end
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
