# Contract: GitHub Actions Workflows

**Location**: `.github/workflows/publish.yml`, `.github/workflows/auto-tag.yml`
**Driven by**: FR-011; research §R9, §R10, §R12
**Consumers**: GitHub Actions runner; downstream the published `ghcr.io/rigrergl/memento` image.

## Workflow 1: `auto-tag.yml`

### Required behaviour

| Aspect | Required value |
|---|---|
| `name` | `auto-tag` |
| `on` | `push: branches: [main]` |
| `permissions` | `contents: write` |
| `concurrency` | group keyed on `auto-tag-${{ github.ref }}` with `cancel-in-progress: false` (don't lose tag operations) |

### Required steps

1. `actions/checkout@v5` with `fetch-depth: 0` and the default `GITHUB_TOKEN`.
2. Read the version: `VERSION=$(grep -E '^version = ' pyproject.toml | head -1 | sed -E 's/.*"(.*)"/\1/')`.
3. If `git rev-parse "v$VERSION" >/dev/null 2>&1`, exit 0 with message "Tag v$VERSION already exists, skipping".
4. Configure git as `github-actions[bot]`: `git config user.name "github-actions[bot]" && git config user.email "41898282+github-actions[bot]@users.noreply.github.com"`.
5. Create annotated tag: `git tag -a "v$VERSION" -m "Release v$VERSION"`.
6. Push tag: `git push origin "v$VERSION"`.

### Forbidden

- MUST NOT trigger Docker publishes directly — only via the tag push (separation of concerns).
- MUST NOT delete or reuse existing tags.

### Test plan

- Merge a PR that bumps `pyproject.toml` to a new version → `v$NEW_VERSION` is created and visible via `git tag --list`.
- Merge a PR that does not bump the version → workflow exits 0 with no new tag.
- Re-run the workflow on a commit that already has its tag → idempotent no-op.

---

## Workflow 2: `publish.yml`

### Required behaviour

| Aspect | Required value |
|---|---|
| `name` | `publish` (or `Build and Publish Image`) |
| `on` | `push: tags: ["v*.*.*"]` |
| `permissions` | `contents: read`, `packages: write` |
| `concurrency` | group keyed on `publish-${{ github.ref }}` with `cancel-in-progress: false` |

### Required steps

1. `actions/checkout@v5`.
2. `docker/setup-qemu-action@v3`.
3. `docker/setup-buildx-action@v3`.
4. `docker/login-action@v3` with:
   - `registry: ghcr.io`
   - `username: ${{ github.actor }}`
   - `password: ${{ secrets.GITHUB_TOKEN }}`
5. `docker/metadata-action@v5` with:
   - `images: ghcr.io/rigrergl/memento`
   - `tags: type=semver,pattern={{version}}` and `type=ref,event=tag`
   - **No `latest` tag.**
6. `docker/build-push-action@v6` with:
   - `context: .`
   - `platforms: linux/amd64,linux/arm64`
   - `push: true`
   - `tags: ${{ steps.meta.outputs.tags }}`
   - `labels: ${{ steps.meta.outputs.labels }}`
   - `cache-from: type=gha`
   - `cache-to: type=gha,mode=max`

### Forbidden

- MUST NOT push `:latest` (FR-011).
- MUST NOT run on `push` to branches — only on tag push.
- MUST NOT require any secret beyond `GITHUB_TOKEN`.

### Test plan

- Push a tag `v0.0.1-test` (manually, in a throwaway run) → image at `ghcr.io/rigrergl/memento:0.0.1-test` is pullable for both architectures.
- Run `docker manifest inspect ghcr.io/rigrergl/memento:<tag>` → JSON includes both `linux/amd64` and `linux/arm64` entries.
- Run a second push with the same tag → action fails (immutable tags) — confirms tag immutability.

---

## Joint test (post-merge bootstrap)

Per spec FR-011 §Bootstrap and research §R12: after merging the implementation PR, the maintainer runs through the sequence:

1. PR merge → `auto-tag.yml` creates `v0.0.2`.
2. Tag push → `publish.yml` builds and pushes `ghcr.io/rigrergl/memento:0.0.2` and `:v0.0.2`.
3. Maintainer sets package visibility to Public in GitHub Packages settings.
4. From a clean machine: `git clone … && docker compose up -d` succeeds without authentication.

This sequence MUST complete in the same session as the merge to keep the `main` window short.
