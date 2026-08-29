local session_key = KEYS[1]
local solved_at_ms = ARGV[1]

if redis.call('EXISTS', session_key) == 0 then
  return {'session_not_found'}
end
local existing = redis.call('HGET', session_key, 'solved_at_ms') or ''
if existing == '' then
  redis.call('HSET', session_key, 'solved_at_ms', solved_at_ms)
  existing = solved_at_ms
end
return {'solved', existing}

