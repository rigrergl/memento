# Docker Setup for Integration Tests

The integration test suite uses [testcontainers](https://testcontainers.com/) to spin up a Neo4j container, which requires Docker to be reachable from your user account **without `sudo`**. The testcontainers Python library talks directly to the Docker socket (`/var/run/docker.sock`), and there is no way to inject `sudo` into that path.

This note records what worked on an Ubuntu 24.04 dev box where `docker ps` was failing with:

```
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

## Why the snap-installed Docker did not work

Ubuntu ships Docker via snap by default. The snap-packaged `dockerd` is started with `--group docker`, but due to snap confinement the socket is created as `root:root` rather than `root:docker`, so adding your user to a host `docker` group does not grant access. Restarting or `snap disable`/`snap enable` did not change this.

## What actually worked: switch to Docker's official apt package

1. **Remove the snap version.** Snap data is snapshotted automatically, so this is recoverable.

   ```bash
   sudo snap remove docker
   ```

2. **Add Docker's official apt repository.** (See the [upstream instructions](https://docs.docker.com/engine/install/ubuntu/) for the canonical version.)

   ```bash
   sudo install -m 0755 -d /etc/apt/keyrings
   sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
   sudo chmod a+r /etc/apt/keyrings/docker.asc

   sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
   Types: deb
   URIs: https://download.docker.com/linux/ubuntu
   Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
   Components: stable
   Architectures: $(dpkg --print-architecture)
   Signed-By: /etc/apt/keyrings/docker.asc
   EOF

   sudo apt update
   ```

3. **Install Docker Engine.**

   ```bash
   sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   ```

   The post-install state should be:
   - `docker.service` enabled and running under systemd
   - `/var/run/docker.sock` owned by `root:docker` with mode `srw-rw----`

4. **Add your user to the `docker` group** (the apt install creates it if missing).

   ```bash
   sudo usermod -aG docker $USER
   ```

5. **Pick up the new group membership.** Group membership is established at login, so opening a new terminal in the *same* desktop session is not enough — the desktop session itself predates the group change. Either:
   - Log out of your desktop session and log back in (or reboot), **or**
   - Run `newgrp docker` in a shell as a session-local workaround.

   Confirm with `id` — you should see `docker` in the group list — and then `docker ps` should work without `sudo`.

## Security note

Membership in the `docker` group is effectively passwordless root: anyone in it can bind-mount the host filesystem into a privileged container. This is the standard tradeoff for a single-user dev machine and matches what Docker's own documentation recommends. On shared or production machines, prefer [rootless Docker](https://docs.docker.com/engine/security/rootless/).

## Verifying the integration tests pick it up

Once `docker ps` works without `sudo`, the testcontainers-based suite should run cleanly:

```bash
uv run pytest tests/integration/
```

The Neo4j container is session-scoped — it starts once at the beginning of the test session and is torn down at the end.
