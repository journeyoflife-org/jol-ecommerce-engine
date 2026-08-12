# Release Runbook — Version Tagging

**Scope**: every `v*` release tag pushed to `origin` for `jol-ecommerce-engine`.
**Why this exists**: on 2026-08-12 a `v2.2.0` tag was pushed pointing at a
pre-merge Dependabot commit (`21e323c`) — a false release attestation. Under
**SOC2 CC7.1** a signed release tag is a cryptographic attestation that a
specific artifact set was reviewed, tested, and approved for production; under
**ISO 27001 A.12.1.2** releases must be traceable to approved changes. A tag
on the wrong commit breaks both. It was deleted and this procedure was
mandated.

## Controls in force

| Control | Where | What it prevents |
|---|---|---|
| `protect-release-tags` ruleset (GitHub) | repo rulesets, `target: tag`, pattern `v*` | creation/update/deletion of any `v*` tag by anyone except the `security` team |
| `tag-integrity-check` workflow | `.github/workflows/tag-integrity-check.yml` | mechanical detection: tag not at `origin/main` tip, CHANGELOG/pyproject version mismatch |
| This runbook | human procedure | process gaps the two mechanical controls cannot cover |

## Mandated release procedure

A release tag is cut **only on the merged `main` SHA**, never on a branch tip.

### Pre-flight checklist (all boxes mandatory)

- [ ] PR merged to `main` and CI green on the merge commit
- [ ] `git log main --oneline -1` matches the expected merge SHA
- [ ] `git diff v{prev}..HEAD --stat` shows the expected file set
- [ ] CHANGELOG version matches the intended tag version
- [ ] `pyproject.toml` version matches the intended tag version
- [ ] Tag will be created locally with `-s` (GPG-signed tag)
- [ ] Tag pushed only after CODEOWNERS approval landed on the merged PR
- [ ] No open security advisories on the merge commit

### Cut the tag

```bash
git checkout main
git pull origin main

# Confirm the tree is the merged release work
git log --oneline -5

git tag -s vX.Y.Z -m "Release vX.Y.Z: <one-line scope summary>"
git tag -v vX.Y.Z          # must show a good signature before push
git push origin vX.Y.Z
```

### Post-push verification

```bash
git ls-remote --tags origin vX.Y.Z          # SHA matches local tag object
git log vX.Y.Z --oneline -1                 # commit is the merge SHA
# tag-integrity-check run is green in Actions
```

## Recovery: wrong tag already pushed

1. Delete from origin immediately: `git push origin :refs/tags/vX.Y.Z`
   (requires `security` team membership — see ruleset above).
2. Broadcast to the team so stale local copies are purged:

   ```bash
   git tag -d vX.Y.Z
   git fetch --prune origin +refs/tags/*:refs/tags/*
   ```

3. Re-cut on the correct merged SHA following the procedure above.
4. Record the incident (what pointed where, for how long, who fetched)
   in the change-management log — a lying tag is an audit finding even
   after correction.

## Versioning rules

- Tag == `pyproject.toml` `[project.version]` == CHANGELOG `[X.Y.Z]` header,
  always, on the same commit. Bump versions in the PR that lands the change,
  never in a tag-only commit.
- Never reuse a tag name **once it has been consumed by any release or
  deployment**. Sole exception: a false tag deleted before any consumer
  saw it (as with the 2026-08-12 `v2.2.0` incident) may be re-cut on the
  correct SHA, because the attestation was retracted before distribution.
  If a shipped release must be replaced, bump the patch version (`v2.2.1`).
