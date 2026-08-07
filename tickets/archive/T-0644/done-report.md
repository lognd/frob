## Done report

T-0640 landed as REL200/REL201 (TIMEOUT obligation) on a sibling worktree
branch not yet merged to main at the time this ticket started -- pulled the
landed non-ticket files in via cherry-picked diffs (git checkout <sha> --
<path> for new files, git apply --3way of the T-0640-only diff for shared
files already touched independently by main since) rather than a wholesale
branch merge, to avoid clobbering unrelated main-side changes to the same
files.

Added REL210 (missing health surface)/REL211 (unproven health surface) to
the SAME src/frob/strata/_reliability.py module (mirroring T-0640's shape:
Report/Violation pydantic pair, apply_waivers, sys_runner wiring), scoped
to nodes carrying the T-0261 std.host unit/service long-lived-daemon
markers. Deliberately did NOT register REL210/REL211 in
_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES, unlike REL200/REL201: a node
carries at most one unit/service marker and can fire at most one
REL210/REL211 finding (no per-flow multiplicity), so the single-instance
bare-rule waiver form (the same carve-out LINT/PII/COMPLIANCE already use)
applies, not the RULE:SUBTARGET form. Disclosed and reasoned in both the
module docstring and docs/strata/reliability.md rather than mirrored
blindly.

No strata-core grammar change needed for health -- unlike timeout's
digit-led-literal ceiling, `health` is a bare presence marker (same shape
as async/local), so REL210/REL211 ship with zero grammar debt.

Own-model disposition: design/frob.strata declares no unit/service nodes
at all, so REL210/REL211 fire zero findings against frob's own model
(verified via `frob sys audit`). `frob sys audit` DOES exit nonzero
overall, but only from 32 pre-existing REL200 (missing timeout) findings
-- T-0640's own obligation, never discharged on frob's own design file --
plus one pre-existing SEC/REL001-unrelated debt; none of that is
attributable to this ticket's rule additions.

