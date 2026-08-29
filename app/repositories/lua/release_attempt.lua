local session_key = KEYS[1]
local idem_key = KEYS[2]
local lock_key = KEYS[3]
local concurrency_key = KEYS[4]
local owner = ARGV[1]

if redis.call('EXISTS', idem_key) == 0 then
  return {'missing'}
end
if (redis.call('HGET', idem_key, 'owner') or '') ~= owner then
  return {'owner_mismatch'}
end

local charged = tonumber(redis.call('HGET', session_key, 'charged_attempts') or '0')
if charged > 0 then
  redis.call('HINCRBY', session_key, 'charged_attempts', -1)
end
redis.call('DEL', idem_key)
if redis.call('GET', lock_key) == owner then
  redis.call('DEL', lock_key)
end
redis.call('ZREM', concurrency_key, owner)
return {'released'}

