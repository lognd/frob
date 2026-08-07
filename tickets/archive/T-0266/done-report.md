## Done report

Changed:
- src/frob/strata/_selfconform.py::_dedupe_sys100_extended_against_core (new)
- src/frob/strata/_selfconform.py::_collect_sys_violations (wires the new dedupe step between the core and extended SYS100 producers)

Investigation note: under the CURRENT registry, `_KIND_MAP` (net/fs/exec) and `_EXTENDED_KINDS` (eval/env/ffi/install-hook/sql/deserialize/html_render/fetch_url/client_storage/fs-read) are disjoint kind vocabularies, so the exact duplicate cannot reproduce through a normal scan today. The fix is written generically (dedupe by `(node, capability)`, core kept whole since it is the only side that can legitimately report multiple real sites per node+kind, extended filtered against it since it is coarser/node-level-only) so a future kind landing in both tables (T-0158/T-0304 already moved capability strings between the two more than once) cannot silently double-report. Regression test forces the overlap via `monkeypatch` widening `_EXTENDED_KINDS` to include `net`, proving the merge collapses a real dual-observed site to one finding end-to-end through `check_self_conformance`, plus two isolated unit tests on the merge helper itself (drops the duplicate; keeps distinct `(node, capability)` pairs untouched).

Evidence:
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceCrossPassDedup::test_dedupe_helper_drops_extended_when_core_already_reports_same_site
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceCrossPassDedup::test_dedupe_helper_keeps_distinct_node_or_capability_sites
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceCrossPassDedup::test_same_site_observed_by_both_passes_yields_one_finding
- `uv run pytest tests/unit/strata/test_selfconform.py -q` -> 38 passed
- `frob test --base main` -> selected `src/frob/strata` + `tests/unit/strata/test_selfconform.py`, `[PASS] python exit=0 5.14s`

Filed: none

Gates: `uv run ruff check src/frob/strata/_selfconform.py tests/unit/strata/test_selfconform.py` clean under both `uv run ruff` and PATH `ruff`. `frob check --ticket T-0266 --json` shows no new errors touching `_selfconform.py`/`test_selfconform.py` (the only `_selfconform`-related line is a pre-existing `TestBindingErrorPropagation` export warning, unrelated to this change). No `.frob/baseline` stamp existed in this worktree so `--delta` fell back to the full violation set (pre-existing, unrelated findings across the repo) -- not a gate this ticket introduced.

Not closed (reviewer-gated per playbook section 11.4).
