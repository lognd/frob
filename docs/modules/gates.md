# frob.gates -- enforcement gates, policy, and invariants

One sentence: the checks that join the obligation graph, the ticket queue,
docs, and policy rules, and turn every unaccounted-for change -- and every
unaccounted-for *absence* of change -- into a `frob check` failure.

Two enforcement halves (see `docs/rework.md`): the drift half (nothing
declared is silently broken) and the coverage half (nothing new escapes
declaration).

## Rule catalog

| Rule | Gate | Fails when |
|---|---|---|
| DRIFT001 | drift | acked digest moved without re-ack (`frob ack`) |
| DRIFT002 | drift | edge endpoint no longer resolves (rename/delete) |
| COV001 | coverage | public symbol has no `doc` edge (docstring counts via `doc` facet only if policy says so) |
| COV002 | coverage | changed symbol has neither a `frob:ticket` edge to an open ticket NOR an open ticket whose `scope` glob covers its file (so one scoped ticket accounts for a whole refactor, not a per-symbol directive). A `frob:ticket` edge to a ticket that just closed to `DONE` in this same uncommitted diff (`tickets.md` itself touched) also counts -- T-0214's grace window, see design decisions below |
| COV003 | coverage | ticket in state done with evidence ids that do not resolve to collected tests (never verifies PASS/FAIL, nor scope-binding -- see the T-0398 note below the table; node-, file-, and directory-level evidence ids all resolve, T-0298 below) |
| COV004 | coverage | attachment sha256 mismatch or file missing |
| COV005 | coverage | a diff-touched file's `frob:` directive now binds a PRIVATE symbol whose span overlaps this diff's hunks, where the same `(kind, target)` directive bound a PUBLIC symbol in that file at the diff's base revision -- a displaced obligation (T-0297), see design decisions below |
| TODO001 | coverage | bare TODO/FIXME comment (not `frob:`-prefixed) in a diff-touched file -- work marked but not accounted for at all |
| TODO002 | coverage | `frob:todo` edge bound to a non-open (closed or missing) ticket -- work accounted for, but the reference is dangling |
| SCOPE001 | scope | diff touches paths/symbols outside the active ticket's `scope` |
| PRE001 | pre-work | ticket moved to in-progress without a recorded pre-work sweep |
| INV001 | invariant | invariant has no evidence (test or policy rule) |
| INV002 | invariant | invariant has no code anchor (`frob:invariant`) |
| DEC001 | decisions | a `frob:decision AD-###` edge points at a record that does not exist (opt-in: a `decisions/` dir must exist) |
| DEC002 | decisions | an `accepted` decision record has no `frob:decision` code anchor |
| TEST001 | test | public function/method has no `frob:tests` unit edge |
| TEST002 | test | unit edges for a symbol number fewer than `min_unit_cases` |
| TEST003 | test | interface (package whose public symbols are imported by another package) has fewer than `min_integration` integration edges |
| TEST004 | test | declared system has fewer than its `min_e2e` e2e edges |
| TEST005 | test | measured coverage below threshold (per-symbol branch, per-module line, or per-system line) |
| TEST006 | test | coverage evidence missing, or stale against current file hashes |
| TEST007 | test | a cross-package `frob:uses-contract` dependency has no pairwise integration test covering that boundary (opt-in via `[testing].pair_integration`) |
| DOC001 | doclink | a doc file matching `[gates.docs] include` globs (default `docs/**/*.md` -- new files auto-obligated) has no frob:describes anchor, no frob:doc edge into it, and is unreachable via markdown links from the roots (docs/index.md, README.md) |
| DOC002 | docanchor | a `frob:doc <file>#<slug>` edge whose target doesn't resolve: missing `#anchor`, missing file, or `<slug>` matches neither a heading slug (`frob.graph.dsl.slugify`) nor an explicit `<a id="...">` in `<file>` |
| POL* | policy | user-defined rules from `frob.toml` (see below) |
| DUP001/DUP002 | clones | the diff introduces a clone of an existing symbol (opt-in, `[dup].enforce`) |
| FUZZ001-003 | fuzz | fuzz obligations under `[fuzz]` (opt-in) |
| PERF001-004 | perf | lexical performance smells (build-a-set-once, etc.) |
| REL001 | release | release-readiness check |
| SYS001 | sys | a `frob:channel/boundary/secret` directive names a construct id absent from the loaded `.strata` design model (opt-in: a `design/`, or `[strata].design_dir`, directory of `.strata` files must exist); suppressed for the whole run while any design file fails to load (SYS004 reports that instead) |
| SYS002 | sys | a `Boundary` or Secret-clearance `Node` in the design model has no `frob:boundary`/`frob:secret` code binding anywhere |
| SYS003 | sys | (warn) tier-2 code binding (`frob.strata.bind_code`/`check_import_conformance`) finds an undeclared cross-component import between two design-bound files; warn-first on landing, intended to flip to error via `[gates.severity]` once proven |
| SYS004 | sys | a `.strata` design file failed to parse/elaborate; the message names a stale native build (`make core`) as the likely remedy when one is detected (T-0347, T-0248's `frob.strata.stale_natives`), per the T-0166 incident where a grammar-ahead-of-native mismatch masqueraded as a `.strata` syntax error |
| SEC001 | secrets | a git-tracked file contains text matching a provider's real-looking credential shape (waivable with reason) |
| SEC002 | secrets | a git-tracked `.env`/`.env.*` file exists (`.env.example`/`.env.sample`/`.env.template` excepted) |
| SEC003 | secrets | a git-tracked file contains a live Stripe secret key (`sk_live_...`) or a private-key PEM header -- unwaivable, see `_UNWAIVABLE_RULES` |
| WAIVE001 | (always on) | a `frob:waive` directive is missing `reason="..."` |
| WAIVE002 | (always on) | a `frob:waive` targets a rule id that can never be matched -- see "Waive boundary" below |
| ARCH001 | arch | `frob.arch`'s complexity-aware long-function check (docs/modules/arch.md) still flags a function after its flat-body filter -- the one `frob.arch` category channeled into a real gate `Violation`, waivable with a reasoned `frob:waive ARCH001 reason="..." [ceiling=N]` (T-0289) |
| PII010 | pii_structural | a pydantic/dataclass/TypedDict/attrs field's name or type annotation matches a PII-shaped signature (`FIELD_SIGNATURES`) with no `frob:waive PII010 reason="..."` -- see "PII010/SEC110" below |
| SEC110 | pii_structural | an `os.environ[...]`/`os.environ.get(...)`/`os.getenv(...)` call site with no `frob:waive SEC110 reason="..."` -- see "PII010/SEC110" below |
| REF001 | refs | a git-tracked file has zero inbound references (auto-detected or verified `frob:used-by`) from any other tracked file -- see "Anti-orphan file-reference gate" below |
| REF002 | refs | a git-tracked file has exactly one inbound reference (fragile single anchor) -- see "Anti-orphan file-reference gate" below |
| REF003 | refs | a `frob:used-by <consumer>` declaration is dangling: the named consumer does not exist as a tracked file, or does not itself reference the declaring file back -- see "Anti-orphan file-reference gate" below |
| DOC004 | docblocks | a fenced code block in a tracked `.md` doc references the project's OWN code surface (manifest-derived python/rust/ts namespaces) and either does not resolve (error, "stale") or resolves but carries no nearby `frob:doc`/`frob:describes`/`frob:tests` anchor (warn, "unbound") -- see "Unbound/stale doc code blocks" below |

**T-0398 (evidence integrity) note on COV003**: COV003 only ever answers
"does this evidence id resolve to a currently-collected test" -- it does
NOT verify the test PASSED, and does NOT verify the evidence binds to the
ticket's own touched/scope symbols (any collected id, however unrelated,
satisfies it). Those two gaps are closed at the `frob.tickets.transition`/
`land` call sites instead, via optional injected parameters
(`add_evidence(..., passed=...)`, `transition(..., covers_scope=...)`,
`land(..., collected=..., passed=..., covers_scope=...)`) rather than a
new COV rule -- `frob.tickets` deliberately has no `frob.testing`/
`frob.graph` dependency (docs/rework.md cycle-avoidance), so it cannot
compute either answer itself; a caller with graph/testing access (today,
directly testable via `frob.gates.evidence_covers_scope`; the `frob
ticket` CLI's own wiring of real values into these parameters is a
disclosed follow-up, not yet done) supplies the answer. See
docs/modules/tickets.md's `add_evidence`/`transition`/`land` entries for
the parameter contracts.

