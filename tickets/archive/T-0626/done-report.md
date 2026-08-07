## Done report

Changed:
- docs/design/registry/arch-checks.yaml -- 13 entries re-dispositioned off
  the placeholder `deferred:T-0391`, closing the T-0330 half of the
  DENOMINATOR MANIFEST gap for architecture-check-catalog.md:
  - `ACC-1-1-1` (SOLID/S, SRP), `ACC-2-1-LARGE-CLASS` -> `handled_by:ARCH101`
    (T-0616's LCOM4 low-cohesion-class check, a real, live, gated rule id
    in `frob.gates._arch._ARCH_CATEGORY_TO_RULE` / `_KNOWN_GATE_RULES`).
  - `ACC-1-1-2` (SOLID/O, OCP), `ACC-2-1-REPEATED-SWITCHES` ->
    `out_of_scope:none -- ...` (T-0617's type-dispatch-smell /
    non-exhaustive-enum-match, built but dispatched only through
    `frob.arch.analyze_project`'s T-0101 unwaivable WARN-suggestion
    channel, no ARCH1xx gate id assigned).
  - `ACC-1-1-3` (SOLID/L, LSP) -> `out_of_scope:none -- ...` (T-0618's
    5 lsp-* checks in `src/frob/arch/_solid.py`; verified the ARCH104-108
    ids that module's own comments use are documentation-only -- NOT
    present in `frob.gates._arch._ARCH_CATEGORY_TO_RULE` nor
    `_KNOWN_GATE_RULES` -- confirmed live by a `handled_by:ARCH104` trial
    edit tripping REG002 "dangling enforcement reference" before this
    correction).
  - `ACC-1-1-4` (SOLID/I, ISP) -> `out_of_scope:none -- ...` (T-0619's
    fat-interface/narrow-client-usage; same ARCH109/110
    documentation-only-id finding as LSP above).
  - `ACC-1-1-5` (SOLID/D, DIP), `ACC-1-2-ADP-ACYCLIC-DEPENDENCIES` ->
    `out_of_scope:none -- ...` (T-0620's dip-layering-violation/
    no-di-construction; T-0625's module-dependency-cycle, reusing
    T-0620's graph builder -- both WARN-channel-only, no gate id).
  - `ACC-2-1-FEATURE-ENVY`, `ACC-2-1-DATA-CLUMPS` ->
    `out_of_scope:none -- ...` (T-0624, WARN-channel-only).
  - `ACC-2-1-PRIMITIVE-OBSESSION`, `ACC-2-2-F3-FLAG-ARGUMENTS` ->
    `out_of_scope:none -- ...` (T-0621, WARN-channel-only).
  - `ACC-2-2-F4-DEAD-FUNCTION` -> `out_of_scope:none -- ...` (T-0624,
    WARN-channel-only).
- tickets.md -- T-0626 lease/evidence bookkeeping (`frob ticket start` /
  `sweep` / `evidence`), this Done report.

Investigation, no code change needed: design-pattern-traps-corpus.md's
half of the DENOMINATOR MANIFEST is ALREADY closed, pre-existing (T-0332,
already `done`) -- `docs/design/registry/patterns.yaml`'s `PAT-TRAP-01`
through `PAT-TRAP-21` entries (`grep -n '"PAT-TRAP-' patterns.yaml`) cover
every one of the corpus's 21 "Phase-0/Phase-2 coverage ledger" sections,
each dispositioned `out_of_scope:advisory-design-pattern-recommendation`
(T-0332's own recommender-scope framing) with `cross_refs` back into
`arch-checks.yaml` where a matching ACC row exists (`ACC-2-1-SPECULATIVE-
GENERALITY`, `ACC-1-5-COMPOSITION-OVER-INHERITANCE`, etc.). I verified
this by enumerating the 21-item ledger against `patterns.yaml`'s ids
before writing a duplicate file; left `patterns.yaml` untouched since
T-0332 is closed and its dispositions are internally consistent for its
own (advisory-recommender, not static-check) scope -- re-litigating them
is outside this ticket's declared scope and outside T-0330's catalog text.

Disclosed scope note: `ACC-1-1-1`/`ACC-2-1-LARGE-CLASS` (`handled_by:
ARCH101`) and `ACC-2-1-LARGE-CLASS` now trip `REG008` (WARN, not ERROR --
`handled_by` claim with no matching `frob:enforces ACC-*` directive
anywhere in code yet) -- the identical gap T-0728 (landed today, same
session) left open and disclosed for `check-coverage.yaml`'s
`CHK-GATE-ARCH101/102/103` rows, with the same reasoning: adding the
`frob:enforces` directive means touching `src/frob/gates/_arch.py`,
outside this ticket's `docs/design/registry/**`-only scope. Filed nothing
new for it -- it is the same disclosed land obligation T-0728 already
named, not a fresh gap this ticket introduced.

Evidence:
- `uv run frob check --only registry --ticket T-0626` -- `gate:REG 0
  errors` (before the LSP/ISP disposition correction above this showed
  `gate:REG 2 errors` -- both `REG002` dangling `handled_by:ARCH104`/
  `handled_by:ARCH109`, which is exactly how I discovered ARCH104-110 are
  documentation-only ids, not live gate rules).
- `uv run frob check --only lint --ticket T-0626` -- 0 errors, 0 warnings.
- `uv run frob check --only gates-fast --ticket T-0626` -- 0 errors (all
  12 gates `pass`, including `gate:REG`).
- `uv run frob check --only static --ticket T-0626` -- 0 errors (all
  `frob-*` tools `pass`).
- `uv run frob check --only gates-native --ticket T-0626` -- 0 errors.
- `uv run frob check --only gates-security --ticket T-0626` -- 0 errors.
- `uv run pytest tests/test_registry_exhaustiveness.py::TestDisposition::
  test_dangling_handled_by_fails
  tests/test_registry_exhaustiveness.py::TestDisposition::
  test_handled_by_real_rule_passes
  tests/test_registry_exhaustiveness.py::TestEnforcesConformance::
  test_handled_by_with_no_frob_enforces_edge_warns
  tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::
  test_substantive_reasoned_none_is_silent -q` -- 4 passed (the existing
  `registry_gate` unit tests that generically exercise the exact
  `handled_by`/`out_of_scope` classification paths this ticket's new
  dispositions are dispatched through; a docs-only ticket with no new
  code surface of its own, per the playbook's precedent for this shape).
- `git diff main --diff-filter=D --stat` -- empty (no unintended
  deletions).

Filed: none.
Gates: `frob check --ticket T-0626` clean across all 5 stage groups
(lint/static/gates-fast/gates-native/gates-security), chunked per the
playbook's `--only` loop.
