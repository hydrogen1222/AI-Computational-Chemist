# AICC CLI Contract

- `aicc doctor` only reads local collection state and reports whether the
  single-agent scientific modeling and structure-prep skills are present.
- `aicc skill` manages AICC-owned instruction blocks and symlinks only.
  Preserve foreign files, links and configuration entries.
- `aicc skill disable --stale` with explicit confirmation may remove a
  verified stale AICC-owned managed link; never remove a live foreign link.
- Legacy `aicc status`, `task`, and `job` are retired. AICC does not
  create `.research/`, track jobs, claim execution leases, or submit HPC work.
- Global Skill scope targets Codex paths; local scope targets the working
  directory. Only explicit migration commands modify legacy Codex config
  with backup; failed or ambiguous link ownership does not authorize removal.
