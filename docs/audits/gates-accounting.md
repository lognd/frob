# Gates accounting audit -- "if frob check passes, the code is actually good"

Status: 2026-07-20

Scope: `src/frob/gates/__init__.py` (4056 lines) plus `_coverage.py`, `_baseline.py`,
`_filehash.py`, `decisions.py`, `invariants` region, and the drift facet machinery in
`src/frob/graph/lock.py` / `digest.py` / `dsl.py` that the DRIFT gates depend on.
North-star claim under test: passing `frob check` implies the code is good.

Bottom line: the accounting gates are overwhelmingly **existence/presence checks over
COLLECTED (not asserting, not executed) test node ids and over EDGE presence (not content
match)**. The only two gates that measure real behavior -- TEST005 (branch coverage) and
DRIFT001 (doc content) -- are respectively (a) non-blocking WARN and silently absent for
unexecuted code, and (b) keyed to the SIGNATURE facet by default so behavior changes never
trip them. The north-star claim is false in several structural, non-theoretical ways below.

---

## (A) What each rule actually checks, and the real mechanism

- **COV001** (`_cov001`, :1017; WARN): a public symbol has an explicit *resolving*
  `frob:doc` edge. Checks edge PRESENCE only, not that the doc says anything true.
  Generated files and test files exempt. Severity WARN -> never blocks.
- **COV002** (`_cov002`, :1190; check `_cov002_check_symref` :1219): a diff-touched symbol
  is bound to an open ticket by `frob:ticket` edge, OR any open ticket's `scope` glob covers
  its file, OR its `.strata` module carries the edge, OR a DONE ticket whose close lands in
  the same diff's `tickets.md` hunk (grace window). Diff-based (`_touched_symrefs`).
- **COV003** (`_cov003`, :1253): a DONE ticket's evidence ids resolve to a collected test /
  cmd evidence. Existence of collected node id, not that it asserts anything.
- **COV004** (`_cov004`, :1324): attachment sha256 matches file on disk.
- **DRIFT001** (:907): an ACKED doc facet's digest moved. Facet defaults to `sig`
  (`lock.py:_DEFAULT_FACET = "sig"`, :36).
- **DRIFT002** (:931): an edge endpoint no longer resolves to a live symbol.
- **DOC002** (`docanchor_gate`, :3466; ERROR): every `frob:doc <file>#<slug>` target file
  exists and slug resolves. Real, sound.
- **SCOPE001** (`scope_gate`, :1566; ERROR): diff touches paths outside the ACTIVE ticket's
  scope. Active ticket is derived from branch name (`active_ticket`, :882). Cross-ticket
  exemption via git-blame + commit-subject ticket ref (`_commit_exempts_file`, :1514).
- **PRE001** (`prework_gate`, :1646; ERROR): an IN_PROGRESS ticket has a recorded pre-work
  sweep whose `scope_digest` still matches. Sweep loaded from `.frob/prework/<id>.json`.
- **TEST001** (:1792; ERROR): a public function/method has >=1 collected unit-test node id,
  either via a `frob:tests` edge with execution evidence OR a naming-convention match
  (`_inferred_unit_cases`, :458).
- **TEST002** (:1809; **WARN**): collected unit case count >= `min_unit_cases`.
- **TEST003/004/009** (:1897/:2142/:1994): per-package / per-`[[system]]` / per-`.strata`
  minimum integration/e2e edge counts (valid = has execution evidence).
- **TEST005** (:2170; **WARN**): per-symbol branch, per-module line, per-system line coverage
  floors from `coverage.xml`.
- **TEST006** (:2406; ERROR): `.frob/coverage-stamp` present and not stale vs live file hashes.
- **TEST007** (:2089; WARN): `frob:uses-contract` boundary has a pairwise integration test.
- **TEST008** (:2292; ERROR, unwaivable): coverage.xml had class data but none joined a repo path.
- **TEST010** (:2422; ERROR): a malformed `frob:tests kind=` surfaced from parse errors.
- **INV001** (:1690; ERROR): an invariant's evidence list has >=1 item resolving to a
  collected test or loaded policy rule id. **INV002** (:1708): invariant has a code anchor.
