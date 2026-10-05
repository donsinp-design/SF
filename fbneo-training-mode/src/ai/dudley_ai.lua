-- Dudley AI for effie's 3rd_training.lua (offline only).
--
-- Defence comes from effie's predictive blocking set to PARRY: it reads every
-- move's real hitboxes from the recorded frame data and parries on the exact
-- frame. This file adds offence on top: frame-exact whiff punishes, hit-confirms
-- into super, anti-airs, oki mixups and footsies spacing.
local gamestate = require("src.gamestate")
local inputs = require("src.control.inputs")
local framedata = require("src.data.framedata")
local advanced_control = require("src.control.advanced_control")
local settings = require("src.settings")
local modules = require("src.modules")
local character_select = require("src.control.character_select")

local AI = {
   enabled = true,    -- false = plain effie training mode
   player_id = 2,     -- side the AI plays
   super_art = 1,     -- 1 Rocket Upper (best with frame-perfect links), 2 Rolling Thunder, 3 Corkscrew Blow
   aggression = 0.7,  -- 0 = patient footsies, 1 = constant pressure
   hurt_margin = 22,  -- pixels of opponent hurtbox in front of their origin
   show_debug = true,
}

local F, B, D = "forward", "back", "down"

-- Input sequences: one table per frame, directions relative to facing.
local S = {
   HK = { { "HK" } },
   MP = { { "MP" } },
   f_MK = { { F, "MK" } },
   f_HK = { { F, "HK" } },
   d_LK = { { D, "LK" } },
   d_MP = { { D, "MP" } },
   d_HP = { { D, "HP" } },
   throw = { { F, "LP", "LK" } },
   dp_HP = { { F }, { D }, { D, F, "HP" } },
   dp_EX = { { F }, { D }, { D, F, "MP", "HP" } },
   mgb_EX = { { B }, { D, B }, { D }, { D, F }, { F, "MP", "HP" } },
   mgb_HP = { { B }, { D, B }, { D }, { D, F }, { F, "HP" } },
   -- 236236 + HP, then piano MP/LP so the super comes out on the first possible frame
   super = { { D }, { D, F }, { F }, { D }, { D, F }, { F, "HP" }, { "MP" }, { "LP" } },
   dash = { { F }, {}, { F } },
   walk_f = { { F }, { F }, { F }, { F } },
   walk_b = { { B }, { B }, { B }, { B } },
}

-- Frames from first input to first active frame (wiki startup + motion length - 1).
local NEED = { HK = 5, MP = 3, f_MK = 5, f_HK = 12, d_LK = 4, dp_HP = 6, mgb_HP = 21, mgb_EX = 20, super = 6 }

local me, opp
local state = { confirm = nil, juggle_until = 0, last_action = "" }
local reach = {}
local selected_this_screen = false

local function has_stock() return me.meter_count >= 1 end
local function has_ex() return me.meter_gauge >= 40 or me.meter_count >= 1 end
local function dist() return math.abs(me.pos_x - opp.pos_x) end

local function in_reach(name, extra)
   local r = reach[name]
   if not r then
      r = framedata.get_hitbox_max_range_by_name("dudley", name) or 0
      reach[name] = r
   end
   return dist() <= r + AI.hurt_margin + (extra or 0)
end

local function opp_longest_poke()
   local best = 0
   for _, n in ipairs({ "MP", "MK", "HP", "HK", "d_MP", "d_MK", "d_HK" }) do
      local r = framedata.get_hitbox_max_range_by_name(opp.char_str, n) or 0
      if r > best then best = r end
   end
   return best
end

local function act(name, seq, confirm)
   inputs.queue_input_sequence(me, seq, 0, true)
   state.last_action = name
   if confirm then state.confirm = { move = name, until_frame = gamestate.frame_number + 30 } end
end

-- frames until the opponent can block or act again is more than `need`
local function opp_stuck_for(need) return not advanced_control.is_idle_timing(opp, need, true) end