CLI wiring: check_reliability_health is called from
src/frob/app/sys_runner.py::_run_audit alongside check_reliability_timeouts,
merged into ONE combined ReliabilityReport before printing/exit-code
evaluation, so it participates in `frob sys audit`'s existing REL2xx
summary line rather than a second, disconnected surface. This required a
ticket scope extension (`frob ticket scope T-0644 --add
src/frob/app/sys_runner.py --reason ...`) since sys_runner.py sits outside
strata/**; recorded via the scope CLI, not a hand-edit.

Gates: `frob check --ticket T-0644` is clean except REL001 (public-API
version-bump gate; forbidden to touch per this worktree's playbook/dispatch
mandate -- coordinator-owned at land) and one pre-existing, unrelated ty
diagnostic in tests/system/test_cli_doctor.py (Literal["..."] vs None `in`
operator). Also pre-existing and unrelated: 3 test_export_golden.py
failures (fleet export golden drift) when running the broader
tests/unit/strata/ suite.

Merge-hygiene lesson (main landed T-0640 AND its own follow-up T-0758 --
REL201 dst-endpoint proof anchoring -- onto main mid-ticket, twice, plus a
third unrelated advance): the FIRST post-commit `git merge main` conflict
resolution for src/frob/strata/_reliability.py/test_reliability.py used a
STALE cached copy of main's file (fetched before T-0758 landed) as the
patch base, which silently dropped T-0758's fix and its two tests even
though the merge reported no conflict-content loss. Caught via
`frob check`'s gate:COV (COV003: two T-0758 evidence ids no longer
resolved to collected tests) on a SECOND full scoped check after the
merge, not by the merge itself -- re-derived the health-only diff onto a
freshly re-fetched `git show main:<path>` and re-verified before
committing the fix. Two further `git merge main` passes (main kept
advancing) each needed the same live re-fetch discipline (never a cached
copy) plus a full `frob check --ticket T-0644` re-run afterward.

## Reviewer REJECT round: shared in_scope waiver-staleness regression

Reviewer caught a real land-safety regression this session's own
`frob sys audit` run never exercised: `_apply_reliability_waivers` was
called by BOTH `check_reliability_timeouts` and `check_reliability_health`
with the SAME shared `in_scope=RELIABILITY_RULES` (all four rule ids).
`check_reliability_health` only ever produces REL210/REL211 findings, so
it saw every declared REL200/REL201 waiver (this repo's own
`graph_cache__fill`/`graph_cache__inval_f_parse`, genuinely matched and
applied by `check_reliability_timeouts`'s own pass) as "in scope but
unmatched this run" and flagged each RELWAIVE002-stale. Net effect: `frob
sys audit`'s reliability leg would have gone from main's clean
`reliability PROVED (2 waived)` to a hard error on THIS repo's own model
-- the exact self-audit-green-at-land class this repo's playbook already
names, and something my own `frob sys audit` runs during implementation
never caught because none of my litmus/unit fixtures combined a REL200
waiver with a daemon node in the SAME model exercised through both
entrypoints.

Fix: `_apply_reliability_waivers` now takes an explicit `family: frozenset[str]`
kwarg instead of closing over the shared `RELIABILITY_RULES`;
`check_reliability_timeouts` passes `_TIMEOUT_RULES =
{REL_MISSING_TIMEOUT, REL_UNPROVEN_TIMEOUT}`, `check_reliability_health`
passes `_HEALTH_RULES = {REL_MISSING_HEALTH, REL_UNPROVEN_HEALTH}`.
`RELIABILITY_RULES` itself is untouched and still correctly used by
`_audit.py::_gap_rule_in_scope`'s cross-family exclusion (that predicate
legitimately needs the whole family). Added
`TestCrossFamilyWaiverScoping::
test_timeout_entrypoint_ignores_health_family_and_health_entrypoint_ignores_timeout_family`:
one model carrying BOTH a genuine REL200 waiver (on `caller`, for
`f_missing`) AND a daemon node (`api`, no health obligation, fires
REL210) run through BOTH entrypoints, asserting neither reports the
other's waiver stale and neither emits a spurious RELWAIVE002.

Re-verified `uv run frob sys audit` on this worktree after the fix:
exit 0, `reliability: 0 violation(s), 2 waived, 0 stale waiver(s)` (log)
and `sys audit: reliability PROVED (2 waived) -- zero UNWAIVED REL2xx
gaps` (summary line) -- byte-for-byte matching main's pre-existing clean
state. 15/15 tests/unit/strata/test_reliability.py pass (14 prior + this
regression test). `frob check --ticket T-0644` re-run clean except the
same two pre-existing, disclosed, out-of-scope items (REL001 version-bump
gate, forbidden to touch per mandate; one unrelated ty diagnostic in
tests/system/test_cli_doctor.py).

### Changed
```
 docs/strata/reliability.md                         |  70 ++++-
 src/frob/app/sys_runner.py                         |  31 ++-
 src/frob/strata/__init__.py                        |   6 +
 src/frob/strata/_audit.py                          |  10 +-
 src/frob/strata/_reliability.py                    | 301 +++++++++++++++++++--
 .../strata/litmus/reliability_health_clean.strata  |  28 ++
 .../litmus/reliability_health_missing_vuln.strata  |  27 ++
 .../strata/litmus/reliability_health_waived.strata |  27 ++
 tests/unit/strata/test_reliability.py              | 178 +++++++++++-
 tickets.md                                         | 112 +++++++-
 10 files changed, 745 insertions(+), 45 deletions(-)
```

### Evidence
- `tests/unit/strata/test_reliability.py::TestMissingHealth::test_daemon_without_health_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestMissingHealth::test_discharged_daemon_nodes_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestMissingHealth::test_waiver_on_one_node_keeps_sibling_node_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenHealth::test_declared_health_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenHealth::test_declared_health_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenHealth::test_declared_health_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestCrossFamilyWaiverScoping::test_timeout_entrypoint_ignores_health_family_and_health_entrypoint_ignores_timeout_family` (pytest node id, verified passing when recorded)
