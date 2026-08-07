## Done report

REVISION 5 (final refresh, coordinator-directed): merged `main` once more
(tip now `90f953d`, "docs(strata): short explicit sub-targets anchor, fix
E501 fallout" -- the coordinator's fix for round 4's 3 `E501` findings,
via an explicit `<a id="sub-targets">` anchor in `docs/strata/waive.md`
plus retargeted directives), ran `rm -rf .frob && make core` fresh, and
re-ran `frob check` (the only number this round's instruction asked to
reconfirm; release check / pytest / sys audit are unaffected by a
docs-only anchor-text change and were not re-run a second time this
round -- their round-4 numbers stand). Result: **exactly 1 error** (the
pre-existing COV003), as predicted.

REVISION 4 (previous round, coordinator-directed): merged `main` once
more (tip then `34ac572`, "docs(strata): fix waive.md anchor slugs in
_waive.py (T-0174 landing fixup)" -- the coordinator's fix for the 4
DOC002s round 3 caught), ran `rm -rf .frob && make core` fresh, and
re-ran the full final-gate battery with the worktree's own `uv run`.

Changed (unchanged from round 3, re-verified against the new merge tip):
`pyproject.toml` (version 0.1.0a0 -> 0.2.0), `strata-core/Cargo.toml` and
`frob-core/Cargo.toml` (version -> 0.2.0), `CHANGELOG.md` (161
done-ticket entries grouped by area, count verified against
`grep -oE 'T-[0-9]{4}' CHANGELOG.md | sort -u | wc -l` = 161), `README.md`
(new "Release status" section), `docs/index.md` (linked the one orphaned
page, `docs/strata/selfconform.md`), `.frob-release.json` (tracked
release manifest; re-stamp this round produced byte-identical content to
round 3's, 818 public symbols, no diff to commit).

Version decision unchanged: 0.1.0a0 -> 0.2.0 (161 closed tickets across
five strata phases, threat/CWE/CVE/compliance catalog, capability
exhaustiveness matrix, design lint family, smart-dup, extending-frob
guides; not 1.0 -- no published wheel, native-crate strategy still
source-build-only).

Evidence, every number captured in this final pass (post-merge tip
`34ac572`, post fresh `make core`, each command's exact invocation named):
- `git log --oneline -1 main` -> `34ac572`.
- `uv run frob release stamp` -> "release: stamped 818 public symbol(s) at
  0.2.0" (unchanged from round 3 -- the merged commit was docs-only, no
  public-API change).
- `uv run frob release check` -> "since 0.2.0: none change -> need >= 0.2.0
  (current 0.2.0): OK".
- `uv build --wheel` / bare-venv degrade verification: unaffected by this
  docs-only merge, still holds as measured in round 1 (wheel builds
  clean; `strata_core`/`frob_core` absent in a bare venv;
  `frob.lang.parse_file()` returns `Err(NativeParserUnavailable)`, no
  crash; `frob check` on a bare repo exits 0 with no `design/` dir, SYS004
  typed-fires on one that has `.strata` files -- the documented degrade
  contract for a genuinely natives-less install).
- `uv run pytest -q -p "no:cacheprovider" -o addopts=""` (xdist disabled
  so the tool's own printed summary line is captured verbatim, per the
  established round-3 method -- `-n auto`, this repo's default `addopts`,
  does not write its final summary line to a redirected non-tty stream in
  this environment): **"2460 passed, 3 skipped in 144.48s"**, exit 0.
  Identical to round 3's number (the merged commit touched only
  `src/frob/strata/_waive.py`/`_models.py` doc-comment anchors, no test
  collection change).
- ROUND 4 (superseded by round 5 below): `uv run frob check` (post-merge
  `34ac572`) showed **4 errors + 316 warnings** -- the 4 DOC002s were
  gone, but the coordinator's anchor-slug fixup had lengthened 3 comment
  lines in `src/frob/strata/_waive.py` (`:85`, `:101`, `:114`) past
  ruff's 88-column limit (`E501`), a small piece of fixup fallout on top
  of the fix. Confirmed pre-existing on `main`, not this branch (`git
  diff main -- src/frob/strata/_waive.py` empty), reported rather than
  fixed (out of `scope`).