local function can_act()
   return me.is_idle and me.remaining_freeze_frames == 0 and not me.is_blocking
      and not inputs.is_playing_input_sequence(me)
end

-- What to do once a starter connects. Runs during hitstop, so cancels are frame-perfect.
local function on_hit(move)
   if move == "HK" then
      if has_stock() then act("HK xx super", S.super)
      elseif has_ex() then act("HK xx EX MGB", S.mgb_EX); state.juggle_until = gamestate.frame_number + 70
      else act("HK xx Jet Upper", S.dp_HP) end
   elseif move == "f_MK" or move == "MP" then
      if has_stock() then act(move .. " xx super", S.super) else act(move .. " xx Jet Upper", S.dp_HP) end
   elseif move == "d_LK" then
      act("2LK chain", S.d_LK, true); state.confirm.move = "d_LK2"
   elseif move == "d_LK2" then
      if has_stock() then act("2LK 2LK xx super", S.super)
      else act("2LK > 2MP > 2HP", { { D, "MP" }, {}, {}, {}, {}, {}, {}, {}, { D, "HP" } }) end
   elseif move == "f_HK" then
      -- dart shot is +2 on crouching hit: link the super on the first free frame
      if has_stock() and AI.super_art ~= 2 and opp.is_crouching then state.link_super = true
      else act("dart shot > MK", { {}, {}, {}, {}, {}, {}, { "MK" } }) end
   end
end

local function on_block(move)
   -- f.MK is +2 and 2LK is 0 on block: keep the pressure going
   if move == "f_MK" or move == "d_LK" or move == "d_LK2" then state.pressure = true end
end

local function update_confirm()
   local c = state.confirm
   if not c then return false end
   if me.has_just_hit then
      state.confirm = nil
      on_hit(c.move)
      return true
   elseif me.has_just_been_blocked or opp.has_just_blocked then
      state.confirm = nil
      on_block(c.move)
      return true
   elseif gamestate.frame_number > c.until_frame then
      state.confirm = nil
   end
   return false
end

local function opp_projectile_out()
   for _, proj in pairs(gamestate.projectiles) do
      if proj.emitter_id == opp.id then return true end
   end
   return false
end

-- their move has finished its last active frame (whiffed or blocked/parried)
local function opp_past_active()
   if opp.is_in_recovery then return true end
   if not opp.is_attacking then return false end
   local last = framedata.get_last_hit_frame(opp.char_str, opp.animation)
   return last > 0 and opp.animation_frame > last
end

local function try_punish()
   if opp.is_airborne or opp.has_just_hit or not opp_past_active() or opp_projectile_out() then return false end
   -- biggest reward that is guaranteed to land before they recover
   if has_stock() and opp_stuck_for(NEED.super) and in_reach("rocket_upper", 10) and AI.super_art == 1 then
      act("punish: super", S.super); return true
   end
   if opp_stuck_for(NEED.HK) and in_reach("HK") then act("punish: HK", S.HK, true); return true end
   if opp_stuck_for(NEED.f_MK) and in_reach("f_MK") then act("punish: f.MK", S.f_MK, true); return true end
   if opp_stuck_for(NEED.MP) and in_reach("MP") then act("punish: MP", S.MP, true); return true end
   if has_ex() and opp_stuck_for(NEED.mgb_EX) and in_reach("machinegun_blow_EXP") then
      act("punish: EX MGB", S.mgb_EX); state.juggle_until = gamestate.frame_number + 70; return true
   end
   if opp_stuck_for(NEED.mgb_HP) and in_reach("machinegun_blow_HP") then act("punish: HP MGB", S.mgb_HP); return true end
   return false
end

local function try_juggle()
   if gamestate.frame_number > state.juggle_until then return false end
   if opp.is_airborne and dist() < 80 then
      state.juggle_until = 0
      act("juggle: Jet Upper", S.dp_HP); return true
   end
   return false
end

