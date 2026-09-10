#!/usr/bin/env bash
set -euo pipefail
image=${1:?Usage: container-smoke.sh IMAGE [CONFIG_DIRECTORY]}
config_directory=${2:-}
smoke_directory=$(mktemp -d)
smoke_name="hyperglass-smoke-$$"
cleanup() {
  docker rm -f "$smoke_name" "$smoke_name-redis" >/dev/null 2>&1 || true
  docker network rm "$smoke_name" >/dev/null 2>&1 || true
  rm -rf "$smoke_directory"
}
trap cleanup EXIT
if [ -n "$config_directory" ]; then
  cp "$config_directory"/{devices.yaml,directives.yaml,config.yaml,ssh.key} "$smoke_directory/"
  cp "$config_directory/plugins/x4b_bird.py" "$smoke_directory/x4b_bird.py"
else
  cat > "$smoke_directory/devices.yaml" <<'YAML'
devices:
  - name: Container Test
    address: 192.0.2.1
    platform: bird
    credential:
      username: test
      key: /etc/hyperglass/ssh.key
    attrs:
      source4: 192.0.2.1
      source6: '2001:db8::1'
YAML
  echo '{}' > "$smoke_directory/config.yaml"
  echo '{}' > "$smoke_directory/directives.yaml"
  touch "$smoke_directory/x4b_bird.py"
  ssh-keygen -q -t ed25519 -N '' -f "$smoke_directory/ssh.key"
fi
chmod 0400 "$smoke_directory/ssh.key"
docker network create --internal "$smoke_name" >/dev/null
docker run -d --name "$smoke_name-redis" --network "$smoke_name" redis:7.4.7-alpine@sha256:02f2cc4882f8bf87c79a220ac958f58c700bdec0dfb9b9ea61b62fb0e8f1bfcf >/dev/null
docker run -d --name "$smoke_name" --network "$smoke_name" --cpus 3 --memory 2g \
  -e "HYPERGLASS_REDIS_HOST=$smoke_name-redis" \
  -v "$smoke_directory/devices.yaml:/etc/hyperglass/devices.yaml:ro" \
  -v "$smoke_directory/directives.yaml:/etc/hyperglass/directives.yaml:ro" \
  -v "$smoke_directory/config.yaml:/etc/hyperglass/config.yaml:ro" \
  -v "$smoke_directory/ssh.key:/etc/hyperglass/ssh.key:ro" \
  -v "$smoke_directory/x4b_bird.py:/etc/hyperglass/plugins/x4b_bird.py:ro" \
  "$image" >/dev/null
wait_ready() {
  for attempt in $(seq 1 120); do
    if docker exec "$smoke_name" curl --fail --silent http://localhost:8001/api/info >/dev/null; then
      docker exec "$smoke_name" curl --fail --silent http://localhost:8001/ >/dev/null
      return
    fi
    if [ "$(docker inspect --format '{{.State.Running}}' "$smoke_name")" != true ]; then
      docker logs --tail 80 "$smoke_name"
      return 1
    fi
    sleep 10
  done
  docker logs --tail 80 "$smoke_name"
  return 1
}
wait_ready
docker exec "$smoke_name" python3 -c 'from pathlib import Path; p=Path("/etc/hyperglass/ssh.key"); assert p.stat().st_mode & 0o777 == 0o400; assert any(Path("/etc/hyperglass/static/ui/_next/static").rglob("*.js"))'
docker restart --time 30 "$smoke_name" >/dev/null
wait_ready
# A missing export must force a rebuild even if the previous config hash matches.
docker exec "$smoke_name" rm -rf /etc/hyperglass/static/ui
docker restart --time 30 "$smoke_name" >/dev/null
wait_ready
docker stop --time 30 "$smoke_name" >/dev/null
test "$(docker inspect --format '{{.State.OOMKilled}}' "$smoke_name")" = false
test "$(docker inspect --format '{{.State.ExitCode}}' "$smoke_name")" != 137
echo 'Container smoke tests passed (offline startup, assets, key permissions, restart, shutdown).'
