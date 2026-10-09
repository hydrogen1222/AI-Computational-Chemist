# AICC CLI

The CLI is **optional**. It manages installed skill discovery and offers local
collection diagnostics; it no longer implements a scientific project state
machine, task claims/leases or job scheduling.

```bash
aicc skill --help
aicc doctor
```

The main entry is `aicc.py`, the trusted installed launcher is `launcher.sh`,
and subcommands live in `commands/`. `skill` only edits managed skill
configuration/symlinks; `doctor` is read-only. Scientific model generation and
checks are handled by the procedure/tool skills, not the CLI.

See [CONTRACT.md](CONTRACT.md) for safe mutation boundaries.