- **REL001** (`release_gate`, :3160; ERROR, opt-in on `.frob-release.json`): `diff_class`
  between the committed manifest's stored API and current snapshot demands a version bump the
  declared version does not satisfy; or changelog omits the version.
- **TICK001/002** (:2567/:2600; ERROR, unwaivable): dup id in active+archive ledger; a
  `T-draft-*` id reaching the default branch.
- **WAIVE001** (:495): `frob:waive` missing `reason=`. **WAIVE002** (:650): `frob:waive`
  targets a rule id that can never match (validity/completeness check).
- **TODO001** (:1357/:1383): a `frob:todo` edge bound to a non-open ticket, or a bare
  TODO/FIXME in a diff-touched file.
- **DEC001/002** (`decisions.py`): a `frob:decision` edge targets a missing record; an
  accepted decision has no code anchor.

Waiver application (`_apply_waivers` :795, `_match_waiver` :769): three site-match modes
(symbol-exact when `violation.symref` set, file-scoped, package-prefix), plus optional
`ceiling=`. `_UNWAIVABLE_RULES = {TEST008, SEC003, TICK001, TICK002}` (:620).

---

## (B) FALSE-NEGATIVE / EVASION hunt (priority)

### B1. A vacuous test satisfies TEST001; TEST002/005 are non-blocking. [HIGH]
TEST001 is the ONLY blocking (ERROR) per-symbol test gate. It is satisfied by a single
collected pytest node id whose name contains the function's snake name
(`_inferred_unit_cases`, :458-477) -- or by a `frob:tests` edge whose `src` merely collects
(`_edge_has_execution_evidence`, :388). Nothing anywhere inspects assertions, return values,
or whether the symbol under test is even called. `def test_myfunc(): pass` collects, matches
by name, and clears TEST001. TEST002 (case count) and TEST005 (branch coverage) are both
**WARN** (:1819, :2203) -- they never fail `frob check`. So the whole per-symbol test story
reduces to "a collected test exists whose name contains the function name." Untested code
passes trivially.

### B2. DRIFT default facet is `sig` -- behavior/body rewrites never drift acked docs. [HIGH]
`lock.py:36 _DEFAULT_FACET = "sig"`; `_facet_for_ref` (:73) only returns `body`/`doc` when a
`frob:describes ... facet=body|doc` directive exists (`dsl.py:105` default `sig`).
`digest.py` computes three independent digests (sig/body/doc) precisely so "a body-only
refactor never invalidates a contract doc." The consequence for the north-star: acknowledge a
`frob:doc` at the default `sig` facet, then completely rewrite the function body so the
documented behavior becomes a lie -- DRIFT001 (:907) stays green because the *signature*
digest is unchanged. Doc-drift detection is blind to behavior by default. Repro: ack any
documented function, change only its body, run `frob check` -> no DRIFT001.

### B3. TypeScript/C/C++ `frob:tests` edges need ZERO execution evidence. [HIGH]
`_edge_has_execution_evidence` (:404-409): for a src whose extension is in
`_NATIVE_TEST_EXTENSIONS` (`.ts/.tsx/.c/.h/.cpp/.hpp/.cc/.hh`), an edge counts as valid if it
merely (a) looks like test code by name (`_is_native_test_symref`: a `tests` path segment or
`test_`/`_test` leaf) and (b) resolves to a bound symbol in the snapshot. frob runs no TS/C/C++
test collector, so the test is NEVER executed -- an empty `void test_foo() {}` that exists in
the graph satisfies TEST001 and contributes 1 to `_case_count` (:429-431). An entire native
codebase's "tests" can be non-functional stubs and every TEST001-004 passes.

