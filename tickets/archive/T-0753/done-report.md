## Done report

Naming correction up front: `WAIVE003` was already live (T-0470,
over-broad package-prefix waiver reach) before this ticket -- the ticket
body's "NEW WAIVE003" for unnecessary-waiver detection would have
collided with it. Implemented as **WAIVE004** instead, and the
`until=`-expiry check as **WAIVE005** (both added to `_KNOWN_GATE_RULES`).

The 3 "live DEAD001 waivers": root-caused, not retargeted. `DEAD001` is a
real, always-run gate rule (`frob.gates._dead_symbols.dead_symbol_gate`,
wired into `_ALL_GATES` as the `dead_symbols` process job) but was simply
missing from `_KNOWN_GATE_RULES`'s frozenset -- a listing omission, not a
rename. Added `"DEAD001"` to that frozenset; all 3 waivers
(`tests/test_dup_cross_lang.py::_isolated_dup_cache`,
`tests/test_docblocks_gate.py::_fake_parser_factory`,
`tests/unit/test_dup_cache.py::_close_cached_connections`) are unchanged
and confirmed genuinely needed: `frob check --only gates-security` (which
runs `dead_symbols`) shows all 3 correctly matched and suppressed, with no
WAIVE004 false-fire at their sites.

(1) WAIVE002 promoted WARN -> ERROR (`_waive002_violation_for`).

(2) WAIVE004 (`_waive004_violations`, `src/frob/gates/__init__.py`): for
every `frob:waive` on a recognized rule id, re-runs `_match_waiver` against
this run's full pre-waiver violation set (same set WAIVE003 already
consumes); zero matches = WARN. Verified both directions: fires on a
constructed valid-rule/zero-finding site
(`test_waive004_fires_on_valid_rule_zero_findings`), stays silent when the
site still has a live match
(`test_waive004_stays_silent_on_a_genuinely_needed_waiver`), and does not
pile onto an edge WAIVE002 already flags
(`test_waive004_skips_a_waive002_unrecognized_rule`). Known-flaky
documented in `docs/modules/gates.md#unnecessary-waiver-detection-t-0753`:
a rule excluded by `--only`/gate selection (e.g. `gates-fast` excludes
`dead_symbols`) or a diff-scoped rule can zero-match for reasons unrelated
to staleness -- trust WAIVE004 only from a full unscoped run. Ratchet-to-
error path noted as a natural T-0569/T-0594-pool follow-up, not built.

(3) `until="YYYY-MM-DD"` on `frob:waive`
(`src/frob/graph/dsl.py::_parse_attrs_verb_error`): reuses `_DATE_RE`
verbatim (the same regex `frob:deprecated`'s `sunset=` validates, T-0576
precedent) -- a malformed date is a WAIVE001-shaped `MalformedDirective`
(same substring-filter reuse DEBT/DEPRECATED already established).
WAIVE005 (`_waive005_violations`) mirrors DEBT003/DEPR004's plain expiry
escalation (ERROR); no ticket-lifecycle check (WAIVE005 has no DEBT002/
DEPR002 counterpart) since `frob:waive` carries no `ticket=`. An expired
waiver still suppresses its violation -- the point is forcing re-review,
not auto-revoking. Coordinated with T-0671/SYSWAIVE002 per the mandate:
documented in `docs/modules/gates.md#waiver-expiry-t-0753`, same grammar,
no second date format.

Changed:
- src/frob/gates/__init__.py::_waive002_violation_for (WARN -> ERROR)
- src/frob/gates/__init__.py::_KNOWN_GATE_RULES (+DEAD001, +WAIVE004, +WAIVE005)
- src/frob/gates/__init__.py::_waive004_violations (new)
- src/frob/gates/__init__.py::_waive005_violations (new)
- src/frob/gates/__init__.py::_assemble_gate_report (wires WAIVE004/WAIVE005 in)
- src/frob/graph/dsl.py::_parse_attrs_verb_error (waive until= validation)
- docs/modules/gates.md (WAIVE002 tier note, WAIVE004/WAIVE005 sections, table rows)
- tests/test_gates.py (severity assertion updated + 7 new tests)

Evidence (all foreground, this worktree):
- `uv run pytest tests/test_gates.py -k "waive0 or dsl001 or Waive"` -- pass
  (new: `TestTestGate::test_waive004_fires_on_valid_rule_zero_findings`,
  `test_waive004_stays_silent_on_a_genuinely_needed_waiver`,
  `test_waive004_skips_a_waive002_unrecognized_rule`,
  `test_waive005_expired_until_is_error`, `test_waive005_future_until_passes`,
  `test_waive_until_bad_date_is_malformed`; updated:
  `TestCoverageGate::test_waive002_flags_arch_category_as_ineffective`)
- `uv run pytest tests/test_gates.py tests/test_dup_cross_lang.py tests/test_docblocks_gate.py tests/unit/test_dup_cache.py tests/unit/graph/test_dsl.py`
  -- 396 passed, 0 failed
- `uv run frob check --ticket T-0753` -- gate:WAIVE 0 errors, 634 warnings,
  0 waived; ruff-check/ruff-format pass; `ty` shows 1 pre-existing
  diagnostic in `tests/system/test_cli_doctor.py` (outside this ticket's
  scope, unrelated to `frob:waive`/gates, present before this change)
- `uv run frob check --only gates-security` -- confirms the 3 DEAD001
  waivers remain genuinely matched/suppressed, no WAIVE004 false-fire

Filed: none (the DEAD001 gap turned out to be a fix within scope, not a
separate filing; `docs/design/registry/check-coverage.yaml`'s REG010 WARN
now also lists WAIVE004/WAIVE005/DEAD001 missing `CHK-GATE-<rule>` entries
-- out of this ticket's declared scope, WARN-tier, pre-existing pattern
for DEAD001/TICK006 already; left for `frob registry audit
--sync-gate-rules` at land or a follow-up, not filed as its own ticket
since it is a one-command sync, not new work).

Gates: `frob check --ticket T-0753` clean (0 errors on every gate:*
stage); pre-existing `ty` diagnostic in an out-of-scope test file is the
only tool-stage FAIL, unrelated to this change.
