# AGENTS.md

Machine-readable operating guidance for AI coding agents in **qgis-osm-conflator**.

Project: **qgis-osm-conflator**  
Accountability: human maintainers are responsible for all merged changes.

---

# 1) Current Architecture

qgis-osm-conflator is a QGIS plugin that includes:

- An OSM data extractor using PostPass.
- OSM login within QGIS.
- An automated conflation UI to merge OSM data with a new dataset as far as possible without intervention.
- A manual conflation UI to manually resolve conflicts in the conflation.
- An OSM changeset creator and submission flow for OSM.

Active app paths:

- `osm_conflator/OSMConflatorPlugin.py`
- `osm_conflator/actions.py`
- `osm_conflator/dialog.py`
- `osm_conflator/conflation/`
- `osm_conflator/login/`
- `osm_conflator/postpass/`

---

# 2) Agent Workflow Contract

Use this execution loop:

1. Discover
   - Inspect current code paths first.
   - Prefer existing patterns over inventing new ones.
2. Plan
   - Keep edits minimal and task-scoped.
   - Identify tests to update/add before coding.
3. Implement
   - Keep handlers thin.
   - Put non-trivial logic in focused modules.
4. Verify
   - Run targeted checks first, then broader checks.
   - Use pre-commit to check lint/format issues across the repo: `uv run pre-commit --all-files`.
   - Report what you could and could not verify.
5. Summarize
   - List changed files and behavioral impact.
   - List risks and follow-up actions if any.

For large work, deliver in safe incremental commits/patches rather than one monolith.

---

# 3) Coding Standards

- Prefer explicit, simple, readable code.
- Avoid unnecessary abstractions.
- Keep functions focused and small.
- Add comments only where intent is non-obvious.

---

# 4) Security and Safety Boundaries

Never:

- Commit `.env` or credentials.
- Hardcode secrets/tokens.
- Bypass auth/permission checks.

Ask first before:

- New dependencies.
- Auth model changes.
- CI workflow changes.

---

# 5) Repo Change Boundaries

Do not modify these unless explicitly requested:

- `.env`
- CI workflows under `.github/workflows/`

---

# 6) Dependency and Versioning Policy

- Use Conventional Commits.
- Keep dependency diffs minimal and justified.
- Respect Renovate flow (`renovate.json`) if present.
- Avoid opportunistic upgrades unrelated to the task.

If requested by maintainers, include:

```text
Assisted-by: <Tool Name>
```

---

# 7) Done Criteria

A change is "done" when all are true:

1. Behavior implemented and documented in code/tests.
2. Relevant checks pass (or blockers are explicitly reported).
3. Lint/format checks run for changed scope.
4. File-level summary and risk notes are provided.

When uncertain, ask instead of assuming.
