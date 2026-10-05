-- Decision layer. Priority: parry incoming hit > punish recovery > neutral pressure.
local I = require("ai_input")
local T = require("ai_threats")
local P = require("ai_predictor")
local D = require("ai_dudley")

local B = { me = 1, opp = 2, prev = nil, opp_anim_age = 0, pending = nil }

B.PUNISH  = D.PUNISH
B.POKE    = D.CR_MK
B.ANTIAIR = D.JET_UPPER
B.AGGRESSION = 0.6     -- 0 = patient footsies, 1 = constant pressure
B.confirm = nil        -- pending hit-confirm {life}

B.MY_POKE_RANGE = D.POKE_RANGE
B.SPACING_MARGIN = 6   -- pixels outside their reach

local PARRY_LEAD = 2   -- frames before the active frame to tap
local function parry(low)
  -- 3S parry: neutral, then tap forward (high) or down (low) inside the window.
  return I.seq(I.hold(5,1), I.hold(low and 2 or 6, 1), I.hold(5,1))
end

function B.step(s)
  local me, op = s[B.me], s[B.opp]
  local prev = B.prev
  local dist = math.abs(me.x - op.x)

  -- animation age tracking
  if prev and prev[B.opp].anim == op.anim then B.opp_anim_age = B.opp_anim_age + 1
  else
    B.opp_anim_age = 0
    if T.lookup(op.anim) then P.observe(string.format("%04X", op.anim)) end
  end

  -- learn from damage
  if prev and me.life < prev[B.me].life then
    if B.pending and B.pending.anim == op.anim then T.parry_failed(op.anim) end
    T.record_hit(op.anim, B.opp_anim_age, dist, op.posture == 0x20)
    B.pending = nil
  end
  if B.pending and B.opp_anim_age > B.pending.hit + 3 then
    T.parry_ok(B.pending.anim); B.pending = nil
  end

  B.prev = s
  B.frame = (B.frame or 0) + 1

  -- hit-confirm: if the cr.LK string connected, cancel into super
  if B.confirm and not I.busy() then
    if op.life < B.confirm.life then I.push(D.SUPER) end
    B.confirm = nil; return
  end
  if I.busy() then return end

  -- 1. reactive parry on a known threat
  local t = T.lookup(op.anim)
  if t and dist <= t.dist + 24 and B.opp_anim_age == t.hit - PARRY_LEAD then
    I.push(parry(t.low)); B.pending = { anim = op.anim, hit = t.hit }; return
  end

  -- 2. predictive: if the model is confident the next move is a known threat,
  --    pre-load a parry the instant that animation begins.
  local guess, conf = P.predict()
  if conf > 0.7 and B.opp_anim_age == 0 and guess == string.format("%04X", op.anim) then
    -- handled by step 1 next frames; nothing extra needed
  end

  -- 3. anti-air
  if op.y > 40 and dist < 90 and op.y < 90 then I.push(B.ANTIAIR) return end

  -- 4. whiff punish: a known attack has passed its active frames without contact
  if t and B.opp_anim_age > t.hit + 2 and dist < t.dist + 30 then I.push(B.PUNISH) return end

  -- 5. aggression: in close, mix pressure-into-confirm and throws
  if dist <= D.THROW_RANGE + 20 and math.random() < B.AGGRESSION * 0.25 then
    if math.random() < 0.6 then
      I.push(D.CONFIRM_STARTER); B.confirm = { life = op.life }
    else I.push(D.THROW) end
    return
  end
  if dist > D.POKE_RANGE and math.random() < B.AGGRESSION * 0.03 then
    I.push(D.DASH_IN); return
  end

  -- 6. footsies: hover just outside the opponent's longest learned attack,
  --    so their pokes whiff and ours land at the tip.
  local reach = B.MY_POKE_RANGE
  for _, e in pairs(T.db) do reach = math.max(reach, e.dist) end
  local sweet = reach + B.SPACING_MARGIN
  if dist > sweet + 8 then I.push(I.hold(6, 2))          -- walk in
  elseif dist < sweet - 8 then I.push(I.hold(4, 2))      -- walk back
  elseif dist <= B.MY_POKE_RANGE and math.random() < 0.15 then I.push(B.POKE) end
end

return B