### B4. TEST005 silently skips any symbol with no coverage entry. [MEDIUM]
`_test005_symbols` (:2187): `pct = data.symbol_branch.get(record.symref); if pct is not None
and pct < floor`. `_symbol_branch` (`_coverage.py:254`) only populates a symref when its file
appears in `coverage.xml` AND some line in the span has a coverage record. A module that no
test ever imports/executes produces NO `<class>` line rows for that symbol -> `pct is None` ->
**skipped, not flagged**. So the branch-coverage floor measures nothing for exactly the code
that is least tested (never executed at all). Combined with B1 this means completely
dead-but-public code clears both TEST001 (name match) and TEST005 (no data -> skip).

### B5. Whole coverage/accounting evidence chain is gitignored -- CI cannot trust it. [MEDIUM]
`.gitignore` ignores `.coverage`, `coverage.xml`, and `.frob/` (lines 10/11/20). Therefore
`coverage.xml` (TEST005/008 source), `.frob/coverage-stamp` (TEST006), `.frob/baseline`
(`--delta`), and `.frob/prework/*.json` (PRE001) are all local, never committed. A fresh CI
checkout has no stamp (TEST006 ERRORs until CI regenerates), and whatever coverage it does
enforce reflects only the `coverage.xml` that CI just produced -- an author can `make coverage`
against a trivially-configured or partial pytest run locally and pass TEST005/006, and there is
no committed artifact any reviewer or CI can diff to detect it. The pre-work sweep (PRE001) is
purely local ephemeral state and is unverifiable after the fact.

### B6. `_inferred_unit_cases` collides across identically-named symbols. [MEDIUM]
`_inferred_unit_cases` (:458) counts any collected node whose last `::` segment, snake-cased,
contains the symbol's leaf name as a whole token. Two different public functions both named
`parse` (in different modules) are both "covered" by a single `test_parse` that exercises only
one of them. Likewise a symbol `run` is credited by `test_run_server` that never touches it.
The convention fallback is name-based only, with no module/path binding, so a real test for
symbol A silently satisfies TEST001 for unrelated symbol B. Repro: two `def parse()` in
different files, one `test_parse` -> both clear TEST001.

### B7. Parametrized vacuous test inflates the case count. [MEDIUM]
`_case_count` (:413) counts each `base[param]` expansion as its own case. A single
`@pytest.mark.parametrize("x", range(10)) def test_foo(x): pass` reports 10 cases and clears
any `min_unit_cases` for `foo` -- while asserting nothing. (TEST002 is WARN anyway, but
TEST003/004/009 use `_valid_edges`/counts the same way for blocking-ER edge floors.)

### B8. COV002/SCOPE001/TODO(bare) fail open on empty/failed diff. [MEDIUM]
`_load_diff` (:3653) degrades to an EMPTY diff (logging a warning) whenever `working_diff`
fails (unknown base, detached HEAD, etc). All of COV002 (:1190), SCOPE001 (:1566), and the
bare-TODO scan (:1383) are diff-driven; an empty diff means "no touched symbols/files" -> they
all pass. Default base is `main` (`_models.py:114`). Committing directly ON `main` yields an
empty diff-vs-`main`, so COV002 (changed symbol needs a ticket), SCOPE001, and bare-TODO
detection never fire for that work. Point `--base` at HEAD, or work on `main`, and the
accounting gates that depend on the touched set go dark -- silently, as a warning nobody reads.

### B9. SCOPE001 / PRE001 disabled entirely when no active ticket. [MEDIUM]
`_build_ticket_scoped_jobs` (:3875): scope and prework jobs are only registered when
`st.ticket is not None`. `active_ticket` (:882) derives the ticket from the branch name's
`T-####` prefix. A branch not named after a ticket (or work on `main`) -> no active ticket ->
scope and pre-work gates are SKIPPED (not failed). Scope enforcement is thus opt-in by branch
naming convention; renaming the branch evades it.

