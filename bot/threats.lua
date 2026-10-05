-- Learned threat model: which opponent animations hit, on which frame, and
-- whether they must be parried high or low. Learned from getting hit, then
-- refined by parry success/failure. Persisted between sessions.
local T = { db = {}, path = (BOT_DATA_DIR or "data/") .. "threats.lua" }

local function key(char_anim) return string.format("%04X", char_anim) end

function T.load()
  local f = io.open(T.path, "r")
  if not f then return end
  local chunk = load("return " .. f:read("*a")); f:close()
  if chunk then T.db = chunk() or {} end
end

function T.save()
  local f = io.open(T.path, "w"); if not f then return end
  f:write("{\n")
  for k, v in pairs(T.db) do
    f:write(string.format("  [%q]={hit=%d,low=%s,dist=%d,seen=%d,ok=%d},\n",
      k, v.hit, tostring(v.low), v.dist, v.seen, v.ok))
  end
  f:write("}\n"); f:close()
end

-- Called when we take damage: opponent anim `anim` connected `age` frames in.
function T.record_hit(anim, age, dist, opp_crouching)
  local e = T.db[key(anim)]
  if not e then
    T.db[key(anim)] = { hit=age, low=opp_crouching, dist=dist, seen=1, ok=0 }
  else
    e.hit  = math.floor((e.hit * e.seen + age) / (e.seen + 1) + 0.5)
    e.dist = math.max(e.dist, dist)
    e.seen = e.seen + 1
  end
end

function T.lookup(anim) return T.db[key(anim)] end

-- A parry attempt failed: if timing was right, the height guess was wrong.
function T.parry_failed(anim) local e = T.lookup(anim) if e then e.low = not e.low end end
function T.parry_ok(anim) local e = T.lookup(anim) if e then e.ok = e.ok + 1 end end

return T
