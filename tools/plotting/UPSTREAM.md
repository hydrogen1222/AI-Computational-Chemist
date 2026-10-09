# Stormy-drawing vendored source

**Single upstream source of truth:** https://github.com/hydrogen1222/Stormy-drawing

- Upstream revision: `900add75a2978597640484d0b805a3d760a9da1b` (`main`, 2026-10-05).
- Upstream path: `skills/plotting/`.
- AICC vendored path: `tools/plotting/`.
- Plotting style version in this snapshot: `0.5.0`.
- Files from upstream `skills/plotting/` (SKILL, scripts, templates, references, demo) are copied **byte-for-byte**; the original MIT license and authorship are retained in `UPSTREAM_LICENSE`.
- The separate AICC changes are routing, deprecation guidance for legacy report figure styles and integration smoke tests. Avoid editing the vendored copies in AICC: implement enhancements in Stormy-drawing, then re-sync and verify all Git blob hashes.
- No Arial font binaries or other licensed fonts are included.
- **Existing AICC reports and computational scripts are not automatically restyled.** Legacy figures and analysis-script PPT previews remain compatible; follow the canonical plotting Skill to make finished figures.
- AICC `install.sh` already discovers `tools/*/SKILL.md`, so `plotting` is installed alongside the other enabled skills with no separate Stormy-drawing installation step. If a project's existing `plotting` installation is managed by Stormy-drawing, do not overwrite it without explicitly reconciling installation ownership. Running two independent installers may point their harness aliases to different copies.
- For an existing project's `figures/_style/pubstyle.py`, running `python <installed-plotting-skill>/scripts/init_figure.py --update-style <project>` archives an older style and updates the copy. Existing finished figures then need to be re-rendered and rechecked; this does **not** happen automatically on installing AICC.