### B10. COV002 satisfied by ANY open ticket whose scope glob covers the file. [MEDIUM]
`_cov002` uses `_open_scopes` (:1065) = every open ticket's scope, and `_scope_covers`
(:1074) matches the file against ANY of them. A single broad-scope open ticket (e.g. scope
`src/**` or `src/frob/**`) makes every changed symbol under it "accounted for," regardless of
whether the change relates to that ticket. The accounting reduces to "some open ticket's glob
happens to include this path."

### B11. File-level waiver blanket-waives every same-rule violation in the file. [MEDIUM]
`_match_waiver` (:769): when `violation.symref is None` (COV001, COV002, DRIFT, most rules), a
waiver matches if `waiver_file == violation.file`. So one `frob:waive COV002 reason="..."`
placed anywhere in a file waives ALL changed-symbol accounting violations for every symbol in
that file. Only TEST005 sets `symref` (symbol-exact matching). The package-prefix branch
(:789) further lets a waiver in any file under a directory-shaped interface id waive the whole
package's TEST003/004 requirement. Waivers are reasoned and visible, but the blast radius is
per-file/per-package, not per-finding, for everything except TEST005.

### B12. INV001 evidence is test EXISTENCE, not proof of the invariant. [MEDIUM]
`invariant_gate` (:1740): an invariant is satisfied if any evidence-list item resolves to a
collected test node id (`_evidence_collected`) or a loaded policy rule id. Nothing checks that
the named test actually asserts the invariant. "X is always non-null" is cleared by listing
any collected (even trivially-passing) test in its evidence. Same existence-not-proof pattern
as TEST001/COV003.

### B13. WAIVE002 completeness -- a waiver on a real-but-non-firing rule is NOT flagged. [LOW]
`_waive002_violations` (:650) flags a waiver only when its target is neither a known gate rule
nor a loaded policy rule id. A `frob:waive DUP001`/`ARCH001`/`SEC001` etc. that targets a real
rule id which simply does not fire in this run is "valid" and silently no-ops -- which is
correct-by-design, but means a mistargeted-but-real-rule waiver (e.g. `frob:waive COV001` when
the author meant `COV002`) silently protects nothing and is never surfaced.

### B14. REL001 changelog check passes on any substring occurrence; opt-in. [LOW]
`_changelog_mentions` (:3121) returns True if the version string appears ANYWHERE in
CHANGELOG.md (even inside an unrelated older entry, a link, or prose). And REL001 as a whole
only runs when `.frob-release.json` exists (opt-in). A repo without the manifest has no
public-API/semver enforcement at all.

### B15. TEST006 staleness misses newly added files. [LOW]
`_test006_stale` (:2383) iterates `snapshot.file_hashes` and only flags a path when
`stamped is not None and stamped != current`. A file ADDED after the last stamp has
`stamped is None` -> never flagged. You can add an entire new source module after stamping
coverage and TEST006 stays green as long as you don't edit an already-stamped file, so the
new file's coverage is unmeasured yet the stamp reads "fresh."

---

## (C) FALSE-POSITIVE / soundness (where it blocks good work)

- **DOC002 vs COV001 interplay is sound** (T-0233, `_resolved_documented_srcs` :993): a broken
  `frob:doc` no longer both DOC002-errors and satisfies COV001. Good, verified.
- **`_ceiling_ok` fails open on a malformed `ceiling=`** (:760) -- correctly avoids a false
  positive (crash/un-suppress) but means a garbled ceiling silently reverts to a permanent
  waiver (mild false-negative, noted at LOW).
- **TEST005 excludes `[graph] exclude` paths** (`_exclude_filtered_coverage` :2335) -- correct;
  prevents false positives on rendered templates.
- **`_test006_stale` returning on first stale file** is fine (any staleness fails).
- No strong spurious-block patterns found beyond the historically-fixed ones the comments
  document (T-0148 root-scoring, T-0314 repo_root, T-0108 cross-ticket scope exemption). Those
  fixes look correct on read.