local function try_anti_air()
   if not opp.is_airborne or opp.is_attacking then return false end -- attacks get parried instead
   if opp.pos_y > 25 and opp.pos_y < 90 and dist() < 90 then
      if has_ex() and AI.aggression < 0.5 then act("anti-air: EX Jet Upper", S.dp_EX)
      else act("anti-air: Jet Upper", S.dp_HP) end
      return true
   end
   return false
end

local function try_oki()
   if not opp.is_waking_up then return false end
   local close = dist() < 70
   if not close then act("oki: dash in", S.dash); return true end
   local r = math.random()
   if r < 0.35 and advanced_control.is_wakeup_timing(opp, NEED.d_LK, true) then
      act("oki: meaty 2LK", S.d_LK, true); return true
   elseif r < 0.6 and advanced_control.is_wakeup_timing(opp, NEED.f_HK, true) then
      act("oki: dart shot", S.f_HK, true); return true
   elseif r < 0.8 and advanced_control.is_throw_vulnerable_timing(opp, 1, true) then
      act("oki: throw", S.throw); return true
   end
   return false
end

local function neutral()
   local d = dist()
   local their_reach = opp_longest_poke() + AI.hurt_margin
   local close = d < framedata.get_contact_distance(me) + 30

   if state.pressure or (close and math.random() < AI.aggression * 0.3) then
      state.pressure = false
      local r = math.random()
      if r < 0.3 then act("pressure: f.MK", S.f_MK, true)
      elseif r < 0.55 then act("pressure: 2LK", S.d_LK, true)
      elseif r < 0.75 then act("pressure: throw", S.throw)
      else act("pressure: dart shot", S.f_HK, true) end
      return
   end
   -- they walk into st.HK range: stuff it (it beats most buttons and builds meter)
   if in_reach("HK") and opp.action == 2 then act("footsie: HK", S.HK, true); return end
   if d > their_reach + 12 then
      if math.random() < AI.aggression * 0.08 then act("dash in", S.dash) else act("walk in", S.walk_f) end
   elseif d < their_reach - 6 and not close then
      if math.random() < AI.aggression then act("footsie: HK", S.HK, true) else act("walk out", S.walk_b) end
   end
end

function AI.update()
   if not gamestate.is_in_match then return end
   me, opp = gamestate.player_objects[AI.player_id], gamestate.player_objects[3 - AI.player_id]
   selected_this_screen = false
   if not framedata.is_loaded or not gamestate.is_in_match_playable or me.char_str ~= "dudley" then return end

   -- stop walking the moment they attack so the parry logic gets the inputs
   if opp.has_just_attacked and state.last_action:find("walk") then inputs.clear_input_sequence(me) end

   if update_confirm() then return end
   if state.link_super and advanced_control.is_idle_timing(me, NEED.super, true) then
      state.link_super = false; act("dart shot > super", S.super); return
   end
   if not can_act() then return end
   local _ = try_juggle() or try_punish() or try_anti_air() or try_oki() or (not opp.is_attacking and neutral())

   if AI.show_debug then
      gui.text(8, 200, string.format("AI: %s  meter %d/%d", state.last_action, me.meter_count, me.meter_gauge))
   end
end

local function apply_settings()
   local t = settings.training
   t.blocking_mode = 2          -- always defend
   t.blocking_style = 2         -- by parrying
   t.life_mode, t.meter_mode, t.stun_mode = 1, 1, 1  -- real match: no refills
   t.infinite_time = false
end

function AI.install()
   if not AI.enabled then return end
   -- run AI.update after effie's per-frame modules (its parry logic runs just before)
   local original_update = modules.update
   modules.update = function(...)
      original_update(...)
      AI.update()
   end
   -- force P2 to Dudley with the chosen super art on every character select
   local original_select = character_select.update_character_select
   character_select.update_character_select = function(input)
      if not selected_this_screen then
         selected_this_screen = true
         apply_settings()
         character_select.force_select_character(AI.player_id, "dudley", AI.super_art, "LP")
      end
      return original_select(input)
   end
end

return AI
