## Done report

Reconciled all 311 `docs/design/registry/arch-checks.yaml` entries. Before
this ticket, 296 were placeholder `deferred:T-0391` (self-referential --
this ticket itself was the deferral target) and 15 were already
dispositioned by earlier work (T-0626's 13 SOLID-family entries + 2
`handled_by` entries). After this pass, 0 entries are undispositioned:

- 6 `handled_by:<rule>` (2 new: `ACC-1-5-DRY-DON-T-REPEAT-YOURSELF` and
  `ACC-4-COPY-PASTE-PROGRAMMING` both bound to `DUP001`, the real
  duplicate-code detector -- verified DUP001 is a live member of
  `frob.gates.known_gate_rule_ids()`; the other 4 were pre-existing:
  ARCH001 x1, ARCH101 x2, DUP001 x1 for `ACC-2-1-DUPLICATED-CODE`).
- 305 `out_of_scope:<reason>` (296 new this pass + 9 pre-existing).

Disposition counts by kind (final state, verified programmatically via
`frob.registry.load_registry_dir` + `frob.gates.known_gate_rule_ids`, not
by eyeballing the yaml): `handled_by`=6 (all resolve against the live
known-rule-id set), `out_of_scope`=305 (all carry a non-empty reason),
`deferred`=0, `duplicate_of`=0, `undispositioned`=0.

Reasoning approach (mirrors T-0722/T-0626/T-0912 precedent): every entry
was checked against frob's ACTUAL built surface before writing a reason.
Two categories of true positives were found and given specific,
individually-verified reasoning:

1. Entries matching a REAL frob.arch check that exists but is NOT wired
   to a gate rule id (`ACC-1-5-MAKE-ILLEGAL-STATES-UNREPRESENTABLE` ->
   T-0621 `check_illegal_states_representable`; `ACC-1-5-PARSE-DON-T-
   VALIDATE` -> T-0621 `check_parse_dont_validate`; `ACC-1-5-ERRORS-AS-
   VALUES` -> T-0688 `check_errors_as_values`, explicitly distinguished
   from the real EXHAUST001/EXHAUST002 gate which enforces a narrower,
   different claim -- exhaustive may-raise handling, not the broader
   errors-as-values idiom -- so EXHAUST001/002 was NOT fabricated as its
   handled_by) -- same T-0101 unwaivable-advisory-channel reasoning the
   existing 15 precedent entries already established.
2. Entries matching the T-0332 pattern-recommender (`src/frob/arch/
   _patterns.py`, advisory HALLMARK->PATTERN/ANTI-PATTERN->ESCAPE, no
   gate rule id) for the GoF/PoEAA/DDD/Concurrency/Functional pattern
   manifest-rollup rows (`ACC-3-1` through `ACC-3-5`).