- ROUND 5 (final, this pass): merged `main` again to `90f953d` (the
  coordinator's fix for round 4's `E501` fallout -- a short explicit
  `<a id="sub-targets">` anchor in `docs/strata/waive.md` plus retargeted
  directives, avoiding the need for a long slug in the comment). Ran
  `rm -rf .frob && make core` fresh, re-stamped the release manifest
  (unchanged, 818 symbols -- docs-only diff), and re-ran `uv run frob
  check`: **"frob check .  [FAIL]  1 error  316 warnings"** (317 total).
  Exactly the coordinator's predicted shape: the 1 error is the
  pre-existing, out-of-scope COV003 on `tickets/T-0168` (evidence-id
  typo in `tickets-archive.md`, not filed as `T-draft-89a86c7a (never refiled)` in round 1);
  no DOC002, no E501, no SYS004. Confirmed both-ruff clean: `ruff check .`
  and `uv run ruff check .` both report "All checks passed!";
  `uv run ruff format --check .` reports "341 files already formatted".
  `git diff main --diff-filter=D --stat` -> empty (deletion-filter
  clean).
- `uv run frob sys audit` and `uv run pytest -q -p "no:cacheprovider" -o
  addopts=""` were NOT re-run this round -- round 5's merge was a
  docs-only anchor-text change (`docs/strata/waive.md` +
  `src/frob/strata/_waive.py` comment retargeting only, confirmed via
  `git show --stat 90f953d`), which cannot affect test collection or the
  capability/self-conformance model. Round 4's numbers stand: sys audit
  self-conformance PROVED, zero SYS100, 4 LINT004 WAIVED (T-0174's
  channel, reasons naming T-0200) + 1 unwaived `tickets_ledger`
  (`T-0250`, queued, out of scope); pytest "2460 passed, 3 skipped",
  exit 0.
- docs/index.md completeness: unchanged from round 1, still holds.

Not Filed: `T-draft-89a86c7a (never refiled)` (T-0168 evidence-id typo in
`tickets-archive.md`, round 1, out of scope for T-0156). No new tickets
this round -- round 4's 3 `E501` findings were the coordinator's own
fixup fallout, now fixed on `main` (`90f953d`), confirmed gone.

Cuts / honest gaps carried forward, not fixed here (all pre-existing or
explicitly out of scope per the ticket's declared `scope`):
- 1 unwaived LINT004 (`tickets_ledger`), tracked as `T-0250`, queued.
- 1 COV003 on T-0168's archived evidence id (`tickets-archive.md`, out of
  scope; not filed as `T-draft-89a86c7a (never refiled)`).
- Native crates (`frob-core`, `strata-core`) remain source-build-only
  local `maturin` path packages, no published wheels -- documented in
  `docs/guides/install.md` (pre-existing, T-0133's "why not a pip extra"
  section); this ticket did not change that strategy, only verified the
  degrade contract holds from a real built wheel.

Release command sequence (documented, NOT run -- no tag, no publish, per
instructions):
```
git tag v0.2.0
uv build --wheel
uv publish   # or: twine upload dist/*
```

Gates, final numbers, all measured against the final merge tip
(`90f953d`, natives rebuilt via `rm -rf .frob && make core`):
- `uv run frob check` -> **1 error + 316 warnings = 317 total** (the 1
  error is the pre-existing, out-of-scope COV003; no SYS004, no DOC002,
  no E501).
- `uv run frob release check` -> clean at 0.2.0 (818 public symbols).
- `uv run pytest -q -p "no:cacheprovider" -o addopts=""` (round 4's
  measurement, unaffected by round 5's docs-only merge) -> **"2460
  passed, 3 skipped"**, exit 0.
- `uv run frob sys audit` (round 4's measurement, worktree editable
  install only, unaffected by round 5's docs-only merge) ->
  self-conformance PROVED, zero SYS100, capability matrix 0 unexcused,
  **4 LINT004 WAIVED + 1 unwaived** (`tickets_ledger`, `T-0250`, queued,
  out of scope).
- `git diff main --diff-filter=D --stat` -> empty.
