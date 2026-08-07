## Done report

Enumerated gate:ARCH (ARCH001 long-function, `frob check --only archgate`) against
current main: 22 unwaived warnings (grown from the ticket's 17-warning baseline
as other work landed on main since filing). Classified each of the 22 as
FIX (a real, low-risk extraction) or WAIVE (a single cohesive algorithm/dispatch
where splitting adds indirection without reducing complexity), executed both
dispositions, and re-verified.

## Classification table

| Function (file) | Disposition | Rationale |
| --- | --- | --- |
| `_place001_file` (gates/__init__.py) | FIXED | extracted per-comment check into `_place001_comment_violation` |
| `_cov006` (gates/__init__.py) | FIXED | extracted per-edge check into `_cov006_edge_violation` |
| `_test014_ambiguous_convention` (gates/__init__.py) | FIXED | extracted grouping phase into `_test014_group_by_leaf` |
| `_test015_vacuous_credit` (gates/__init__.py) | FIXED | extracted per-record check into `_test015_record_violation` |
| `doc005_gate` (gates/_docblocks.py) | FIXED | split into `_doc005_missing_stale_violations` + `_doc005_count_violations` |
| `_parse_attrs` (graph/dsl.py) | FIXED | extracted per-verb dispatch into `_parse_attrs_verb_error` |
| `redundant_computation_violations` (perf/_redundancy.py) | FIXED | extracted collection phase into `_perf007_call_sites` |
| `load_repo_benign_capabilities` (strata/_threat.py) | FIXED | extracted per-entry validation into `_validate_benign_entry` (typani `Result`) |
| `_kt_collect_body_events` (arch/_kotlin.py) | WAIVED | flat per-node-type dispatch intentionally mirroring the rust/ts adapters (T-0609); splitting fragments one coherent walk |
| `_rust_collect_body_events` (arch/_rust.py) | WAIVED | same as above, rust adapter |
| `_ts_collect_body_events` (arch/_typescript.py) | WAIVED | same as above, typescript adapter |
| `build_group_template` (dup/_template.py) | WAIVED | incremental Plotkin lgg fold threading running state across two load-bearing loops |
| `_cov006_implicit_dispatch_reachable` (gates/__init__.py) | WAIVED | multi-stage heuristic, each stage's guard depends on the prior stage's locals |
| `_cov006_third_file_reachable` (gates/__init__.py) | WAIVED | multi-stage heuristic, chain of derived candidate sets |
| `_cov006_public_wrapper_reachable` (gates/__init__.py) | WAIVED | multi-stage same-file-wrapper heuristic, same shape |
| `dead_symbol_gate` (gates/_dead_symbols.py) | WAIVED | per-package reference-graph cache built lazily inside the loop |
| `_console_command_violations` (gates/_docblocks.py) | WAIVED | trailing UNBOUND check depends on an accumulator built across the whole per-line scan |
| `_lang003_unsound_gaps` (gates/_lang_conformance.py) | WAIVED | already split out of `project_lang_conformance_gate` once for a prior ARCH001 finding |
| `_walk_repo_files` (graph/__init__.py) | WAIVED | deliberate single-pass fusion (T-0239/T-0245) for perf; extracting would add a per-file call in a hot walk |
| `stale_natives` (strata/_native_staleness.py) | WAIVED | T-0513's ordered mtime/first-observation/content-digest decision tree over one mutated stamps dict |
| `add_evidence` (tickets/__init__.py) | WAIVED | typani Result guard chain, each stage already its own dedicated helper |
| `_land_locked` (tickets/_land.py) | WAIVED | already the decomposed T-0577 orchestrator; remainder is try/finally sequencing |

8 fixed via real extractions (each new helper carries its own one-line
docstring and a `frob:ticket T-0598` directive), 14 waived with an honest,
specific `frob:waive ARCH001 reason="..."` naming the actual reason
splitting would not help.

## Final gate line

`uv run frob check --only archgate`:
```
pass  gate:ARCH               0 errors, 0 warnings, 14 waived
```
0 unwaived ARCH001 warnings. (`gate:WAIVE`'s 3 WAIVE002 warnings in that same
run are pre-existing, unrelated to this ticket -- DEAD001 waivers in test
files outside this ticket's `src/frob/**` scope.)

## Verification

- `uv run ruff check <touched files>` -- clean, both `uv run ruff` (0.15.16)
  and PATH `ruff` (0.14.10).
- `uv run ty check <touched files>` -- clean (fixed one `Any` vs `object`
  typing regression introduced by the `_validate_benign_entry` extraction).
- Targeted pytest, foreground, all green:
  `tests/test_gates.py`, `tests/test_docblocks_gate.py`,
  `tests/unit/graph/test_dsl.py`, `tests/unit/test_arch.py`,
  `tests/unit/strata/test_native_staleness.py`, `tests/test_perf.py`,
  `tests/unit/strata/test_threat.py`, `tests/test_ticket_land.py`,
  `tests/test_tickets.py`, `tests/test_tickets_acceptance.py`.
- Reverted an incidental `uv.lock` version-string diff produced by the
  `make core` warm-up (unrelated to this ticket, would have tripped
  SCOPE001).

No threshold was loosened; the `ARCH001` line-count/complexity threshold
in `frob.toml`'s `[arch]` table is untouched.

### Changed
```
 tickets.md | 149 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 143 insertions(+), 6 deletions(-)
```

### Evidence
(no evidence recorded)
