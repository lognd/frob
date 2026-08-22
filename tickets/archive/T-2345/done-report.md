## Done report

Root cause fixed at its actual entry point, per the ticket's own
diagnosis: `_parse_error_findings_from_json` (src/frob/app/ticket_runner/
_verify.py) built findings as `(d.get("code") or "", d.get("file") or
"")` unconditionally -- any error-severity diagnostic missing BOTH fields
became a genuine `("", "")` member of the returned identity set. T-2313
already fixed the SYMPTOM one layer downstream
(`_rapid_sweep.py::_normalize_identities` drops an identity-less pair
before it reaches a baseline diff or a filed ticket); this ticket closes
the actual source so every OTHER caller of this function inherits the
same protection automatically, not just the one consumer T-2313 touched.

Fix: skip (never silently) any diagnostic where both `code` and `file`
are empty/missing, logging a WARNING that names the ticket id AND the
emitting tool (`r.get("tool")`) plus the raw diagnostic dict -- this
doubles as the "identify which tool is emitting this shape" half of the
ticket's own WANTED section: rather than a one-time static grep for a
candidate culprit (which could miss a tool that only produces this shape
under a specific failure condition), the warning surfaces the actual
offending tool live, every time it happens, from here forward.

Interaction with T-2313 noted explicitly per the coordinator's brief:
with T-2313 already landed, a broken record is now discarded by BOTH the
producer (this fix) and the consumer (T-2313's filter) -- the repro test
here calls `_parse_error_findings_from_json` directly rather than trying
to observe a surviving blank identity downstream, since T-2313 would
already have removed it by the time anything downstream could see it.

Verified against a genuine repro: committed the repro tests alone
(9e48165f7), confirmed both new failure-mode tests genuinely FAIL at that
commit against the pre-fix source (checked by temporarily restoring
main's pre-fix _verify.py and re-running -- one assertion failure showing
the stray `("", "")` identity, one showing an empty log), restored the
fix (1a13fb679), re-ran -- all 23 tests in the file pass.
`--check-repro`/`--designate-repro` against base-ref 9e48165f7 confirms
FAILED_AT_PARENT.

Changed:
- src/frob/app/ticket_runner/_verify.py::_parse_error_findings_from_json

Evidence:
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_blank_identity_diagnostic_is_dropped_not_added (designated repro, FAILED_AT_PARENT @ 9e48165f7)
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_drop_is_logged_naming_the_emitting_tool
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_a_diagnostic_with_only_file_set_is_kept

Filed: none.

ADDENDUM (confirmed live, not just synthetic): the new WARNING fired for
real during this ticket's own done-report gate check, naming the culprit
tool directly: `frob-cycle` (import-cycle detection) emits its
diagnostic with `code: None, file: None` -- it reports the cycle only in
free-text `message` (a chain of file paths), never in the structured
`code`/`file` fields every other tool uses. This is the concrete answer
to the ticket's "identify which tool is emitting this shape" ask: cycle
diagnostics are inherently multi-file (a whole cycle, not one site), so
they were never a good fit for a single `(rule, file)` identity to begin
with -- this fix stops them from corrupting the identity space as a
blank pair; whether `frob-cycle` should instead synthesize a
representative `code`/`file` (e.g. the first file in the cycle) is a
separate, out-of-scope design question worth its own ticket if the
coordinator wants cycle regressions tracked as first-class identities
rather than just not-corrupting ones.

### Changed
```
 src/frob/app/ticket_runner/_verify.py          | 39 +++++++++++-
 tests/unit/test_ticket_runner_gate_findings.py | 87 ++++++++++++++++++++++++++
 tickets/T-2345/done-report.md                  | 65 +++++++++++++++++++
 tickets/T-2345/ticket.md                       | 10 ++-
 4 files changed, 197 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_blank_identity_diagnostic_is_dropped_not_added` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_drop_is_logged_naming_the_emitting_tool` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_a_diagnostic_with_only_file_set_is_kept` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_verify.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2345/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2345/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2345, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
