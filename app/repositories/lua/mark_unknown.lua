local idem_key = KEYS[1]
local lock_key = KEYS[2]
local concurrency_key = KEYS[3]
local owner = ARGV[1]
local now_ms = ARGV[2]
local idem_ttl_ms = tonumber(ARGV[3])

if redis.call('EXISTS', idem_key) == 0 then
  return {'missing'}
end
if (redis.call('HGET', idem_key, 'owner') or '') ~= owner then
  return {'owner_mismatch'}
end

redis.call('HSET', idem_key, 'state', 'outcome_unknown', 'completed_at_ms', now_ms)
redis.call('PEXPIRE', idem_key, idem_ttl_ms)
if redis.call('GET', lock_key) == owner then
  redis.call('DEL', lock_key)
end
redis.call('ZREM', concurrency_key, owner)
return {'outcome_unknown'}