---

## (D) Per-family pessimistic verdict

- **TEST001-004/009 (presence/count):** NOT good enough for the north-star. Fast way, not right
  way. They prove a named, collected test EXISTS; they do not prove it exercises or asserts the
  symbol. Native-language edges prove even less (no execution at all). This is the single
  biggest gap.
- **TEST005/006 (coverage):** the only real behavioral signal, but WARN (non-blocking),
  blind to unexecuted symbols (B4), and sourced from gitignored local artifacts (B5). Right
  idea, undermined by severity + trust model.
- **DRIFT/COV001 (docs):** DRIFT is sound for what it tracks, but the default `sig` facet makes
  it blind to behavior drift (B2), and COV001 (presence, WARN) does not compensate. Documentation
  correctness is effectively unenforced against behavior changes.
- **COV002/COV003/COV004 (ticket accounting):** COV004 (sha) is solid. COV002 is diff-fragile
  (B8) and glob-dilutable (B10). COV003 is existence-not-proof.
- **SCOPE001/PRE001:** sound logic, but both are disabled by branch naming / empty diff (B9/B8),
  and PRE001's evidence is local-only.
- **REL001:** genuinely static and sound where it runs, but opt-in and with a weak changelog
  check (B14). Depends on `frob.release.diff_class` fidelity (not re-audited here).
- **TICK001/002, DEC001/002, WAIVE001, TEST008/010:** these are the strongest -- real structural
  invariants, mostly unwaivable, fail loud. Good enough.
- **Waiver engine:** correct precision for TEST005; too coarse (file/package blanket) for
  everything else (B11).

Overall: the gates enforce that WORK IS ACCOUNTED FOR PROCEDURALLY (a ticket, an edge, a named
test, an ack exist) far more than that the CODE IS GOOD. "frob check passes" currently means
"every public symbol has a name-matching collected test and a doc edge, and every change names a
ticket" -- all of which a disciplined-but-lazy or adversarial author can satisfy without the
code being correct or tested.

---

## (E) Concrete gaps / defects (severity | one-line repro | site)

1. **HIGH** -- Vacuous `def test_foo(): pass` clears TEST001; TEST002/005 are WARN so nothing
   blocks. Repro: name one empty test after the function. `__init__.py:1785`, :1819, :2203.
2. **HIGH** -- Body/behavior rewrite never trips DRIFT001 because acked facet defaults to `sig`.
   Repro: `frob ack` a doc, change only the body. `graph/lock.py:36`, `__init__.py:907`.
3. **HIGH** -- TS/C/C++ `frob:tests` edges require no execution evidence; an empty `test_x` stub
   satisfies TEST001-004. Repro: add `void test_x(){}` bound in graph. `__init__.py:404-409`.
4. **MEDIUM** -- TEST005 skips any symbol absent from coverage.xml (`pct is None`), so never-executed
   modules escape the branch floor. Repro: a public module no test imports. `__init__.py:2187`.
5. **MEDIUM** -- coverage.xml / coverage-stamp / baseline / prework all gitignored; CI/reviewer
   cannot trust or diff the coverage claim. `.gitignore:10-11,20`; `_coverage.py:32`.
6. **MEDIUM** -- Name-only convention match credits a test for symbol A to an unrelated symbol B of
   the same leaf name. Repro: two `def parse()`, one `test_parse`. `__init__.py:458-477`.
7. **MEDIUM** -- Diff-driven COV002/SCOPE001/bare-TODO fail open on empty/failed diff; committing on
   `main` (default base) zeros the touched set. `__init__.py:3653-3668`, `_models.py:114`.
8. **MEDIUM** -- SCOPE001 & PRE001 are skipped entirely when the branch name carries no `T-####`;
   rename the branch to evade scope enforcement. `__init__.py:3882-3895`, :882.
