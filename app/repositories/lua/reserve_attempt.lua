local session_key = KEYS[1]
local idem_key = KEYS[2]
local lock_key = KEYS[3]
local rate_key = KEYS[4]
local concurrency_key = KEYS[5]

local now_ms = tonumber(ARGV[1])
local request_digest = ARGV[2]
local attempt_id = ARGV[3]
local owner = ARGV[4]
local attempt_limit = tonumber(ARGV[5])
local idem_ttl_ms = tonumber(ARGV[6])
local lock_ttl_ms = tonumber(ARGV[7])
local rate_capacity = tonumber(ARGV[8])
local concurrency_limit = tonumber(ARGV[9])

if redis.call('EXISTS', session_key) == 0 then
  return {'session_not_found'}
end

local expires_at_ms = tonumber(redis.call('HGET', session_key, 'expires_at_ms') or '0')
if expires_at_ms <= now_ms then
  return {'session_expired'}
end

local solved_at_ms = redis.call('HGET', session_key, 'solved_at_ms')
if solved_at_ms and solved_at_ms ~= '' then
  return {'session_solved', solved_at_ms}
end

if redis.call('EXISTS', idem_key) == 1 then
  local stored_digest = redis.call('HGET', idem_key, 'request_digest') or ''
  if stored_digest ~= request_digest then
    return {'idempotency_conflict'}
  end
  local state = redis.call('HGET', idem_key, 'state') or 'pending'
  if state == 'completed' then
    return {'replay', redis.call('HGET', idem_key, 'encrypted_replay') or ''}
  end
  return {'in_progress', state}
end

if redis.call('EXISTS', lock_key) == 1 then
  return {'in_progress', 'session_lock'}
end

local charged = tonumber(redis.call('HGET', session_key, 'charged_attempts') or '0')
if charged >= attempt_limit then
  return {'attempts_exhausted', tostring(charged)}
end

local tokens = tonumber(redis.call('HGET', rate_key, 'tokens') or tostring(rate_capacity))
local last_ms = tonumber(redis.call('HGET', rate_key, 'last_ms') or tostring(now_ms))
local elapsed = math.max(0, now_ms - last_ms)
tokens = math.min(rate_capacity, tokens + (elapsed * rate_capacity / 60000))
if tokens < 1 then
  local retry_ms = math.ceil((1 - tokens) * 60000 / rate_capacity)
  redis.call('HSET', rate_key, 'tokens', tostring(tokens), 'last_ms', tostring(now_ms))
  redis.call('PEXPIRE', rate_key, 120000)
  return {'rate_limited', tostring(retry_ms)}
end

redis.call('ZREMRANGEBYSCORE', concurrency_key, '-inf', now_ms)
if tonumber(redis.call('ZCARD', concurrency_key)) >= concurrency_limit then
  return {'preset_busy'}
end

tokens = tokens - 1
redis.call('HSET', rate_key, 'tokens', tostring(tokens), 'last_ms', tostring(now_ms))
redis.call('PEXPIRE', rate_key, 120000)
redis.call('SET', lock_key, owner, 'PX', lock_ttl_ms)
redis.call('ZADD', concurrency_key, now_ms + lock_ttl_ms, owner)
redis.call('PEXPIRE', concurrency_key, lock_ttl_ms * 2)

charged = redis.call('HINCRBY', session_key, 'charged_attempts', 1)
redis.call('HSET', idem_key,
  'state', 'pending',
  'request_digest', request_digest,
  'attempt_id', attempt_id,
  'owner', owner,
  'created_at_ms', tostring(now_ms))
redis.call('PEXPIRE', idem_key, idem_ttl_ms)

return {'reserved', attempt_id, tostring(attempt_limit - charged)}

