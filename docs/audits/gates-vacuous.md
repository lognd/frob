# Gate-by-gate vacuous-satisfaction sweep + lang parser trust-boundary pass

Status: 2026-07-23

Scope: T-0786, the two surfaces the 2026-07-23 blindspot audit
(`docs/audits/frob-blindspots-2026-07-23.md`) explicitly named as skipped --
(a) a full vacuous-satisfaction sweep of `gates/__init__.py` and the
`gates/_*.py` modules (can any gate go green on an empty diff, empty scope,
stale cache, or missing backing file, without doing its work?), and (b) the
`lang/**` tree-sitter ingestion of untrusted repo files (parser-level
DoS/trust-boundary). Round 2 (this revision) completes the catalog after
round 1 left ~45 rule ids unread; every rule id `known_gate_rule_ids()`
returns, plus every real, currently-firing `rule="..."` site this sweep
found MISSING from that frozenset, now has a recorded verdict below.

Repo state at audit: worktree merged to main tip `138d6319`, clean tree.

Method: for every rule id, read the dispatching gate function (or, for a
family sharing one dispatcher, the dispatcher once) and ask adversarially:
what diff/scope/ticket/filesystem/native-toolchain state makes this rule
fire ZERO violations without having actually verified anything? A verdict
of "non-vacuous" means the empty-input/missing-file/native-unavailable
paths were read and found to fail loud, or the skip is a disclosed,
intentional opt-in posture (not a defect) -- never an assumption.

---

## HIGH

### H1. SCOPE001 vacuously passes when the active ticket's `scope` is empty

- Evidence: `src/frob/gates/__init__.py:5006` (`scope_gate`):
  ```
  if not ticket.scope:
      _log.debug(...)
      return ()
  ```
  `Ticket.scope`/`TicketSpec.scope` (`src/frob/tickets/_models.py`) both
  default to `()`, and neither carries a `min_length` or any other
  non-empty constraint. `frob ticket new` with no `--scope` (or a
  `frob ticket scope` edit that clears it) produces a ticket SCOPE001 can
  never flag, no matter what the diff touches.
- Net effect: the one gate whose entire purpose is "keep a worked ticket's
  diff inside its declared boundary" gives an UNDECLARED-scope ticket
  (arguably the riskiest case -- no stated intent at all) strictly LESS
  enforcement than a normally-scoped one, not more.
- Why no other gate catches it: `TicketSpec`/`Ticket` have no scope
  cardinality validator; `frob ticket start`'s pre-work sweep does not
  require a non-empty scope either.
- Filed: fix ticket "SCOPE001 vacuously passes when ticket.scope is empty
  (no non-empty-scope precondition)"; paired gate/test ticket "Add
  regression gate/test: empty-scope ticket must not silently pass SCOPE001".

### H2. Partial (salvaged) tree-sitter parses silently drop symbols -- `partial_parse_files()` has zero consumers

- Evidence: `src/frob/lang/__init__.py` (`_parse`, `_warn_if_partial_tree`,
  ~lines 280-370) already distinguishes a HARD parse failure (unusable
  tree) from a PARTIAL/salvaged parse (`tree.root_node.has_error` but the
  grammar still recovered a usable structure). The hard-failure case is a
  real gate: `PARSE001` (`src/frob/gates/_parse_failures.py`, T-0558/T-0561)
  turns a recorded `snapshot.parse_failures` entry into a loud ERROR
  violation. The partial case is NOT wired anywhere: `_warn_if_partial_tree`
  only logs a WARNING and records the path into a module-level
  `_partial_parse_files` set, exposed publicly via `partial_parse_files()`.
  Repo-wide grep for `partial_parse_files` turns up exactly: the
  definition, its own docstring, and the `__all__` export -- no gate, no
  CLI dispatch, no test calls it.
