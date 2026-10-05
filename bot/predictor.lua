-- Variable-order n-gram over the opponent's attack choices. It predicts what
-- comes next from what they have done, the way a human reads habits.
local P = { hist = {}, counts = {}, ORDER = 3 }

function P.observe(sym)
  for n = 1, P.ORDER do
    if #P.hist >= n then
      local ctx = table.concat(P.hist, ",", #P.hist - n + 1, #P.hist)
      P.counts[ctx] = P.counts[ctx] or {}
      P.counts[ctx][sym] = (P.counts[ctx][sym] or 0) + 1
    end
  end
  table.insert(P.hist, sym)
  if #P.hist > 64 then table.remove(P.hist, 1) end
end

-- Returns the most likely next symbol and its confidence, backing off to shorter context.
function P.predict()
  for n = math.min(P.ORDER, #P.hist), 1, -1 do
    local ctx = table.concat(P.hist, ",", #P.hist - n + 1, #P.hist)
    local c = P.counts[ctx]
    if c then
      local best, bc, total = nil, 0, 0
      for s, v in pairs(c) do total = total + v if v > bc then best, bc = s, v end end
      if total >= 3 then return best, bc / total end
    end
  end
  return nil, 0
end

return P
