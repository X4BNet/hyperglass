# X4B hyperglass v2

This fork merges upstream `fd34bda03fe3382cb14a00dc9ec76cf282bc3e0a` (v2.0.4 plus unreleased fixes) into the v1 fork without rewriting its history.

## Build and check

The container pins Python 3.12.12, Node 22.22.0, pnpm 10.11.0, and base-image digests. Python requirements use upstream's checked-in locks; the UI uses its pnpm lock. Application startup builds UI assets from the mounted configuration, using the image's offline dependency store. Next.js build concurrency is limited for the existing 3 CPU / 2 GiB pod budget. UI dependencies and generated asset directories must remain writable.

```sh
docker build --target test -t hyperglass:test .
docker build --build-arg APPLICATION_REVISION="$(git rev-parse HEAD)" -t hyperglass:local .
.tests/container-smoke.sh hyperglass:local
../k8s-hyperglass/scripts/test.sh hyperglass:test
.tests/container-smoke.sh hyperglass:local ../k8s-hyperglass/config
```

The migration test command uses isolated Redis and mocks router access and containing-prefix lookup. The smoke test uses a network without internet access, checks mounted-key permissions and static assets, then verifies restart and graceful shutdown. It performs no router queries.

CI runs the backend suite/Ruff and frontend formatting/Biome/TypeScript/Vitest before building and smoke-testing the application image. Only trusted pushes to `main` or `v*` tags publish `x4bnet/hyperglass:git-<application-sha>`; `main` also publishes `latest`. Deploy using the reported digest. PRs never publish images or deploy.

## Configuration and deployment

The coordinated change in `X4BNet/k8s-hyperglass` owns devices, directives, the X4B BIRD plugin, and rollout tooling. Mount its `devices.yaml`, `directives.yaml`, `config.yaml`, `plugins/x4b_bird.py`, and the SSH key under `/etc/hyperglass`; give the key mode `0400`. Use per-file mounts so hyperglass can write generated assets alongside them.

Runtime defaults bind `0.0.0.0:8001`, use local Redis, keep the UI enabled, and run two workers. Compose overrides Redis to the service hostname. The old `HYPERGLASS_PATH`, `hyperglass.yaml`, `commands.yaml`, and VRF configuration are replaced by upstream v2 settings and directives. The API accepts device and directive IDs; no v1 API compatibility layer is included.

See the deployment repository's `UPGRADE.md` for preview, cutover, rollback, and the validation record. Its GitOps renderer preserves the old deployment and its Secret while adding v2. Do not replace the old Secret with v2 configuration.

## Deliberate compatibility choices

The old validator never enforced configured prefix-length limits. The migrated directives therefore retain host/prefix queries, RFC1918 denials, and reserved/loopback/unspecified rejection. They preserve the public-host containing-prefix lookup and BIRD AS-path/community formatting through a v2 input plugin. Dual-stack community/AS-path queries execute both `birdc` and `birdc6`; Brazil uses only IPv4 commands.

Obsolete v1 Redis, asyncssh, installer, and frontend patches were retired in favor of upstream implementations. Remaining application changes concern reproducible container startup, bounded UI build concurrency, build-retry correctness, and SSH collection outside the event loop with per-request async timeouts.