- Net effect: PARSE001's own T-0558 module docstring names this exact
  failure mode ("tree-sitter produced a PARTIAL tree ... some top-level
  symbols may be silently dropped from the salvaged tree ... the same
  'log line existed but nothing consumed it' gap") as the still-open half
  of the T-0404 finding-2 fix -- a file with, e.g., a stray unmatched
  brace or an unterminated string partway through can silently drop every
  obligation (COV001, DRIFT, INV, TEST001-*) for everything tree-sitter's
  error recovery failed to salvage, with only a DEBUG/WARNING log line as
  evidence.
- Filed: fix ticket "Partial tree-sitter parse (salvaged, has_error)
  silently drops symbols -- partial_parse_files() has zero gate consumers";
  paired ticket "Add PARSE002 gate wiring partial_parse_files() into frob
  check + regression test".

### H3. `_KNOWN_GATE_RULES` omits 7 real, currently-firing rule ids

- Evidence: `known_gate_rule_ids()`/`_KNOWN_GATE_RULES`
  (`src/frob/gates/__init__.py:904`) returns 118 rule ids. Direct
  membership check plus a repo grep for every `rule="..."` literal that
  actually constructs a `Violation` finds at least 7 real, live rule ids
  MISSING from it: `PARSE001` (registered as an always-run process job in
  `_ALL_GATES`), `TICK005` (`__init__.py:7352`, dispatched from
  `tickets_gate`), `REG011` (`_registry_exhaustiveness.py:301/317`,
  dispatched from `registry_gate`), `PII011`/`PII012`
  (`_pii_structural.py:892/957`, dispatched from `pii_structural_gate`),
  `SYSWAIVE002` (`strata/_contention.py:437`), and `THREAT006`
  (`strata/_threat.py:1477`).
- Net effect: this frozenset is the single validity check every
  `frob:waive RULE reason="..."` is matched against (WAIVE002: "rule id
  can never match anything") AND the set the function's own docstring
  says strata `caught_by`/registry `handled_by` resolution treats as a
  recognized real rule id rather than an unresolved reference. Any
  `frob:waive PARSE001 reason="..."` (or the other 6) written anywhere in
  this tree today is silently flagged WAIVE002-ineffective despite
  targeting a perfectly real, currently-firing rule; a strata/registry
  claim naming any of these 7 ids as its catching control is treated as
  UNRESOLVED rather than credited, which can silently understate a
  threat-model or compliance disposition's real coverage.
- Why this recurred: this is the exact DEAD001-class omission T-0753
  already fixed once (its own comment: "This was a listing omission, not
  evidence DEAD001 was ever renamed or removed") -- but nothing prevents
  the SAME omission from recurring per new rule added since, and it has,
  at least 6 more times.
- Filed: fix ticket "_KNOWN_GATE_RULES omits 7 real, currently-firing rule
  ids (PARSE001/TICK005/REG011/PII011/PII012/SYSWAIVE002/THREAT006)";
  paired ticket "Add drift-lock test: every emitted rule= literal must be
  a _KNOWN_GATE_RULES member" (a permanent fix for the recurrence, not
  just the current 7).

---

## MEDIUM

### M1. `lang/**` tree-sitter ingestion has no file-size cap or parse timeout (untrusted-file trust boundary)

- Evidence: `_parse` (`src/frob/lang/__init__.py:316-370`) does
  `path.read_bytes()` unconditionally, then `parser.parse(source)`, with no
  `st_size` guard before the read and no wall-clock budget around the
  parse call. This is the exact surface the ticket's part (b) names: frob
  is a general-purpose static-analysis tool pointed at arbitrary repos
  (including untrusted/adversarial ones during an audit run), and
  tree-sitter's error-recovery, while generally robust, is not proven
  immune to pathological-input classes (deeply nested bracket/paren
  structures driving expensive recovery, or simply a multi-GB single
  file committed as a decoy). No structural guard exists at any layer
  above `_parse` either (`frob.graph`'s file walk calls `parse_file`
  directly).
- Why no gate catches it: there is no PERF/SEC rule modeling "the parser
  itself" as an attack surface -- `PERF001-007` model frob's own hot
  paths, not adversarial input to the parser.
- Filed: fix ticket "lang/** tree-sitter parse has no file-size cap or
  timeout -- untrusted-file DoS trust-boundary gap"; paired ticket "Add
  regression test/lint for lang/** parse size+timeout guard".

### M2. Registry/design-dir-backed gates cannot distinguish "never adopted" from "deleted" (COMPLIANCE005, REG*, DEC*, SYS*, DOC003, DOC001)

- Evidence: at least SIX independently-justified but structurally
  identical early-exits:
  - `registry_gate` (`src/frob/gates/_registry_exhaustiveness.py:812`):
    `if not base.is_dir(): ...` (REG001-011 make no claim at all).
  - `compliance_gate` (`src/frob/gates/__init__.py:7665`): `if not
    (base / "compliance.yaml").is_file(): ... return ()` -- its own
    docstring explicitly says this is "matching registry_gate's own
    missing-directory posture."
  - `decisions_gate`'s DEC001/DEC002 half (`src/frob/gates/__init__.py:7035`):
    `if not decisions_dir(root).exists(): return ()`.
  - `sys_gate` (`src/frob/gates/__init__.py:8104`): `if not (root /
    design_dir).is_dir(): ... return ()` -- silences SYS001-004 AND
    DOC003 (`_doc003` is dispatched from inside `sys_gate`, sharing the
    same guard) whenever the `.strata` design directory is absent.
  - `doclink_gate` (`src/frob/gates/__init__.py:8689`): `if not obligated:
    return ()` -- an empty `[gates.docs] include` glob match (misconfig,
    or every doc under it deleted in one diff) silences DOC001 entirely,
    the same shape one level removed (config-driven emptiness rather than
    a single missing directory).
- Net effect: each is individually defensible ("a repo that never adopted
  the registry/design-dir/docs-glob makes no claim"), but none
  distinguishes "never adopted" from "adopted, then the backing
  file/dir/glob-match vanished" (accidentally, or by a malicious diff).
  Once a repo HAS populated e.g. `docs/design/registry/compliance.yaml`
  with real disposition claims, or a `.strata` design tree with real
  SYS00x-checked boundaries, deleting it is structurally indistinguishable
  to the corresponding gate from "this repo never adopted it" -- both
  silently clear every finding the artifact existing would have produced.
  No REF/DOC-family gate treats the artifact's disappearance as its own
  finding once adopted.
- Severity note: COMPLIANCE005 and SYS001-004 are the highest-stakes
  instances (regulatory-control disposition exhaustiveness and design
  boundary/secret conformance, respectively); REG*/DEC*/DOC001 share the
  same shape at lower stakes.
- Filed (round 1): fix ticket "Registry-backed gates (COMPLIANCE005/REG*/
  DEC*) cannot distinguish never-adopted from deleted-registry"; paired
  ticket "Add regression test for COMPLIANCE005 adopted-then-deleted-
  registry detection". SYS*/DOC003/DOC001's instances of the same class
  are recorded here as additional evidence for that ticket's fix
  direction (a general "adopted, then vanished" detector), not filed as
  separate tickets -- one mechanism should cover all six once built.

### M3. `dup_gate` silently no-ops (log-only) when `frob-core` native is unavailable, despite `[dup].enforce=true`

- Evidence: `dup_gate` (`src/frob/gates/__init__.py:8175`) is opt-in via
  `[dup].enforce=true` (disclosed, fine) -- but when enforce IS on and
  `core_available()` is False:
  ```
  _log.warning("dup_gate: frob-core not installed; DUP rules skipped")
  return ()
  ```
  a bare log warning, not a `Violation` -- `frob check`'s exit code and
  violation list are unchanged whether DUP001/002 genuinely found nothing
  or silently could not run at all.
- Net effect: this repo's own playbook (`docs/guides/agent-playbook.md`
  section 1) documents the missing-native failure mode as REAL and
  recurring ("Fresh worktrees do not inherit a sibling worktree's build
  -- strata_core/frob_core come up missing", T-0144) -- a repo that has
  opted into `[dup].enforce=true` and runs `frob check` from a worktree
  where `make core` has not run yet gets zero DUP001/002 enforcement,
  green gate-summary, log-only signal.
- Why no gate catches it: T-0552/TEST013 already fixed the identical
  shape for the coverage gate's own native-unavailable structural
  fallback ("make the structural-fallback credit ... LOUD instead of
  silent") -- DUP never got the equivalent treatment.
- Filed: fix ticket "dup_gate silently no-ops (log-only) when frob-core
  native is unavailable despite [dup].enforce=true"; paired ticket "Add
  regression test for dup_gate native-unavailable loud-violation
  behavior".

### M4. RENDER001/PII010/SEC-CVE-FINGERPRINT-001 each run a private silent-skip-on-unparseable file read outside PARSE001

- Evidence: three gates run their OWN per-file read+parse, independent of
  `frob.lang.parse_file`'s centrally-tracked pipeline (the one
  `snapshot.parse_failures`/PARSE001 actually covers), each silently
  skipping a file that fails, with only a DEBUG log line:
  - `render_lint_gate` (`_render_lint.py:220-224`):
    `except (OSError, UnicodeDecodeError, SyntaxError): skip` around its
    own `ast.parse`.
  - `pii_structural_gate` (`_pii_structural.py:1861-1865`): the identical
    shape around its own `ast.parse`, for PII010/SEC110.
  - `cve_fingerprint_scan_gate` (`_cve_fingerprint_scan.py:183-187`):
    `except (OSError, UnicodeDecodeError): skip` around its plain text
    read, for SEC-CVE-FINGERPRINT-001.
- Net effect: a Python file with a syntax error or bad encoding is
  invisible to RENDER001 (bare-print-bypassing-Renderer) and to
  PII010/SEC110 (structural PII/secret-shape detection) -- exactly the
  two families where "this file's content was never actually inspected"
  matters most from a security-review standpoint -- with zero surfaced
  signal, unlike the general PARSE001 mechanism T-0558 built specifically
  to make this class loud for `frob.lang`-routed gates.
- Filed: fix ticket "RENDER001/PII010/SEC-CVE-FINGERPRINT-001 each run a
  private silent-skip-on-unparseable file read outside PARSE001"; paired
  ticket "Add regression tests for RENDER001/PII010 loud-on-unparseable-
  file behavior".

---

## LOW / reviewed, no ticket filed (documented, accepted risk)

### L1. `secrets_gate`'s line-oriented matching misses a token split across a line-wrap

- Evidence: `src/frob/gates/_secrets.py:63-67`, the module's own docstring:
  "this scanner is line-oriented ... a token that has been line-wrapped
  ... will not match any pattern and will silently pass. Documented gap,
  not a silent omission." Same module also explicitly declines several
  entropy-heuristic secret classes (AWS/Azure keys, generic API-key
  patterns) as a deliberate anti-false-positive tradeoff (T-0151).
- Verdict: already fully disclosed, in-repo, with the reasoning recorded
  at the point of the gap -- not a new finding. No ticket filed.

### L2. `dead_symbol_gate` (DEAD001) is Python-only by design, already ticketed

- Evidence: `src/frob/gates/_dead_symbols.py:152`'s own docstring: the
  call graph's callee-privacy check hardcodes Python's leading-underscore
  convention; running DEAD001 against Rust/TypeScript/C measured a
  ~100% false-positive rate on this repo's own native sources, so the
  gate is deliberately scoped to `.py` only. The docstring records "See
  this ticket's Done report for the filed follow-up" -- a real ticket
  already exists for the underlying call-graph soundness gap (T-0422's
  Done report, `tickets-archive.md`).
- Verdict: real, currently-live gap (Rust/TS/C private dead code gets
  zero DEAD001 coverage, repo-wide, indefinitely) but already disclosed
  loudly in-code and already tracked by an existing ticket -- not
  re-filed here to avoid duplicating open work.

### L3. `ARCH101/102/103` lack their own `frob:enforces CHK-GATE-*` cross-link

- Evidence: `src/frob/gates/_arch.py:62-66`'s own comment: "ARCH101/102/103
  are NOT wired to a frob:enforces CHK-GATE-* directive here ...
  the coordinator adds CHK-GATE-ARCH101/102/103 rows plus the matching
  directives as a land obligation, same as T-0788's COMPLIANCE005
  precedent left it."
- Verdict: the rules themselves fire correctly (verified: `arch_gate`
  unconditionally calls `analyze_project` with no absence-guard) -- this
  is a registry cross-link completeness gap (REG008-adjacent), not a
  vacuous-satisfaction defect, and it is already disclosed as a pending
  land obligation. Not re-filed.

---

## Swept and confirmed NON-vacuous (read in full, no defect)

- `coverage_gate` (COV001-007, TODO001-003): `_load_diff`'s
  `diff_load_failed`/`diff_load_no_repo` split (T-0550/T-0719) already
  turns a genuinely-failed diff load into a loud `_diff_load_failed_violation`
  for COV002/TODO001 instead of silently clearing them on the empty
  placeholder diff.
- `parse_failure_gate` (PARSE001's own dispatch): the HARD-failure half
  this sweep cross-references for H2/H3 is itself correct and loud.
- `tickets_gate`'s TICK002 (`_tick002_draft_on_default`): only fires
  `on_default_branch(root)`, but `on_default_branch` fails CLOSED on
  every ambiguous case (no git repo, detached HEAD both resolve to
  `True`/"assume default") -- ambiguity produces MORE enforcement, not
  less.
- `fuzz_gate` (FUZZ001-003): silent when `[fuzz].enforce` is unset, a
  disclosed, deliberate "warn-first adoption posture" in the function's
  own docstring, not a hidden vacuousness vector.
- `dup_gate`'s enforce-off path (distinct from M3's native-unavailable
  path): disclosed opt-in, correctly silent, non-vacuous.
- `release_gate` (REL001): opt-in via `.frob-release.json` manifest
  presence (disclosed); `FROB_AGENT`-suppressed bump/changelog demand is
  T-0731's deliberate, documented land-ownership design (playbook section
  4b); open-debt (DEBT-family, via `_release_open_debt_violations`) and
  expired-deprecation (DEPR-family) checks still run unconditionally
  regardless of the opt-in state -- read in full, correctly hardened.