**T-0298 (file-/directory-level COV003 evidence)**: an evidence id with no
`::` at all (a bare path, e.g. `tests/test_vet.py` or `tests/unit/deploy`)
resolves iff at least one collected node id lives under it -- as that exact
file (`<path>::...`) or inside that directory (`<path>/...`). Node-level
resolution (`path::Class::method`) is tried FIRST and stays the preferred,
most precise granularity; the path-level check is a fallback, not a
replacement. It is deliberately non-vacuous: a path with zero matching
collected node ids (nothing landed there, or a typo'd/nonexistent
directory) still fails COV003 -- "this whole file/dir passes" only counts
when something under it actually collected. This exists because a refactor
touching ~20 files naturally produces evidence at file granularity ("this
test file passes"), not one node id per file; forcing node-level-only
evidence for that shape of change is what produced a real 25-error
main-red incident (2026-07-19) when two agents both recorded file-level
ids COV003 could not, at the time, resolve at all.

Severity: `error` (exit 1) or `warn`; per-rule default overridable via the
`[gates.severity]` table in `frob.toml` (`COV001 = "warn"`), applied as a
single post-processing step in `run_gates` -- the legacy-adoption dial. A
rule produced by any of the gates above is waivable at a site via
`frob:waive RULE-ID reason="..."`; waivers are listed in every report, so a
waiver is visible debt, never silence.

### Waive boundary (T-0101, revised T-0289)

`frob:waive` only ever suppresses entries in a `GateReport`'s `violations`
tuple -- `_apply_waivers` matches a waiver's target against `Violation.rule`
and can never see anything that isn't a `Violation`. `frob check`'s
`frob-arch` tool stage calls `frob.arch.analyze_project` directly and
wraps its `ArchSuggestion`s straight into `Diagnostic`s, bypassing
`frob.gates` entirely -- `god-class`, `high-coupling`, `deep-nesting`,
`abstraction-opportunity`, and `large-file` are still only reachable that
way, so a `frob:waive` naming one of those categories is flagged as
**WAIVE002** (ineffective).

`long-function` is the ONE exception (T-0289): `frob.gates._arch.arch_gate`
now runs `analyze_project` a second time inside the `archgate` GATE (a
distinct `frob check`/`run_gates` selection name from the `frob-arch` TOOL
stage above -- do not conflate the two) and turns every `long-function`
suggestion into a real `ARCH001` `Violation`, symref-bound to the exact
function. `ARCH001` is in `frob.gates._KNOWN_GATE_RULES`, so
`frob:waive ARCH001 reason="..." [ceiling=N]` is a real, effective,
auditable waiver -- not flagged by WAIVE002 -- while
`frob:waive long-function reason="..."` (the bare category name) still is,
since that string was never a rule id `_apply_waivers` could match.

Any rule id that is simply a typo or a rule that was never registered is
also flagged as WAIVE002 the same way. `frob.gates._KNOWN_GATE_RULES`
(plus the run's loaded `[policy]` rule ids) is the whitelist; anything
outside it is presumed unwaivable. If a future change makes another arch
category waivable, remove it from `_unwaivable_channel_rules`'s returned
set the same way `long-function` was removed, and update this note.

### `frob check`'s dup/arch stage summaries are also waiver-aware (T-0375)

The `frob-dup` and `frob-arch` TOOL stages (`frob.check._python._run_dup`/
`_run_arch`, distinct from the `gates` TOOL stage above) never route
through `frob.gates.run_gates`, so they don't get the gates stage's
`N error, M warning, K waived` split for free. T-0375 gave each its own
cross-reference against the obligation graph's WAIVE edges (`_run_dup`:
exact fragment-symref match on DUP001/DUP002; `_run_arch`: reuses
`_apply_waivers` over ARCH001 `Violation`s built from the already-computed
long-function suggestions, `ceiling=` included) so their headlines also
report only unaccounted findings, with waived ones still listed as `note`
diagnostics -- see docs/modules/dup.md#check-stage-summary-is-waiver-aware-t-0375
and docs/modules/arch.md#check-stage-summary-is-waiver-aware-for-arch001-t-0375.
This does not change gate pass/fail behavior anywhere -- it only makes the
advisory count in `frob check`'s printed summary honest.

## Public API

<!-- frob:describes src/frob/gates/__init__.py::run_gates -->
<!-- frob:describes src/frob/gates/__init__.py::evidence_covers_scope -->
<!-- frob:describes src/frob/gates/__init__.py::drift_gate -->
<!-- frob:describes src/frob/gates/__init__.py::coverage_gate -->
<!-- frob:describes src/frob/gates/__init__.py::scope_gate -->
<!-- frob:describes src/frob/gates/__init__.py::prework_gate -->
<!-- frob:describes src/frob/gates/__init__.py::invariant_gate -->
<!-- frob:describes src/frob/gates/__init__.py::test_gate -->
<!-- frob:describes src/frob/gates/_coverage.py::stamp_coverage -->
<!-- frob:describes src/frob/gates/_coverage.py::load_coverage -->
<!-- frob:describes src/frob/gates/__init__.py::active_ticket -->
<!-- frob:describes src/frob/gates/_prework.py::record_prework -->
<!-- frob:describes src/frob/policy/__init__.py::load_policy -->
<!-- frob:describes src/frob/policy/__init__.py::policy_gate -->
<!-- frob:describes src/frob/gates/invariants.py::load_invariants -->
<!-- frob:describes src/frob/gates/_coverage.py::load_stamp -->
<!-- frob:describes src/frob/gates/_prework.py::load_prework -->
<!-- frob:describes src/frob/gates/__init__.py::scope_digest -->
<!-- frob:describes src/frob/gates/__init__.py::decisions_gate -->
<!-- frob:describes src/frob/gates/__init__.py::dup_gate -->
<!-- frob:describes src/frob/gates/__init__.py::release_gate -->
<!-- frob:describes src/frob/gates/__init__.py::fuzz_gate -->
<!-- frob:describes src/frob/gates/__init__.py::doclink_gate -->
<!-- frob:describes src/frob/gates/__init__.py::docanchor_gate -->
<!-- frob:describes src/frob/gates/__init__.py::run_gates -->
<!-- frob:describes src/frob/gates/_baseline.py::stamp_baseline -->
<!-- frob:describes src/frob/gates/_baseline.py::load_baseline -->
<!-- frob:describes src/frob/gates/_baseline.py::is_baseline_stale -->
<!-- frob:describes src/frob/gates/_baseline.py::delta_violations -->
<!-- frob:describes src/frob/gates/_baseline.py::violation_fingerprint -->
<!-- frob:describes src/frob/gates/_secrets.py::secrets_gate -->
<!-- frob:describes src/frob/gates/_secrets.py::_redact -->
<!-- frob:describes src/frob/gates/_pii_structural.py::pii_structural_gate -->
<!-- frob:describes src/frob/gates/_pii_structural.py::_FieldSignature -->
<!-- frob:describes src/frob/gates/_pii_structural.py::_scan_python_fields -->
<!-- frob:describes src/frob/gates/_pii_structural.py::_scan_python_env_access -->

- `load_stamp` -- the raw `.frob/coverage-stamp` document, or `None` if
  never stamped/unreadable; TEST006 compares it against live file hashes.
- `load_prework` -- the recorded pre-work sweep for a ticket, or `None` if
  `frob ticket start` never ran one; PRE001 compares it to a fresh digest.
- `scope_digest` -- the one canonical sha256 over a scope glob's matched
  file hashes, shared by `frob ticket start` and `prework_gate` so PRE001
  can never see two independently-computed digests drift apart.
- `decisions_gate` -- DEC001/DEC002 over `decisions/` records and their
  code anchors; a no-op when no `decisions/` directory exists.
- `dup_gate` -- DUP001/DUP002: flags a diff that introduces a clone of an
  existing symbol; opt-in via `[dup].enforce` in `frob.toml`.
- `release_gate` -- REL001: the public-API change since the last release
  stamp demands a version bump the declared version does not cover.
- `fuzz_gate` -- FUZZ001..003 over the `[fuzz]` policy; opt-in via
  `[fuzz].enforce`, default off.
- `doclink_gate` -- DOC001: a doc file nothing links to (no describes
  anchor, no `frob:doc` edge, unreachable from the doc roots) is an error.
- `sys_gate` -- SYS001/SYS002/SYS003/SYS004 (T-0080): joins `frob:channel`/
  `frob:boundary`/`frob:secret` code directives and tier-2 code binding
  against a `.strata` design model; opt-in via a `design/` (or
  `[strata].design_dir`) directory of `.strata` files existing, same
  posture as `decisions_gate`. See docs/strata/surface.md#directives-t-0080.
- `docanchor_gate` -- DOC002: a `frob:doc` target whose anchor doesn't
  resolve (missing `#anchor`, missing file, or `<slug>` matches neither a
  heading slug nor an explicit `<a id>`) is an error.
- `secrets_gate` -- SEC001/SEC002/SEC003 (T-0157): scans every git-tracked
  file (never untracked/`.env`-skipped -- a tracked `.env` IS the SEC002
  finding) for real-looking provider credentials via a per-provider regex
  table; default-on. `redact` is the one function allowed to turn a matched
  token into printable output (`<provider prefix>... (<N> chars)`, never
  the token itself). A site is exempted by a placeholder shape inside the
  token (`XXXX`/`****` runs, or the words fake/changeme/example/placeholder)
  or by a `frob:secret-fake` marker comment on the same or preceding line
  -- deliberately NOT the pre-existing `frob:secret <construct-id>`
  directive, which already binds code to a strata design's Secret-clearance
  node id; see `frob.gates._secrets`'s module docstring for the full
  reasoning. `SEC003` (live Stripe secret keys, PEM private-key headers) is
  in `_UNWAIVABLE_RULES` alongside `TEST008`; `SEC001`/`SEC002` stay
  waivable with a written reason like every other rule.
- `run_gates` -- the single entry point: loads all state once, then runs
  the selected gates in parallel and merges/severity-overrides the result.

### Structural PII secrets detection T-0207

`frob.gates._pii_structural` -- `pii_structural_gate` (gate name
`pii_structural`, default-on, WARN severity, dial via `[gates.severity]`).
Extends `frob.strata._pii` (T-0154, declaration/join layer) and
`frob.gates._secrets` (T-0157, tracked-file token scan) with a THIRD,
previously-missing layer: structural observation of actual Python data
structures and env-var access sites, drawn from
`docs/design/secrets-pii-corpus.md`'s field-name/type keyword catalog.

- **PII010**: a pydantic `BaseModel` / `@dataclass` / `TypedDict` /
  `NamedTuple` / attrs class field whose NAME (`_`-tokenized match) or TYPE
  ANNOTATION (`EmailStr`, `SecretStr`) matches an entry in
  `FieldSignature`/`FIELD_SIGNATURES` fires -- deny-by-default, waivable via
  `frob:waive PII010 reason="..."`.
- **SEC110**: an `os.environ[...]`/`os.environ.get(...)`/`os.getenv(...)`
  call/subscript site fires -- an unmapped secret-source observation,
  waivable via `frob:waive SEC110 reason="..."`.
- Both rules are file-scoped (same waiver-matching mode as SEC001-003:
  `violation.symref` is `None`, so a waiver anywhere in the file suppresses
  every hit in it).
- Self-match exclusion (T-0201 lesson): `_pii_structural.py`'s own path is
  hardcoded-excluded from the scan, so `FIELD_SIGNATURES`'s own keyword
  string literals can never be misread as a scanned field.
- **Deliberately not built this pass** (see `_pii_structural.py`'s module
  docstring and this ticket's Done report): DB/DDL schema scanning (`CREATE
  TABLE`, sqlalchemy `Column`), structural (non-regex) email-shape value
  detection, identifier/comment keyword-sweep at suggestion severity, and
  non-Python language equivalents. Filed as follow-on tickets, not silently
  dropped. A direct join from a PII010/SEC110 finding to a T-0154 `carries`
  tag or a T-0082 `std.secrets` node (rather than a bare waiver) is likewise
  a follow-on -- today's only discharge mechanism is the waiver.

### Anti-orphan file-reference gate T-0396

`frob.gates._refs` -- `ref_gate` (gate name `refs`, default-on, WARN
severity, dial via `[gates.severity]`). Motivating case: the
`docs/design/registry/*.yaml` manifests were read by ZERO other tracked
files -- a silently dead/unenforced artifact no existing gate reasons
about, because every other gate reasons about SOURCE symbols
(`frob.graph`'s import/DSL edges), never about a bare tracked file's
existence being justified at all. This gate runs over EVERY git-tracked
file, regardless of type (source, docs, config, data, assets).

Two detection layers, both required to feed the same inbound-reference
count per file:

- **Auto-scan**: file X counts as referenced by file Y when Y's text
  names X (full repo-relative path or bare basename) in a real reference
  SYNTACTIC position -- a markdown link (`](path)`), a quoted string
  literal, a `frob:doc`/`frob:describes`/`frob:used-by`/`frob:tests`
  directive target, a `require`/`include`/`use` target, or a Python
  import (`from X import a, b, c` -- single-line, comma-list, OR
  parenthesized/multi-line -- and plain `import a, b.c`, EVERY imported
  name resolved, not just the module prefix). Deliberately NOT a bare
  substring match over the whole text: a README table cell or a
  ticket-body sentence merely NAMING a file (`` `patterns.yaml` ``) is
  not a reference in any of these shapes, and counting it as one
  silently defeats the gate. For `.py` targets only, a bare imported
  name or a dispatch table's quoted bare module-name string (e.g.
  `"ack_runner"` reaching `ack_runner.py`) also resolves via the
  target's extensionless stem -- restricted to `.py` targets because a
  stem match against a non-Python (data/doc) target reintroduces the
  same false-pass failure mode (an unrelated quoted English word
  colliding with a data file's stem).
- **Test-discovery IMPLICIT reference**: a file `frob.excludes.
  is_test_file` recognizes (`tests/**`, `test_*.py`, `*_test.py`, ...)
  is exempt from REF001/REF002 outright -- it is referenced by the test
  RUNNER via filesystem/naming convention, which no textual scan can see.
- **Declared** (`frob:used-by <consumer>`): a file names its own consumer
  explicitly, for references the auto-scan structurally cannot see (a
  path built at runtime, a glob loaded by a directory base). Every
  declaration is VERIFIED, not trusted: the named consumer must be a
  tracked file AND must itself reach the declaring file (same
  syntactic-position check, in reverse) -- a declaration naming a
  nonexistent or non-reaching consumer is REF003, not a silent pass. This
  is the anti-lie half: a `frob:used-by` cannot manufacture a reference
  that isn't real.

**Round-2 correction (reviewer-rejected the first landing, T-0396 Done
report):** the first working version's auto-scan produced an 86%
false-positive rate on this repo's own tree (326 of 379 REF001 findings
were detector gaps, not real orphans) -- two systemic causes, both fixed:
(1) a `from X import a, b, c` only captured the module PREFIX, never the
imported names, so any module reached ONLY through a multi-name import
was a permanent false orphan; (2) pytest-discovered test files (52% of
the false findings) are reached by filesystem convention, which no
textual auto-scan can see, and were flagged forever without the implicit
test-discovery exemption above. A post-fix full manual review of every
remaining REF001 finding on this repo found the detector's false-positive
rate at effectively zero (see T-0396's Done report for the finding-by-
finding verification and the exact before/after counts).

Tiers, over the deduped set of inbound-referencing files (auto plus
verified-declared, unioned): **0** -> REF001 (orphan), **1** -> REF002
(single fragile anchor), **2+** -> pass. All three rules are WARN -- this
never fails `frob check`'s exit code, but every REF001/REF002 must
eventually be waived-with-reason (`frob:waive REF001 reason="..."`) or
fixed, same advisory-but-tracked posture as PERF/FUZZ.

`[[refs.entrypoint]]` in `frob.toml` exempts genuinely externally-facing
files (README.md, LICENSE, pyproject.toml, the CLI `__main__.py`, ...)
from REF001/REF002 -- each entry is `{ path = "...", reason = "..." }`; a
malformed entry (missing `path`/`reason`) is skipped and logged, never
treated as a blanket mute.

`used-by` is a reserved marker verb in `frob.graph.dsl`
(`_RESERVED_MARKER_VERBS`): recognized and silently skipped by the graph's
generic directive parser (never routed through `EdgeKind`, never an
"unknown verb" `MalformedDirective`) because `_refs.py` owns and verifies
it directly via its own line-oriented scan -- a `frob:used-by` target is a
whole FILE, not a symbol, and every non-source tracked type
(yaml/md/toml/json/...) must be able to carry it too, most of which
`frob.lang` never parses at all.

### DOC004 unbound stale doc code blocks T-0436

`frob.gates._docblocks` -- `doc004_gate` (gate name `docblocks`, default-on,
mixed severity per finding). Motivating case: a fenced code block in a
`.md` doc (a python `from X import Y` example, a rust `use crate::path`
snippet) is the highest-drift-risk prose in a repo -- nothing binds it to
the code it demonstrates, so a rename/removal silently makes the doc lie.
No existing gate catches this: REF001-003 reason about whole-FILE
reachability, never a fenced block's own text; DOC001/DOC002 reason about
doc-to-doc/doc-to-symbol link structure, never code embedded in prose.

Deliberately SIMPLE, CONSERVATIVE, and PROJECT-GENERIC (the REF001
false-positive lesson applies here too: a noisy gate gets blanket-waived):

1. **Namespace derivation (never the directory name, never a hardcoded
   per-tool list)**: python from `pyproject.toml`'s `[project].name` plus
   every top-level package under `src/`; rust from the root `Cargo.toml`'s
   `[package].name` PLUS every `[workspace].members` glob's resolved
   subcrate (each subcrate is its own namespace -- a repo packaged as
   `logandapp_backend` is keyed on that name, never its directory); ts/js
   from `package.json`'s `name` plus `workspaces` members. Computed once
   per gate run.
2. **Extraction**: python `from X import ...`; rust `use X::...;`; ts/js
   `import ... from "X"` / `require("X")`. A token whose root namespace
   segment is not one of the project's own is skipped outright -- external
   libraries, generic shell, pseudo-code never flagged.
3. **Two tiers** for a token that DOES reference the project's own
   surface: **stale** (error) -- the module/crate/symbol does not resolve
   (python: checked against the real `GraphSnapshot` symbols, including a
   deliberately loose re-export check so a package `__init__.py` that only
   imports-and-re-exports a submodule's symbol via `__all__` is not a
   false positive; rust: checked by scanning the resolved crate's tracked
   `.rs` files for a matching `pub` item declaration) -- or **unbound**
   (warn) -- it resolves, but the block carries no `frob:doc`/
   `frob:describes`/`frob:tests` directive within itself or its three
   immediately-preceding doc lines, so future drift on it would go
   undetected. TS/JS is UNBOUND-only by design (no reliable static
   resolver for its export shapes here -- see the module docstring).
4. **`frob:waive DOC004 reason="..."` is prominently honored** directly
   out of the block's own nearby text (an HTML comment above the fence, or
   a comment line inside it) -- NOT routed through `frob.graph`'s WAIVE
   edge machinery, because `.md` files never go through
   `frob.graph.dsl.parse_directives` (only the narrower `markdown_anchors`
   describes-only scan), so a waiver written in doc prose has no graph
   edge to bind to. This is the deliberate escape hatch for a genuinely
   external or illustrative block the heuristic cannot confidently
   classify.

**Scope cut (disclosed, not silent)**: console/bash command-drift checking
(`frob <subcommand>` against a live registry) is NOT implemented in this
landing -- the ticket's own refinement demanded a CONFIGURABLE command
source (a `frob.toml`-declared entry point, generic per project, frob
being only one instance among many) rather than a hardcoded argparse-of-
frob special case, and building that generically was judged out of scope
for a first, conservative pass. Filed as a follow-up ticket (see T-0436's
Done report in `tickets.md` for the id).

**Dogfooding result (T-0436 Done report has the full finding-by-finding
detail)**: run on this repo's own tracked docs, DOC004 found 5 real
blocks -- 2 genuinely stale (`frob.edit._impl`, `frob.app.stub_runner`:
illustrative example modules referencing a removed/never-real command
surface) and 1 hypothetical-future worked example
(`export_terraform_sg`), each dispositioned with a reasoned
`frob:waive DOC004 reason="..."`; 1 initial false positive (a package
`__init__.py` re-export, `frob.strata`) was a real detector bug, fixed
before landing (see `_module_reexports`); 1 real UNBOUND advisory
(`docs/modules/logging.md`'s usage example, anchored later in the same
doc's "Public API" section rather than immediately above/inside the
block) was waived with a reason explaining why. Zero blanket waivers --
every waiver names its own specific reason.

### WALK001 unpruned traversal T-0471

`frob.gates._walk_lint` -- `walk_lint_gate` (gate name `walk_lint`,
default-on, WARN severity). Motivating case: T-0453's `_repo_files` did
`root.rglob("*")` -- walking the ENTIRE tree including `.git`, `.venv`,
`__pycache__`, and ~129 stale worktrees under `.claude/worktrees/` --
making `frob ticket doable` take minutes. `frob.excludes` already carried
the shared prune machinery (`_should_prune_dir`/`is_always_pruned_dir`, the
built-in skip set + `frob.toml` globs, established by T-0335 for `os.walk`
sites), but nothing stopped a raw traversal call from bypassing it. This
gate turns that mistake class into a static check: no NEW unpruned
traversal can land silently.

`frob.excludes` grew two shared entry points every walking caller should
route through instead (T-0471): `walk_pruned(root)` (an `os.walk`
generator that prunes `dirnames` in place via `_should_prune_dir` BEFORE
descending) and `iter_files(root, *, suffix=None)` (prefers a `git
ls-files` fast path -- tracked files only, no traversal at all -- when
`root` looks like a git work tree, falling back to `walk_pruned`
otherwise).

Detection is AST-based (Python's `ast` module, matching `_pii_structural`'s
precedent -- a regex/lexical scan both over- and under-fires on multi-line
calls and string mentions that merely name the pattern), scanning every
git-tracked `src/frob/**/*.py` file for:

- `Path.rglob(...)` -- always unbounded recursive regardless of pattern.
- `Path.glob(...)`/`Path.iglob(...)` -- only when the pattern argument
  contains `"**"` (a non-literal/dynamic pattern is treated as
  potentially recursive, deny-by-default).
- `os.walk(...)` -- dotted or bare-imported (`from os import walk`) form.
- `glob.glob(...)`/`glob.iglob(...)` with a `"**"` pattern -- dotted or
  bare-imported form.

Self-excludes `frob/gates/_walk_lint.py` (its own detection logic) and
`frob/excludes.py` (the shared helpers' own implementation, which contains
the one legitimate raw `os.walk` call this whole gate exists to keep
singular). Waivable per-line (`frob:waive WALK001 reason="..."`) for a
genuinely small, bounded-scope walk (e.g. `design_dir.rglob("*.strata")`
over a directory that will never be large enough to matter) -- the message
always names the remedy: route through `frob.excludes.iter_files` /
`frob.excludes.walk_pruned`.

```python
# frob/gates/__init__.py
def run_gates(cfg: GateConfig) -> Result[GateReport, GateError]
    # Orchestrates all gates (parallel where independent) over one
    # GraphSnapshot + TicketQueue + diff; single entry for check_runner.

def drift_gate(snapshot: GraphSnapshot, lock: LockFile) -> tuple[Violation, ...]
def coverage_gate(snapshot: GraphSnapshot, queue: TicketQueue,
                  diff: Diff, tests: CollectedTests) -> tuple[Violation, ...]
def scope_gate(diff: Diff, ticket: Ticket, snapshot: GraphSnapshot, *,
               root: Path | None = None,
               queue: TicketQueue | None = None) -> tuple[Violation, ...]
    # SCOPE001. When root/queue are given (run_gates always passes them),
    # a file failing this ticket's own scope is re-checked hunk by hunk via
    # git blame: a hunk is exempt only if every line is already committed
    # (never a dirty/uncommitted line) and every covering commit's subject
    # names another ticket whose own declared scope covers the file (T-0108
    # -- fixes false SCOPE001 on files an earlier ticket already committed
    # on the same branch). Callers omitting root/queue keep the old,
    # unconditional check.
def prework_gate(ticket: Ticket, snapshot: GraphSnapshot) -> tuple[Violation, ...]
def invariant_gate(invariants: tuple[Invariant, ...], snapshot: GraphSnapshot,
                   tests: CollectedTests) -> tuple[Violation, ...]

def test_gate(snapshot: GraphSnapshot, systems: tuple[SystemSpec, ...],
              coverage: Option[CoverageData], tests: CollectedTests,
              cfg: TestPolicy) -> tuple[Violation, ...]
    # TEST001..TEST006. Interfaces are derived from the snapshot: every
    # package whose public symbols are imported by another package is an
    # interface and owes integration tests. Coverage is consumed as
    # recorded evidence, never produced here.

def stamp_coverage(root: Path) -> Result[Unit, GateError]
    # Called by `make coverage` after pytest-cov: records coverage.xml's
    # sha plus current per-file content hashes into .frob/coverage-stamp.
    # TEST006 compares this stamp against the live snapshot.

def load_coverage(root: Path) -> Result[CoverageData, CoverageError]
    # Parses coverage.xml (branch mode) and maps line hits onto symbol
    # spans from the snapshot -> per-symbol/module percentages.

def active_ticket(root: Path, explicit: str | None) -> Option[str]
    # --ticket flag wins; else branch name matching ^(T-\d{4})- ; else Nothing.
    # Scope/pre-work gates run only when a ticket context exists.

def record_prework(root: Path, ticket_id: str,
                   sweep: PreworkSweep) -> Result[Unit, GateError]
    # `frob ticket start` runs dup+xref over the ticket scope and stores the
    # sweep digest in the ticket body; PRE001 checks its presence.

# Diff/working_diff live in frob/gitio.py (the ONE git seam, shared with
# frob.testing -- see docs/modules/testing.md); base default "main", configurable
# [tool.frob] check_base. CollectedTests and its pytest-collection cache
# live in frob.testing and are imported from there.

# frob/policy/__init__.py
def load_policy(root: Path) -> Result[tuple[PolicyRule, ...], PolicyError]
def policy_gate(rules: tuple[PolicyRule, ...], snapshot: GraphSnapshot,
                diff: Diff) -> tuple[Violation, ...]

# frob/gates/invariants.py
def load_invariants(root: Path) -> Result[tuple[Invariant, ...], InvariantError]
```

## Invariants

<!-- frob:describes src/frob/gates/invariants.py::_Criticality -->
<!-- frob:describes src/frob/gates/invariants.py::Invariant -->
<!-- frob:describes src/frob/gates/invariants.py::InvariantError -->

- `Criticality` -- how severe a broken invariant would be (`high` |
  `medium`); feeds severity weighting in INV001/INV002 reporting.
- `Invariant` -- one tracked invariant: id, statement, criticality, and
  its evidence list, parsed from `invariants/INV-###.md`.
- `InvariantError` -- failure values `load_invariants` can return
  (malformed frontmatter, duplicate id).

"Proving things that matter": an invariant is a tracked statement whose
truth must have standing evidence. Files in `invariants/INV-###.md`:

```markdown
---
id: INV-007
statement: Lock writes are atomic; a crashed frob never truncates frob.lock
criticality: high             # high|medium
evidence:
  - tests/test_lock.py::test_write_atomic_under_kill   # pytest node id
  - POL-no-direct-lock-write                            # or a policy rule id
---
Rationale and threat model prose here.
```

INV001/INV002 close the loop: every invariant is anchored in code
(`frob:invariant INV-007` at the enforcing site) and backed by evidence
that `frob check` verifies still exists (test collected, rule loaded).
Security work becomes monotonic: each audit finding lands as an invariant
plus a policy rule or property test, never a one-off fix.

## Policy rules (`frob.toml`, `[policy]`)

<!-- frob:describes src/frob/policy/_models.py::PolicyKind -->
<!-- frob:describes src/frob/policy/_models.py::PolicyRule -->

- `PolicyKind` -- the three rule kinds `frob.toml`'s `[policy]` table
  supports at alpha: `forbidden-import`, `pattern`, `norm`.
- `PolicyRule` -- one `[[policy.<kind>]]` entry; fields not used by its
  `kind` are left at their default.

```toml
[[policy.forbidden-import]]
id = "POL-no-requests-in-core"
module = "requests"
within = "src/frob/graph/**"
reason = "graph must stay offline-pure"

[[policy.pattern]]
id = "POL-no-subprocess-shell"
language = "python"
query = "(call ...)"          # tree-sitter query, file in policy/queries/
severity = "error"

[[policy.norm]]
id = "POL-max-diff-lines"
max_diff_lines = 400          # per active ticket; restraint merges
```

Three rule kinds at alpha: `forbidden-import`, `pattern` (tree-sitter query
over `frob.lang` trees), and `norm` (diff-shape rules). Taint analysis is
explicitly out of scope for 0.1.0.

## Test obligations (`frob.toml`, `[testing]` and `[[system]]`)

```toml
[testing]
min_unit_cases = 3            # TEST002: unit edges per public symbol
min_integration = 1           # TEST003: integration edges per interface
unit_branch_cov = 90          # TEST005: per-symbol branch coverage floor
module_line_cov = 85          # TEST005: per-module line coverage floor
system_line_cov = 80          # TEST005: per-system line coverage floor

[[system]]
id = "cli-check"              # target of frob:tests <id> kind="e2e"
entrypoint = "frob check"     # documentation; e2e tests drive it via subprocess
min_e2e = 5                   # TEST004
paths = ["src/frob/check/**", "src/frob/gates/**"]   # system_line_cov scope
```

Binding is explicit: a test declares what it tests via `frob:tests`
directives (see docs/modules/graph.md); the gate verifies the declared node ids are
actually collected by pytest, so a deleted test cannot keep satisfying an
obligation. Coverage is recorded evidence: `make coverage` runs pytest-cov
then `stamp_coverage`; `frob check` only reads the stamp and coverage.xml.
A stale or missing stamp is itself a violation (TEST006) -- the gate never
silently passes because tests were not run.

## Delta baseline (agent workflow, T-0095/T-0107)

`frob check` reports every kept violation on every run -- most of them
pre-existing legacy debt (ticketed, not new), not signal for the agent
driving one ticket to green. `stamp_baseline` records the current
violation set's fingerprints (rule + file + message digest, via
`violation_fingerprint`) plus a per-file content hash to `.frob/baseline`.
`delta_violations` filters a later violation set down to fingerprints
absent from that stamp; `is_baseline_stale` detects when any hashed file
has changed since the stamp, the same staleness shape `stamp_coverage`
uses for `.frob/coverage-stamp`.

Wired at the CLI as `frob check --stamp-baseline` (record and exit) and
`frob check --delta` (gates stage reports only new violations; see
docs/commands/check.md). A missing or stale baseline degrades `--delta` to
the full, unfiltered set with a warning -- this is an agent-facing filter
only, opt-in, never a silent narrowing of the human-facing report.

## Data models

<!-- frob:describes src/frob/gates/_models.py::Severity -->
<!-- frob:describes src/frob/gates/_models.py::WaiverRef -->
<!-- frob:describes src/frob/gates/_models.py::Violation -->
<!-- frob:describes src/frob/gates/_models.py::GateStats -->
<!-- frob:describes src/frob/gates/_models.py::GateReport -->
<!-- frob:describes src/frob/gates/_models.py::GateConfig -->
<!-- frob:describes src/frob/gates/_models.py::PreworkSweep -->
<!-- frob:describes src/frob/gates/_models.py::SystemSpec -->
<!-- frob:describes src/frob/gates/_models.py::TestPolicy -->
<!-- frob:describes src/frob/gates/_models.py::CoverageData -->

- `Severity` -- a violation's exit-code weight: `error` fails
  `frob check`, `warn` does not.
- `WaiverRef` -- the `frob:waive` edge that suppressed a violation, kept
  on the `Violation` so waivers stay visible debt rather than silence.
- `Violation` -- one gate finding: rule id, severity, site, and a message
  that always embeds its own remedy command.
- `GateStats` -- per-gate counters (violation counts, timing, skipped
  gates) attached to every `GateReport`.
- `GateReport` -- the merged result of `run_gates`: kept violations,
  waived violations, and stats.
- `GateConfig` -- everything `run_gates` needs to load state and select
  which gates run (root, base ref, ticket, gate subset).
- `PreworkSweep` -- a recorded dup+xref sweep over a ticket's scope,
  stamped at `frob ticket start` time; PRE001's evidence.
- `SystemSpec` -- one `[[system]]` entry: an e2e-tested surface, its
  entrypoint, and its coverage scope for TEST004/TEST005.
- `TestPolicy` -- the `[testing]` table: all test-obligation floors
  (unit case counts, coverage percentages), each overridable.
- `CoverageData` -- parsed `coverage.xml` mapped onto the snapshot:
  per-symbol branch and per-module line percentages.

```python
class Violation(BaseModel):
    rule: str                   # "DRIFT001", "POL-..."
    severity: Severity          # ERROR | WARN
    file: str
    line: int
    message: str                # human sentence incl. the fix command
    waived: WaiverRef | None    # populated when a frob:waive matched

class GateReport(BaseModel):
    violations: tuple[Violation, ...]
    waived: tuple[Violation, ...]
    stats: GateStats            # counts per gate, timing per gate

class GateConfig(BaseModel):
    root: Path
    base: str = "main"
    ticket: str | None = None   # explicit --ticket
    gates: frozenset[str]       # subset selection for frob check --only

class Diff(BaseModel):
    base: str
    hunks: tuple[Hunk, ...]     # file, span, touched symrefs (resolved
                                # against the snapshot by frob.gates)

class PreworkSweep(BaseModel):
    date: date
    dup_findings: int
    xref_hits: tuple[str, ...]
    digest: str                 # over scope file hashes at sweep time

class Invariant(BaseModel):
    id: str                     # ^INV-\d{3}$
    statement: str
    criticality: Criticality
    evidence: tuple[str, ...]

class CollectedTests(BaseModel):
    node_ids: frozenset[str]    # from pytest --collect-only -q, cached

class SystemSpec(BaseModel):
    id: str
    entrypoint: str
    min_e2e: int
    paths: tuple[str, ...]

class TestPolicy(BaseModel):    # [testing] table, all floors overridable
    min_unit_cases: int = 3
    min_integration: int = 1
    unit_branch_cov: int = 90
    module_line_cov: int = 85
    system_line_cov: int = 80

class CoverageData(BaseModel):
    source_sha: str             # coverage.xml sha recorded by the stamp
    symbol_branch: Mapping[str, float]   # symref -> percent
    module_line: Mapping[str, float]     # package path -> percent
```

## Error types

<!-- frob:describes src/frob/gates/_models.py::GateError -->
<!-- frob:describes src/frob/gates/_models.py::CoverageError -->
<!-- frob:describes src/frob/policy/_models.py::PolicyError -->

- `GateError` -- failure values `run_gates` and its loading steps
  (graph build, ticket queue, lock, git diff) can return.
- `CoverageError` -- failure values `load_coverage`/`stamp_coverage` can
  return (missing `coverage.xml`, malformed XML).
- `PolicyError` -- failure values `frob.policy`'s rule loading and
  matching paths can return (malformed rule, non-compiling tree-sitter
  query).

```python
class GateError(ErrorSet):
    GraphUnavailable = "Graph build failed; gates cannot run"
    GitFailed        = "git diff/merge-base failed"
    NoTicketContext  = "Scope gate requested but no active ticket resolved"

class PolicyError(ErrorSet):
    MalformedRule = "Policy rule failed schema validation"
    BadQuery      = "tree-sitter query does not compile"

class InvariantError(ErrorSet):
    Malformed   = "Invariant file failed schema validation"
    DuplicateId = "Two invariant files share an id"

class CoverageError(ErrorSet):
    Missing  = "No coverage.xml/stamp found; run make coverage"
    Malformed = "coverage.xml could not be parsed"
```

## Design decisions

- **Gates are pure functions over loaded state.** Load once (snapshot,
  queue, lock, diff, tests), run gates in parallel. Most gates run on a
  `ThreadPoolExecutor`; the CPU-bound giants (archgate, sys, clones, perf,
  pii_structural, secrets -- docs/audits/perf.md H3) run on a separate
  `ProcessPoolExecutor` instead, so they get real parallelism rather than
  GIL-serializing on the shared thread pool (T-0415). Results from both
  pools are merged back in a fixed gate-name order, so output stays
  byte-identical regardless of which pool finishes a given job first. No
  gate does IO; `run_gates` owns all loading.
- **Ticket context is optional; scope/pre-work gates degrade to skipped,
  not failed**, when no ticket resolves -- humans doing exploratory work on
  main are not fighting the tool. COV002 still catches unticketed diffs at
  check time, so nothing escapes; it just fails later rather than louder.
- **Every violation message embeds its remedy** ("run: frob ack <ref>",
  "run: frob ticket new ..."). Agents act on messages; a message without a
  next command is a dead end.
- **Waivers are per-site, reasoned, and reported.** Global rule disabling
  requires editing `frob.toml` in a reviewed commit.
- **Bare TODO/FIXME comments are violations** (TODO001). The habit the
  system replaces must not survive alongside it.
- **COV002 has a same-diff grace window for a ticket that just closed**
  (T-0214). Without it, closing the covering ticket while its edit is still
  uncommitted is a catch-22: the ticket moves out of `_OPEN_STATES`
  immediately, so every symbol it was covering becomes a hard "changed with
  no open ticket" error before the user has a chance to commit. The
  narrowest honest fix: a `DONE` ticket's `frob:ticket` edge still counts
  if `tickets.md` itself is part of the current diff -- i.e. the close and
  the covered edit are landing together as one change, not two. Once the
  close lands as its own commit and drops out of the diff, the grace window
  closes and a genuinely later, unrelated touch to the same symbol is
  caught exactly as before.
- **COV005 catches a directive silently rebound to the WRONG symbol, not
  just an unattached one** (T-0297). COV001 only proves a directive resolves
  to SOME symbol; it says nothing about whether that symbol is still the
  one the directive's author meant. Extracting a private helper directly
  above an existing public `def` (a common refactor shape) silently moves
  every trailing `frob:` directive that used to describe the public `def`
  onto the new private helper, because the DSL's `following`/`enclosing`
  binding always attaches to the NEAREST symbol below the comment, not the
  one the author intended -- and every other gate stays green afterward,
  since the directive still resolves. This bit twice in this repo's own
  history (`scan_tree`, `renumber_one`) and was only caught by manual
  review. COV005 is git-diff-aware and scoped to files the current diff
  touches: for each `(kind, target)` pair a directive carries in the
  current tree, it compares against the SAME `(kind, target)` pair's
  binding at `diff.base` (via `git show <base>:<file>`, reparsed) -- if that
  pair bound a PUBLIC symbol at `diff.base` and now binds a PRIVATE one, it
  is a CANDIDATE rebind, flagged as an ERROR only if the new private
  symbol's own span also overlaps one of the diff's hunks in that file --
  i.e. the private symbol carrying the directive is itself part of what
  this diff just changed, the "extracted helper directly above an existing
  def" shape the ticket describes. A `(kind, target)` pair alone is NOT a
  unique directive identity: this repo's own convention reuses one
  `frob:doc <page>#<anchor>` target across every public function a doc
  page covers, so comparing old vs new bindings FILE-WIDE (without the
  hunk-overlap restriction) flagged roughly 50 pre-existing, untouched
  private helpers that merely happen to share an anchor with some
  unrelated public function elsewhere in the same file -- the
  hunk-overlap guard is what keeps COV005 from being a repo-wide,
  diff-oblivious full scan. Files with no
  resolvable blob at `diff.base` (new files) are skipped -- there is no
  "before" to compare a new file's directives against, and COV001 already
  covers a new symbol's own missing-doc obligation. The other two
  candidate detections from the ticket -- (b) `frob:tests` evidence whose
  named test does not actually reach the bound symbol (call-graph
  reachability, ties into T-0288/T-0290's shared substrate) and (c) a
  `frob:doc #public-api` anchor specifically on a private helper -- are
  deliberately out of scope for this pass; each needs its own ticket rather
  than folding into COV005's git-diff comparison.
- **pytest collection is the evidence oracle** for test node ids, cached in
  `.frob/` keyed on test-file hashes; running tests is `make test`'s job,
  existence is the gate's job.
- **Test obligations verify existence, quantity, and measured reach -- not
  quality.** Counts and coverage floors are gameable proxies (assert-free
  tests pass them); the honest quality oracle is mutation testing, which is
  tracked in the ticket ledger (mutation testing shipped as `frob mutate`). A `pattern` policy rule
  banning assert-free test functions ships as a first defense.
- **Interfaces are derived, not declared.** Any package whose public
  symbols another package imports owes integration tests; deriving this
  from the graph means a new boundary cannot be forgotten. Pair-level
  (consumer x provider) strictness is deferred; per-provider at alpha.
- **Coverage thresholds are floors in config, not goals in prose.**
  Raising a floor is a reviewed `frob.toml` commit; lowering one is too,
  and shows up in diff review.

## Dependencies

- `frob.graph` (snapshot, lock, drift), `frob.tickets` (queue),
  `frob.policy`, `frob.lang` (pattern queries).
- git via subprocess (diff, merge-base, branch name).
- `pydantic`, `typani`.

## Integration points

- `frob.check`: `run_check` gains a gates stage; `frob check --only gates`,
  `--ticket T-0042`, `--base <ref>` flags; exit code folds into the
  existing errors-first report and `frob parse` output format.
- `frob ticket start` calls `record_prework` (dup + xref over scope).
- Pre-commit hook and CI both run `frob check`; agents run it after every
  ticket before writing a done-report.

## Phase 4 implementation notes (deviations from the design above)

The design above is otherwise as-implemented. The following are the
concrete choices made where the design was ambiguous or where a
dependency's real API did not match the sketch:

- **`WAIVE001` is derived from `GraphSnapshot.malformed`, not a separate
  scan.** `frob.graph.dsl.parse_directives` already refuses to turn a
  `frob:waive` directive lacking `reason="..."` into an `Edge` -- it
  becomes a `MalformedDirective` instead. `gates._waive001_violations`
  simply surfaces any malformed directive whose reason text mentions
  `frob:waive`. Every `Edge` with `kind == WAIVE` that reaches a gate is
  therefore guaranteed to already carry a `reason` attr.
- **`prework_gate` takes an extra `sweep: Option[PreworkSweep] = Nothing()`
  argument** beyond the doc's `(ticket, snapshot)` signature. The sweep is
  loaded state (see below) and gates must not do IO, so `run_gates` loads
  it via `gates._prework.load_prework` and passes it in.
- **`invariant_gate` takes an extra `policy_rule_ids: frozenset[str] =
  frozenset()` argument** beyond `(invariants, snapshot, tests)`, so
  INV001 can treat a loaded policy rule id as valid evidence (the doc's
  own example evidence list includes `POL-no-direct-lock-write`); without
  it the pure function would have no way to see policy state.
- **`record_prework` storage**: `frob.tickets` exposes only
  `record_failure` (a fixed "## Failure log" section), not a generic
  body-section appender, and growing `frob.tickets`'s public surface is
  out of scope for this phase. The sweep is instead stored as JSON at
  `.frob/prework/<ticket_id>.json` (`gates/_prework.py`), read back by
  `load_prework`. `PRE001` compares `sweep.digest` against a fresh
  `_scope_digest(ticket, snapshot)` (sha256 over the ticket's scope-glob-
  matched `snapshot.file_hashes` entries).
- **Hunk-to-symref resolution is reimplemented in `gates`**, not imported
  from `frob.testing._select`: `select_tests` does the same span-overlap
  match inline as part of a larger algorithm and never exposes it as a
  standalone function. `gates._touched_symrefs`/`_touched_files` are a
  documented duplicate of that overlap primitive, same posture as the
  extension-table duplicates already accepted across
  `frob.graph`/`frob.testing`/`frob.policy`.
- **TEST003 interface derivation, alpha semantics**: the graph has no
  cross-file import edges (only `frob:` directive edges and doc anchors),
  so real "package A's public symbols imported by package B" derivation
  is not available. Alpha instead treats every `src/<pkg>/<subpkg>`
  directory containing at least one public, non-test symbol as an
  interface owing `min_integration` integration `frob:tests` edges -- the
  simple, honest over-approximation the design's own "Interfaces are
  derived, not declared" note anticipates. Pair-level (consumer x
  provider) strictness is deferred.
- **TEST001/TEST002/TEST005 skip symbols in test files themselves**
  (`gates._is_test_file`, a documented duplicate of
  `frob.testing._select._is_test_file`'s heuristic) -- a public `test_*`
  function does not owe itself a unit test.
- **TEST005 system floor** is approximated as the mean of `module_line`
  percentages for files matching any of `[[system]].paths`, since
  `CoverageData` (per the doc's own model) has no separate per-system
  map; `load_coverage` only ever produces `symbol_branch`/`module_line`.
- **`frob.gates` does not re-export `PolicyRule`/`PolicyError`/
  `load_policy`/`policy_gate`.** `frob.policy` imports `Violation`/
  `Severity`/`WaiverRef` from `frob.gates._models`, so a module-level
  `from frob.policy import ...` in `frob.gates.__init__` would form an
  import cycle the first time either package is imported standalone.
  `run_gates` imports `load_policy`/`policy_gate` lazily inside its own
  body instead; callers needing policy types import them from
  `frob.policy` directly.
- **`policy_gate`'s `forbidden-import` and `pattern` rules read file
  content off disk via `Path(snapshot.root)`** plus
  `snapshot.file_hashes` (for glob-matched file listing), since the
  signature `policy_gate(rules, snapshot, diff)` carries no separate
  root parameter; `GraphSnapshot.root` already carries it.
- **`GateError` collapses every loading failure** (`frob.graph`,
  `frob.graph.lock`, `frob.tickets`, `frob.gates.invariants`,
  `frob.policy`) into one of `GraphUnavailable` / `QueueUnavailable` /
  `ConfigMalformed` / `GitFailed` / `WriteFailed`, rather than a full
  `GraphError | LockError | TicketError | InvariantError | PolicyError`
  union, to keep `run_gates`'s `Result[GateReport, GateError]` a single
  small enum callers can match on directly.
- **Severity defaults per rule** are fixed in code (`ERROR` for
  DRIFT/COV002-004/SCOPE001/PRE001/INV001-002/TEST001/TEST004/WAIVE001/
  policy rules with no `severity` override; `WARN` for COV001, TODO001,
  TODO002, TEST002/003/005). Per-rule severity overrides in `frob.toml` were
  scoped out of this phase; `PolicyRule.severity` is the only
  user-configurable severity today (via `[[policy.*]].severity`).