9. **MEDIUM** -- COV002 accepts ANY open ticket whose scope glob covers the file; one broad-scope
   ticket accounts for all edits. `__init__.py:1065-1078`.
10. **MEDIUM** -- One file-top `frob:waive <rule>` blanket-waives every same-rule symref-less
    violation in the file (all rules except TEST005). `__init__.py:783-791`.
11. **MEDIUM** -- INV001 treats any collected test in the evidence list as proof, without checking
    it asserts the invariant. `__init__.py:1740-1743`.
12. **MEDIUM** -- Parametrized asserting-nothing test inflates `_case_count` to N, clearing case
    floors (and edge floors via valid-edge counts). `__init__.py:429-453`.
13. **LOW** -- TEST006 never flags newly-added files as making the stamp stale. `__init__.py:2387-2389`.
14. **LOW** -- REL001 changelog check passes on any substring occurrence of the version; whole gate
    opt-in on `.frob-release.json`. `__init__.py:3121-3130`, :3165.
15. **LOW** -- `_ceiling_ok` fails open (stays waived) on a malformed `ceiling=`. `__init__.py:760-765`.

---

## Ranked TOP 5 (fix these first for the north-star)

1. **(E1/B1) The blocking test gate proves existence, not testing.** Make at least a minimal
   branch-coverage floor on the tested symbol a condition for TEST001 credit (i.e. tie the
   name/edge match to real per-symbol coverage > 0), or promote TEST005 per-symbol to ERROR.
   Today a repo of empty tests is green.
2. **(E2/B2) Doc drift is blind to behavior.** Default `frob:doc`/DESCRIBES acks to the `body`
   facet (or require an explicit facet and drift-check body+sig together). A doc that lies about
   behavior should never pass.
3. **(E3/B3) Native-language tests are never executed yet count.** Either wire real TS/C/C++
   collectors or stop granting execution credit to unrun native `frob:tests` edges (make them an
   explicit, visibly-degraded "unverified" state, not silent TEST001 satisfaction).
4. **(E5/B5) The coverage evidence chain is untrusted local state.** Commit a signed/summary
   coverage artifact (or fail closed in CI when the stamp's `source_sha` cannot be reproduced),
   so TEST005/006 mean something a reviewer can verify.
5. **(E7+E8/B8+B9) Accounting gates fail open on branch/diff shape.** Do not silently degrade to
   an empty diff; treat a failed `working_diff` or a no-active-ticket state as a loud, blocking
   condition for COV002/SCOPE001/PRE001 rather than skipping them.

### Notes -- checked-and-correct (don't re-verify)
DOC002 anchor resolution and its reuse by COV001 (`_resolved_documented_srcs`, T-0233) is sound;
COV004 sha comparison is sound; TEST008 unjoined-root detection and the per-class root scoring
(`_coverage.py` T-0148/T-0311) are correct; TICK001/002, WAIVE001, TEST010, DEC001/002 are real
loud structural invariants; the T-0148/T-0314/T-0108 historical fixes read as correct; TEST005's
symbol-exact waiver matching (vs the old blanket bug) is correct.

### Notes -- skipped / skimmed (audit boundary)
Did NOT deeply audit: `frob.release.diff_class`/`required_version` internals (REL001 soundness
depends on them -- only the gate wiring was checked); `_secrets.py`, `_pii_structural.py`,
`_arch.py`, `_prework.py` internals beyond their gate entry points; `frob.policy.policy_gate`;
`frob.dup`/`frob.fuzz` engines (opt-in, out of the COV/TEST/DRIFT/SCOPE/PRE/DEC/INV/REL/TICK/
WAIVE/TODO families named in the task); the graph builder's symbol/public-detection accuracy
(assumed correct -- if it under-detects public symbols, TEST001/COV001 silently under-fire, an
orthogonal risk). `_touched_symrefs`/`working_diff` internals were treated as black boxes beyond
the empty-diff fail-open path.
</content>
</invoke>