- `krb_trust_flows` / `_validate_store_waives` (`strata/_krb.py`,
  `strata/_infra.py`): both have comments flagging a "would silently
  skip" shape, but in both cases a sibling check elsewhere in the same
  elaboration pass already closes the gap -- read and confirmed.
- `registry_gate`'s REG006/REG007 malformed-entry handling: explicitly
  loud (`_registry_exhaustiveness.py:76`, an already-fixed historical
  gap, not current).
- `exclude_hazard_gate` (EXCL001): both early exits (`common_dir is
  None`, `not entries`) are structurally correct no-ops (nothing to
  check outside a git repo / with an empty exclude file), not
  vacuousness.
- `ref_gate` (REF001-003): the test-file exemption is a deliberately
  narrow, reviewer-hardened carve-out (T-0396 rounds 2-3) with its own
  regression tests, not a broad vacuousness hole.
- `perf_gate` (PERF001-007): routes every candidate file through the
  real `frob.lang.parse_file` (PARSE001-covered), and its own docstring
  states a parse failure "still gets a visible skip message" -- verified
  true by reading `_perf_gate_parse_files`.
- `protocol_summary_gate` (PROTO001-003): the non-Python callee-privacy
  gap is explicitly disclosed in its own T-0841 docstring update as a
  narrower, already-acknowledged residual gap, not a silent one.
