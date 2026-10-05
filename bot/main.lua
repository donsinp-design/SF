-- Entry point. In FBNeo: Game > Lua Scripting > New Lua Script Window > run bot/main.lua
-- Netplay is opt-in: set ALLOW_NETPLAY = true only on an account clearly named as a bot
-- (e.g. "AI_..."), and tell opponents before the match.
-- Find our own folder so the bot works wherever it's unzipped.
local HERE = (debug.getinfo(1, "S").source:sub(2):match("^(.*[/\\])") or "bot/")
package.path = HERE .. "?.lua;" .. package.path
BOT_DATA_DIR = HERE .. "../data/"
local M = require("ai_memory")
local I = require("ai_input")
local T = require("ai_threats")
local B = require("ai_brain")
local D = require("ai_dudley")

local F_DEBUG = true
local ALLOW_NETPLAY = false
-- Simulated network lag for offline latency tests: the bot sees the game this
-- many frames late (1 frame = ~16.7 ms). Try 0, 2, 4, 6 and compare parry rates.
local DELAY_FRAMES = 0
local history = {}

-- Auto-pick Dudley + super art on the select screen. Char id addresses are from
-- community research; the debug line shows what it reads so we can fix them.
local AUTO_SELECT = true
local CHAR_ADDR = { 0x02011387, 0x02011388 }
local sel = { t = 0, phase = "char" }

local function auto_select()
  sel.t = sel.t + 1
  local id = memory.readbyte(CHAR_ADDR[B.me])
  local pad, P = {}, "P" .. B.me .. " "
  if sel.phase == "char" then
    if id == D.CHAR_ID then
      if sel.t % 10 == 0 then pad[P.."Weak Punch"] = true; sel.phase = "art"; sel.t = 0 end
    elseif sel.t % 8 == 0 then pad[P.."Right"] = true end
  elseif sel.phase == "art" then
    -- art screen: move down (SUPER_ART - 1) times, then confirm
    local downs = D.SUPER_ART - 1
    local step = math.floor(sel.t / 15)
    if sel.t % 15 == 0 and step >= 3 and step < 3 + downs then pad[P.."Down"] = true end
    if sel.t == (3 + downs) * 15 + 5 then pad[P.."Weak Punch"] = true; sel.phase = "done" end
  end
  joypad.set(pad)
  if F_DEBUG then gui.text(8, 50, string.format("select: P%d char id %02X (want %02X) phase %s",
    B.me, id, D.CHAR_ID, sel.phase)) end
end
B.me  = 2   -- side the bot controls (2 = you play P1 against it)
B.opp = 3 - B.me

T.load()
local frame = 0

emu.registerbefore(function()
  if not ALLOW_NETPLAY and emu.isnetplay and emu.isnetplay() then return end
  local live = { M.read_player(1), M.read_player(2) }
  -- Only play during a round (life is 0..160). On menus and character select
  -- life reads as garbage like 255, so hand the controls back to you.
  local in_round = live[1].life <= 160 and live[2].life <= 160
  if not in_round then
    I.clear(); history = {}; B.prev = nil
    if F_DEBUG then gui.text(8, 40, "AI waiting for round start") end
    if AUTO_SELECT then auto_select() end
    return
  end
  table.insert(history, live)
  sel.phase, sel.t = "char", 0   -- re-arm select for the next match
  local s = history[math.max(1, #history - DELAY_FRAMES)]
  while #history > DELAY_FRAMES + 1 do table.remove(history, 1) end
  B.step(s)
  I.apply(B.me, s[B.me].x < s[B.opp].x)
  frame = frame + 1
  if frame % 600 == 0 then T.save() end

  if F_DEBUG then
    local o = s[B.opp]
    gui.text(8, 40, string.format("opp anim %04X age %d  x %d y %d post %02X life %d/%d",
      o.anim, B.opp_anim_age, o.x, o.y, o.posture, s[1].life, s[2].life))
    local n = 0 for _ in pairs(T.db) do n = n + 1 end
    gui.text(8, 50, string.format("learned threats: %d   simulated lag: %d frames (%d ms)",
      n, DELAY_FRAMES, math.floor(DELAY_FRAMES * 1000 / 60)))
  end
end)

emu.registerexit(T.save)
