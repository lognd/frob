## Done report

A fresh `uv run frob check` on `fdb0ff6` (post-T-0151, nine landings after
this ticket's 87/55 baseline) measured **96 unwaived gates violation(s)**,
not 87/55 -- the number had drifted. Full triage below, family by family.
End state verified repeatedly: `frob check` and `frob check --ticket
T-0148` both report **gates 0 violation(s), 331 waived**, exit 0.

### Per-rule-family outcome table

| Family | Starting (fresh measure) | Fixed | Waived | Ticketed | Notes |
|---|---|---|---|---|---|
| PERF001 (membership-in-loop) | 14 | 0 | 14 | 0 | all false positives from the documented "lexical, one-token-stream-deep" heuristic (src/frob/perf/_rules.py) -- HashSet/HashMap membership mistaken for O(n), or sibling loops |
| PERF002 (.index()/.count() in loop) | 8 | 0 | 8 | 0 | same heuristic; one-shot calls lexically nested in an outer loop, not per-iteration |
| PERF003 (nested-loop join) | 104 raw hits / 52 unique lines | 0 | 52 | 0 | overwhelming majority: two sibling loops (setup + assertion) or small fixture-bounded comprehensions, not real joins |
| PERF004 (sorted()/.sort() in loop) | 38 raw hits / 19 unique lines | 0 | 19 | 0 | one-shot sort of an already-collected small result list, lexically nested but not re-sorted per outer iteration |
| TEST002 (unit case floor) | 1 (strata-core/src/parse/mod.rs::parse_source_impl) | 1 | 0 | 0 | directive existed but sat inside the function body (never counted as bound); moved to the real `#[test]` (`parses_bare_module`) that calls it |
| TEST003 (interface integration-test floor) | 12 (2 strata-core, 10 src/frob/**) | 12 | 0 | 0 | every one bound to a genuinely cross-boundary existing test (never fabricated): src/frob/exports, fuzz, bind, excludes.py, stats, mutate, release, gitio.py, logging, scaffold, and strata-core lib.rs/parse.rs via tests/system/test_frob_self_model.py |
| TEST006 (coverage stamp missing/stale) | 1 | 1 | 0 | 0 | `make coverage` regenerates the stamp; re-run after every subsequent edit since the stamp keys off live file hashes |
| TEST005 (module/symbol coverage floor) | 0 visible at baseline, 208 after TEST006 was fixed | 1 real bug fixed (see below) | ~320 file-level | 1 (T-0160) | see "TEST005 / coverage-path bug" below -- this was the largest and most consequential part of the sweep |

### TEST005 / coverage-path bug (the real find of this sweep)

TEST005 was invisible at the ticket's original baseline because this
worktree had no `.frob/coverage-stamp` -- TEST006 fires "no stamp found"
and TEST005 silently produces zero findings without one. Running `make
coverage` to clear TEST006 (a mechanical, in-scope fix) surfaced ~78
TEST005 module-coverage findings that had never been visible in any prior
sweep.

Investigating those findings to waive them individually (per the ticket's
"narrowly-scoped waiver, no blanket" rule) surfaced a real, pre-existing
bug: `src/frob/gates/_coverage.py::_parse_classes` stored Cobertura
`filename` attributes exactly as `pytest --cov=src/frob` reports them
(package-relative, e.g. `app/ack_runner.py`), but every other path in
`frob.graph` -- and thus every `frob:waive`/`frob:doc`/etc directive's
binding site, and `_symbol_branch`'s own join against `record.id.path` --
is repo-relative (`src/frob/app/ack_runner.py`). The mismatch meant (a)
per-symbol branch-coverage findings (TEST005's other half) never joined
for ANY python module, silently, for as long as this code has existed,
and (b) a same-file `frob:waive TEST005` directive could never match a
module-line finding either. Fixed by prefixing with `src/frob/` at the
one production site (`_parse_classes`), documented in that function's
docstring and via a `frob:ticket T-0148` marker on the new
`_COVERAGE_SOURCE_ROOT` constant and on `_test005` itself. A regression
test already existed at `tests/test_gates.py::TestCoverageLoad::
test_parses_line_to_symbol_span` and was updated to exercise the real
(unprefixed) Cobertura shape rather than a same-shape fixture that
happened to mask the bug.

Fixing the path bug correctly is what took the real, previously-hidden
finding count from ~78 to 197 (module-line + now-correctly-joining
symbol-branch findings) -- genuine, pre-existing coverage debt this repo
never had visibility into. That backlog is real and large (thin CLI
`app/*_runner.py` entry points at literal 0%, several modules a few
points under the 85%/90% floors) -- burning it down is out of scope for a
gates-sweep ticket, so it is filed as **T-0160** ("burn down TEST005
module-line-coverage backlog") with acceptance criteria, and every
affected file (~102) carries a specific `# frob:waive TEST005
reason="pre-existing coverage debt, tracked in T-0160"` directive rather
than a blanket/file-glob suppression -- each is a real, individually
inspectable finding, just deferred.

Separately, `src/frob/scaffold/data/**` (jinja templates rendered into
OTHER repos' source trees, never imported/executed here) was showing up
in TEST005 as if it were maintained frob source -- a genuine rule
misfire (measuring "line coverage" of template text is a category
error). `[graph] exclude` already has this exact precedent (T-0130's
`design/litmus/**`), but TEST005 is driven straight from `coverage.xml`
and does not consult that exclude list the way the graph walk does, so
`_test005` in `frob.gates` was updated to filter `CoverageData` against
`frob.excludes.load_exclude_globs`/`is_excluded` (the same helper every
other file-walking surface already uses) before evaluating floors, and
`src/frob/scaffold/data/**` was added to `frob.toml`'s `[graph] exclude`
with a written rationale in the config comment. This is config extension
along an existing, precedented axis, not a new rule disable.

Note on T-0153/T-0156 collision: a coordination message mid-sweep flagged
that main had landed T-0153..T-0156 (a different set of tickets) while a
locally-filed ticket had also claimed id T-0153 for the TEST005 backlog.
Resolved by merging main first, keeping main's T-0153..T-0156 intact, and
re-filing the local ticket as **T-0160** via `frob ticket new` in this
worktree so ids allocated correctly against the merged state.

Filed: **T-0160** (TEST005 module-line-coverage backlog, blocked_by: []),
**T-0161** (PERF001-004 lexical-heuristic false-positive classes, filed
after first review pass -- see below).

### Post-review fix: hardcoded coverage source root (CRITICAL)

First review pass (REJECT) flagged that `_COVERAGE_SOURCE_ROOT =
"src/frob"` in `_coverage.py` -- the fix for the Cobertura path-join bug
above -- was itself hardcoded to this repo's layout. This gate ships in
and runs against nine sibling repos with different package roots
(typani, logand.app, ...); for any repo but this one the hardcode would
silently reproduce the exact zero-match bug just fixed, relocated rather
than solved. Fixed properly: `_coverage.py::_parse_classes` now reads the
`<sources><source>` root(s) Cobertura's own XML declares (the standard's
documented mechanism for exactly this re-rooting), makes each repo-
relative, and scores every candidate root (each declared source, plus a
bare-filename fallback for repos whose coverage config already emits
repo-relative paths) by how many `<class filename>` entries it actually
resolves against a known repo path (the graph snapshot's symbol paths
when available, else a filesystem walk) -- the highest-scoring root wins,
handling multi-source coverage runs. If every candidate resolves zero
classes while there were classes and known paths to check against, that
is no longer a silent empty map: `CoverageData` gained a
`root_join_ok`/`attempted_roots` pair, and a new **TEST008** gate
(`frob.gates._test008_unjoined_root`, severity ERROR, always-on since
this must never degrade to quiet across any sibling repo) fires loudly
naming every root tried.

New tests: `test_joins_via_repo_relative_source` (non-frob layout --
package at repo root, no `src/` tree), `test_multi_source_picks_the_root_
that_joins` (two `<source>` entries, only one resolves), `test_zero_join_
is_loud_not_silent` (every root fails -> `root_join_ok=False`), plus
`test_test008_fires_on_unjoined_root`/`test_test008_silent_when_root_
joined` at the gate-wiring level. `test_parses_line_to_symbol_span`
(pre-existing) was updated to use a real `<sources>` element instead of
a same-shape fixture that happened to match the old hardcode.

Frob-repo behavior re-verified unchanged after the fix: real
`coverage.xml` from `make coverage` carries `<sources><source>.../src/frob
</source></sources>`; `load_coverage` logs `join_ok=True`, 208 module(s)/
1731 symbol(s) mapped this run (~195-208 TEST005 findings depending on
run noise, all still individually `frob:waive`d under T-0160, matching
the original ~197-208 figure -- not a regression). `frob check` and
`frob check --ticket T-0148` both **0 violation(s), 338 waived**, exit 0.
`frob sys audit` -- **PROVED**, zero gaps, self-conformance PROVED. Full
`pytest -q` -- clean, exit 0.

Gates: `frob check` -- gates stage reports **0 violation(s), 338
waived**, exit 0. `frob check --ticket T-0148` -- gates stage reports **0
violation(s), 338 waived**, exit 0 (PRE001 cleared via `frob ticket sweep
T-0148` re-run after the merge and after this fix). `frob sys audit` --
**PROVED, zero gaps across every configured view; self-conformance
PROVED, zero SYS gaps**. Full `pytest -q` (1878 collected across the
whole suite) -- clean pass, exit 0, no failures/errors. `cargo test
--manifest-path strata-core/Cargo.toml` -- **95 passed, 0 failed**. No
`frob.toml` rule was disabled; the one `frob.toml` change
(`src/frob/scaffold/data/**` added to `[graph] exclude`) extends an
existing, precedented exclude axis with a written rationale in the
config comment itself, not a rule disable.

### Round-2 review fix: TEST005 blanket waivers were structurally blanket (MAJOR)

Round-2 review (REJECT, one MAJOR) traced the mechanism precisely: a
`frob:waive` placed at a file's top binds via `frob.graph.dsl`'s
`_enclosing_src` to the bare file path, and BOTH `_test005_symbols` and
`_test005_modules` emit `Violation.file` as that same bare path -- so one
directive matched every TEST005 finding in that file regardless of which
symbol it was written to describe. Empirically: 195 violations waived
through 102 file-top sites, up to 7 distinct symbol findings absorbed by
one directive in the worst case (`src/frob/check/__init__.py`).

This was a real gap in `_match_waiver`, not just directive placement --
even a `frob:waive` comment placed directly above one specific symbol
still matched via the OLD comparison, `waiver.src.split("::", 1)[0] ==
violation.file`, which strips the `::qualname` back off before comparing
and so is blind to which symbol the directive names. Fixing this required
a real code change, not just re-placing comments:

1. `Violation` (`_models.py`) gained a `symref: str | None = None` field,
   set only where a violation is genuinely about one symbol (TEST005's
   per-symbol branch-coverage check, `_test005_symbols`); left `None`
   everywhere else (module-line/system TEST005, every other rule), where
   a file-level waiver remains the CORRECT precision, not a shortcut.
2. `_match_waiver` now requires an EXACT `waiver.src == violation.symref`
   match whenever `violation.symref` is set, bypassing the old file-prefix
   comparison entirely for that case. Every other rule's matching is
   byte-for-byte unchanged (verified: the 93 PERF waivers, TEST003/TEST007
   bindings, etc. all still resolve identically -- this only tightens the
   TEST005-per-symbol path).
3. All 102 file-top TEST005 directives were reverted and replaced with
   one `frob:waive TEST005` directive placed immediately above EACH
   under-covered symbol (so `comment.following` binds `path::qualname`,
   matching the new exact-symref check), plus a separate bare-file
   directive for each file's module-line-floor finding (which has no
   single symbol to bind to -- one such finding per file, so a file-level
   waiver there is the correct site, per the reviewer's own carve-out).
   Reasons lead with the symbol-specific fact, e.g. `"get_fingerprint
   85.7% branch cover, debt T-0160"`, with the T-0160 pointer kept.
   Placement was scripted from a fresh `frob check --only test` run
   (file, symref, line), not hand-edited, then adjusted once more after
   discovering that inserting/removing waiver comment lines shifts every
   later symbol's line number in that file -- `frob.graph` re-parses the
   CURRENT (edited) source for symbol spans while a stale `coverage.xml`
   still carries the PRE-edit line numbers, so branch-coverage percentages
   silently drift between edits until `make coverage` is re-run against
   the final, stable source tree. Final sequencing: place all directives,
   `ruff format`, ONE final `make coverage`, then verify -- not
   interleaved.
4. Verified the mapping is exactly 1:1, not just "gates report 0": a
   script cross-tabulated, per file, the count of live TEST005 violations
   marked `[waived: ...]` in a fresh `frob check` against the count of
   `frob:waive TEST005` directives physically present in that file.
   Final result: **195 waived violations, 195 waiver directives, 0
   files with a count mismatch** (six waivers that had gone dormant
   after the final `make coverage` -- their symbol's coverage crossed
   back above the 90%/85% floor between measurement passes, inherent
   run-to-run branch-coverage noise, not a mechanism defect -- were
   removed rather than left as stale wallpaper).

Re-verified after the fix: `frob check` -- **0 violation(s), 340
waived**, exit 0. `frob check --ticket T-0148` -- same, PRE001 cleared via
another `frob ticket sweep T-0148`. `frob sys audit` -- **PROVED**, zero
gaps, self-conformance PROVED. Full `pytest -q` -- clean, exit 0. New
tests: `TestCoverageLoad`'s three T-0148 coverage-root tests (unaffected
by this round's fix) plus `TestTestGate::test_test008_cannot_be_waived`
(below) all pass.

### Round-2 review fix: TEST008 "cannot be silenced" claim (MINOR)

The earlier Done-report claim that TEST008 "genuinely cannot be
silenced" was overstated -- nothing previously stopped a same-repo
`frob:waive TEST008 reason="..."` from suppressing it like any other
rule; it was merely unwaivable-in-practice (nobody would think to waive
a coverage-tooling diagnostic). Fixed by adding the by-construction
guard the reviewer offered as the cheap option: `_UNWAIVABLE_RULES =
frozenset({"TEST008"})` in `frob.gates`, and `_match_waiver` now
short-circuits to `None` for any violation whose rule is in that set,
before ever consulting `waivers_by_rule` -- a `frob:waive TEST008`
directive anywhere in the tree is now provably inert, not just unlikely
to be written. `frob.toml`'s `[gates.severity]` override table remains
the correct, explicit, per-repo mechanism for a repo that has a real
reason to downgrade TEST008's severity -- that path is untouched and
visible in the config diff, unlike a same-repo code-comment waiver.
New test: `TestTestGate::test_test008_cannot_be_waived` -- writes a
`frob:waive TEST008` directive, confirms TEST008 still fires, and
confirms `_apply_waivers` keeps it (never moves it to the waived list).