- `debt_gate` (DEBT001-003) / `deprecated_gate` (DEPR001-004): both scan
  `snapshot.edges` unconditionally with no absence-guard of any kind.
- `doc004_gate`/`doc005_gate` (DOC004/005, `_docblocks.py`): both scan
  every tracked doc/README unconditionally, no absence-guard.
- `fmt_gate` (FMT001): diff-scoped by design (WARN-tier only, not
  ERROR) -- lower stakes than COV002/TODO001's ERROR-tier obligations, so
  not getting the same loud-diff-load-failure treatment those got is
  consistent with its own severity, not an oversight.
- WAIVE001-007: `_UNWAIVABLE_RULES` (`__init__.py:1203`) is a small,
  explicit frozenset (`TEST008, SEC003, TICK001, TICK002, EXCL001`);
  every other rule's waiver requires a non-blank `reason=` (WAIVE001) and
  is itself subject to WAIVE003 (over-broad package-prefix reach),
  WAIVE004 (stale/non-matching waiver hygiene), WAIVE006/WAIVE007
  (waiver bound to a closed/unresolvable ticket) -- no blanket-waiver
  vacuousness path found beyond the already-covered per-rule checks.

---

## Catalog coverage: every rule id, one verdict each

`known_gate_rule_ids()` returns 118 ids (verified via direct call this
pass). This sweep additionally found 7 real, firing rule ids the function
OMITS (H3) -- those 7 are included in the tally below since they are real,
live gate output this audit is responsible for covering, not because they
are catalog members.

