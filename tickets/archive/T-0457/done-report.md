## Done report

Tiered `frob clean` built: `frob clean` (tier1 safe), `--all` (tier2 build/
test artifacts), `--deep` (tier3 + .frob/ caches + FROBLEMS.md). --dry-run is
the DEFAULT; -y to execute; summary via frob.render (T-0448). New package
src/frob/clean/ (_core scan/clean, _rules tier_patterns + frob.toml [clean]
extras, _models) + app/clean_runner.py, wired through __main__/config/app;
Makefile `make clean` -> --all -y and `make coverage` post-step -> tier1 -y
(drops .coverage.* fragments post-combine).

FAIL-SAFE (the critical property): operates on a KNOWN artifact ALLOWLIST
(never enumerate-untracked-then-filter); a tracked file is never removed
(git ls-files check -> skipped_tracked); an untracked file NOT on the
allowlist is NEVER removed. Recursive ** excludes .git/.venv/node_modules.
Reviewer VERIFIED the fail-safe LIVE (paranoid check): built a real scratch
repo with artifacts + an untracked non-allowlisted src/scratch_notes.py and
ran clean --deep -- all artifacts removed, the source file survived. The
reviewer's only REJECT was procedural (no Done report yet) -- this report
closes that; on the merits it is approve-quality.

Evidence (3 of 9 tests): clean_never_touches_src (git diff --stat src/ empty +
untracked source survives all 3 tiers), deep_removes_frob_state, and
scan_skips_tracked_files. Landed via 3-way + explicit copy of the 7 new files
(clean/ package + tests + docs) -- the untracked-new-file case T-0463 now
guards; enumerated with git ls-files --others so none were dropped.