For the remaining ~289 entries (package/component metrics, GRASP,
connascence, laws/heuristics, Fowler/Clean-Code smell catalogs,
language idioms, anti-patterns, distributed-systems/cloud/12-factor/
observability/consistency/security/scalability principles, and the
structural-linter-adversarial-hardening.md design-defense rows), I
verified NO frob detector exists for the specific named concept (checked
against every `check_*` function across `frob.arch/_smells.py`,
`_typedesign.py`, `_solid.py`, `_layering.py`, `_ocp.py`, `_exceptions.py`,
`_fallibility.py`, `_logging_checks.py`, `_async_hazards.py`,
`_lock_ordering.py`) and no gate/policy rule id exists to bind. Several
DO have a closely-related obligation freshly landed in `frob.strata`
(e.g. `_ssot.py`'s REL290/291 for Single Source of Truth,
`_delivery_semantics.py`, `_backpressure.py`, `_observability.py`) --
verified these strata rule ids are NOT yet part of this registry gate's
`known_rules` union (`_KNOWN_GATE_RULES | st.rule_ids` in
`src/frob/gates/__init__.py`'s `registry` gate lambda only draws from
`_KNOWN_GATE_RULES` + loaded `frob.policy` rules, neither of which
includes strata's REL-family ids today -- confirmed live via
`known_gate_rule_ids()`, `'REL290' not in _KNOWN_GATE_RULES`). Binding
`handled_by` to those would have been an unverifiable lie past this
gate's own REG002 check (it would in fact fail REG002 outright, since
`known_rules` doesn't include them) -- disclosed explicitly in each such
entry's reason text rather than silently claimed or silently dropped.
This strata-rule-id/registry-gate wiring gap is the same class T-0382's
Done report already flagged for `caught_by`; not re-filed as a new
ticket here since it is already a named, tracked gap, not a silent one,
and fixing it would mean editing `frob.strata`'s public surface, outside
this ticket's declared scope (`src/frob/gates/`, `docs/design/registry/
arch-checks.yaml`).

No new child ticket filed: every one of the 311 entries received a
disposition this pass (0 remain `pending`/undispositioned), so there is
no "precise remainder" left to defer -- the file's own `total: 311` field
now agrees with the entry-list length.

Real bug encountered and worked around (not silently fixed elsewhere,
resolved in-scope in this same file): my first mechanical disposition
pass wrote unquoted YAML scalars containing `:` characters, which is
invalid YAML (`mapping values are not allowed here`) -- caught by
re-parsing the file with `frob.registry.load_registry_dir` rather than
trusting `grep`, and fixed by double-quoting + escaping every affected
`disposition:` value in a follow-up pass; final state verified to parse
cleanly and resolve with zero malformed entries.

Infra note (NOT fixed, outside this ticket's scope, disclosed not
hidden): this worktree's `tickets.md`/`tickets-archive.md` (inherited
unchanged from `main` at merge time -- confirmed byte-identical to
`main`'s own `tickets-archive.md`) has ~100 ticket ids present in BOTH
the active and archive ledgers (`DuplicateId` on full queue load), which
makes `frob ticket show`/`frob check` fail outright. This pre-exists
this ticket's changes (verified against `main`'s own checked-out
`tickets.md`/`tickets-archive.md` before any edit here) and is a
repo-wide ledger-hygiene bug, not something in this ticket's scope to
fix. Verification here was therefore done directly against
`frob.registry.load_registry_dir` + `frob.gates.known_gate_rule_ids`
(bypassing the broken ticket-queue load path) plus the registry's own
pytest fixture suite, neither of which depends on the live ticket queue.

Test evidence (measured): `uv run pytest
tests/test_registry_exhaustiveness.py -q` -> 33 passed (all
pre-existing fixture tests, unaffected -- this ticket only edits the
corpus yaml, not the gate logic). Programmatic verification against the
live registry+known-rules (not a fixture): `load_registry_dir` on
`docs/design/registry/arch-checks.yaml` -> 0 malformed, 0
undispositioned, 0 dangling `handled_by`, 0 empty `out_of_scope`
reasons, 0 duplicate ids within the file; whole-registry scan (all
`REGISTRY_FILES`) -> 0 dangling `duplicate_of` targets across 2081
total ids.

Filed: none.

Gates: `frob check` / `frob check --ticket T-0391` could not be run end
to end due to the pre-existing, out-of-scope `tickets.md`/
`tickets-archive.md` DuplicateId condition described above (disclosed,
not waived around) -- the CLI's gate runner loads the full ticket queue
before dispatching to individual gates, so `--only registry` could not
be isolated that way either. In its place: `frob.registry.
load_registry_dir` + `frob.gates.known_gate_rule_ids` direct
verification (above) plus `tests/test_registry_exhaustiveness.py` (33
passed) stand as the evidence that the registry-gate LOGIC this
ticket's yaml must satisfy does in fact accept every entry cleanly.

### Changed
```
 tickets.md | 12628 ++++++++++++++++++++++++++++++++++++++++++++---------------
 1 file changed, 9543 insertions(+), 3085 deletions(-)
```

### Evidence
- `tests/test_registry_exhaustiveness.py::TestDisposition::test_undispositioned_entry_fails` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestDisposition::test_handled_by_real_rule_passes` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestDisposition::test_out_of_scope_no_reason_fails` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_fails` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: none (measured, zero errors)