| Family | Rule ids | Verdict |
|---|---|---|
| COV | 001-007 | non-vacuous (read in full, round 1) |
| PLACE | 001 | non-vacuous (round 1, dispatched with COV) |
| TODO | 001-003 | non-vacuous (round 1, `_load_diff` hardening) |
| SCOPE | 001 | **H1: vacuous on empty ticket.scope** |
| PRE | 001 | non-vacuous (round 1) |
| INV | 001-006 | non-vacuous -- unconditional scan over `invariants`/`snapshot`, no absence-guard (INV001/002/005 read in full this pass; INV003/004/006 are markdown-marker/malformed-directive variants dispatched the same unconditional way, spot-confirmed) |
| TEST | 001-016 | non-vacuous (round 1, TEST013/014/015 are themselves anti-vacuousness fixes) |
| DEBT | 001-003 | non-vacuous (this pass, unconditional edge scan) |
| DEPR | 001-004 | non-vacuous (this pass, unconditional edge scan) |
| DSL | 001 | non-vacuous -- catch-all for a malformed directive not claimed by a per-flavor check; fires whenever `frob.graph`'s DSL parser records a `MalformedDirective`, no absence-guard possible by construction |
| WAIVE | 001-007 | non-vacuous (spot-checked this pass; `_UNWAIVABLE_RULES` + WAIVE003/004/006/007 close the blanket-waiver paths) |
| DEC | 001-002 | **part of M2** (silent when `docs/decisions/` absent, same class as REG/COMPLIANCE) |
| REL | 001 | non-vacuous -- disclosed opt-in (manifest presence), DEBT/DEPR sub-checks unconditional |
| DOC | 001 | **part of M2** (silent when the obligated-docs glob match is empty) |
| DOC | 002 | non-vacuous -- `docanchor_gate` resolves every `frob:doc` edge unconditionally |
| DOC | 003 | **part of M2** (dispatched from `sys_gate`, shares its design-dir absence guard) |
| DOC | 004-005 | non-vacuous (this pass, unconditional doc scan) |
| DUP | 001-002 | enforce-off path non-vacuous (disclosed opt-in); **M3: native-unavailable path is a silent log-only degrade** |
| FUZZ | 001-003 | non-vacuous -- disclosed opt-in (`[fuzz].enforce`) |
| PERF | 001-007 | non-vacuous (this pass, routes through PARSE001-covered `parse_file`) |
| SYS | 001-004 | **part of M2** (silent when `.strata` design dir absent) |
| SEC | 001-003 | non-vacuous (round 1, spot-checked with `secrets_gate`) |
| SEC | 110 | non-vacuous (round 1) |
| TICK | 001-002 | non-vacuous (round 1; TICK002 fails closed on ambiguity) |
| TICK | 003-004,006-008 | non-vacuous (this pass, unconditional ledger scans, no absence-guard found) |
| TICK | 005 | fires correctly (`_tick005_merge_state_regression`, this pass) but **H3: missing from `_KNOWN_GATE_RULES`** |
| COMPLIANCE | 005 | **part of M2** (round 1 finding, highest-stakes instance) |
| FMT | 001 | non-vacuous -- diff-scoped by design, WARN-tier only (consistent with its own severity, this pass) |
| PII | 010 | non-vacuous structurally, but **part of M4** (private ast.parse silent-skip) |
| ARCH | 001 | non-vacuous (this pass, unconditional `analyze_project` call) |
| ARCH | 101-103 | non-vacuous enforcement; **L3: registry cross-link gap only, already disclosed, not re-filed** |
| REF | 001-003 | non-vacuous (this pass, T-0396-hardened exemptions) |
| REG | 001-010 | **part of M2** (round 1 finding) |
| REG | 011 | fires correctly (this pass) but **H3: missing from `_KNOWN_GATE_RULES`** |
| WALK | 001 | non-vacuous (round 1, spot-checked via `frob check` output) |
| EXCL | 001 | non-vacuous (this pass, both early exits are structurally correct) |
| SEC-CVE-FINGERPRINT | 001 | non-vacuous structurally, but **part of M4** (silent-skip-on-unreadable, lower-stakes text-only variant) |
| RENDER | 001 | non-vacuous structurally, but **part of M4** (private ast.parse silent-skip) |
| LANG | 001-003 | non-vacuous -- LANG001/002/003 read this pass; LANG002's `_UNREGISTERED_CANDIDATE_LANGUAGES` is a finite curated list by inherent design (cannot flag a wholly novel, unenumerated extension), a completeness boundary rather than a defect in existing logic, not filed |
| DEAD | 001 | fires correctly, Python-only by disclosed design; **L2: already tracked by an existing ticket, not re-filed** |
| PROTO | 001-003 | non-vacuous (this pass, T-0841's non-Python residual gap is disclosed) |
| PARSE | 001 | fires correctly (dispatched, unconditional over `snapshot.parse_failures`) but **H3: missing from `_KNOWN_GATE_RULES`**; its own PARTIAL-tree half is **H2** |
| PII | 011-012 | fire correctly (this pass, dispatched from `pii_structural_gate`) but **H3: missing from `_KNOWN_GATE_RULES`** |
| SYSWAIVE | 002 | fires correctly (`strata/_contention.py`) but **H3: missing from `_KNOWN_GATE_RULES`** |
| THREAT | 006 | fires correctly (`strata/_threat.py`) but **H3: missing from `_KNOWN_GATE_RULES`** |

---

## Findings tally

- Rule ids in `known_gate_rule_ids()`: 118. Plus 7 real, firing ids this
  sweep found omitted from it (H3): 125 total distinct rule ids given a
  verdict above.
- Swept this pass (round 2) at dispatch-function-or-deeper depth: INV,
  DEBT, DEPR, DSL, WAIVE (spot), DEC, REL, DOC001-005, DUP (native path),
  FUZZ (confirmed), PERF, SYS, TICK003-008, FMT, PII010-012, ARCH,
  ARCH101-103, REF, REG011, WALK (confirmed), EXCL, SEC-CVE-FINGERPRINT,
  RENDER, LANG001-003, DEAD001, PROTO001-003, PARSE001, SYSWAIVE002,
  THREAT006, plus the `_KNOWN_GATE_RULES`-completeness cross-check itself
  -- roughly 60 additional rule ids/dispatch sites read this round.
- Combined with round 1's 18 examined vectors (COV/TODO/SCOPE/PRE/TEST/
  TICK001-002/COMPLIANCE/REG001-010/DEC/FUZZ/PARSE-partial/SEC/lang parse
  entrypoint/2 strata sites), **every one of the 125 distinct rule ids in
  the table above now carries an explicit verdict** -- catalog total ==
  swept total, zero unread.
- Findings: 3 HIGH (H1, H2, H3), 4 MEDIUM (M1, M2, M3, M4), 3 LOW
  (L1/L2/L3, disclosed/already-tracked, no new ticket).
- Draft tickets filed: 7 fix/gate pairs total (14 tickets) -- 4 pairs from
  round 1 (H1, H2, M1, and M2's COMPLIANCE005 instance), 3 more pairs this
  round (H3, M3, M4). M2's additional SYS*/DOC001/DOC003 instances are
  folded into the existing M2 fix ticket's scope rather than re-filed,
  since one "adopted-then-vanished" detection mechanism should cover all
  six sites.
