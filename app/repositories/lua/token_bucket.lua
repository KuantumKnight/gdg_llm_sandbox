local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local window_ms = tonumber(ARGV[3])

local tokens = tonumber(redis.call('HGET', key, 'tokens') or tostring(capacity))
local last_ms = tonumber(redis.call('HGET', key, 'last_ms') or tostring(now_ms))
local elapsed = math.max(0, now_ms - last_ms)
tokens = math.min(capacity, tokens + (elapsed * capacity / window_ms))

if tokens < 1 then
  local retry_ms = math.ceil((1 - tokens) * window_ms / capacity)
  redis.call('HSET', key, 'tokens', tostring(tokens), 'last_ms', tostring(now_ms))
  redis.call('PEXPIRE', key, window_ms * 2)
  return {'limited', tostring(retry_ms)}
end

tokens = tokens - 1
redis.call('HSET', key, 'tokens', tostring(tokens), 'last_ms', tostring(now_ms))
redis.call('PEXPIRE', key, window_ms * 2)
return {'allowed', '0'}

