local session_key = KEYS[1]
local idem_key = KEYS[2]
local lock_key = KEYS[3]
local concurrency_key = KEYS[4]

local owner = ARGV[1]
local encrypted_replay = ARGV[2]
local solved_at_ms = ARGV[3]
local now_ms = ARGV[4]
local idem_ttl_ms = tonumber(ARGV[5])

if redis.call('EXISTS', idem_key) == 0 then
  return {'missing'}
end

local authoritative_solved = redis.call('HGET', session_key, 'solved_at_ms') or ''
if solved_at_ms ~= '' and authoritative_solved == '' then
  redis.call('HSET', session_key, 'solved_at_ms', solved_at_ms)
  authoritative_solved = solved_at_ms
end

redis.call('HSET', idem_key,
  'state', 'completed',
  'encrypted_replay', encrypted_replay,
  'completed_at_ms', now_ms)
redis.call('PEXPIRE', idem_key, idem_ttl_ms)

if redis.call('GET', lock_key) == owner then
  redis.call('DEL', lock_key)
end
redis.call('ZREM', concurrency_key, owner)

local limit = tonumber(redis.call('HGET', session_key, 'attempt_limit') or '0')
local charged = tonumber(redis.call('HGET', session_key, 'charged_attempts') or '0')
return {'completed', authoritative_solved, tostring(math.max(0, limit - charged))}

