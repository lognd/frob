## Done report

Fixed the vacuous NoFlow discharge gap (docs/audits/strata.md G2/G7):
`_mitigation_is_chokepoint`'s vacuous-path short-circuit ("if `claim`
already holds with every boundary removed, accept it as PROVED") used
to accept a discharge with zero mitigation modeled whenever the
foreign->sink flow was simply absent from the model, regardless of
whether the model actually contained a real adversary elsewhere.

Repro that previously discharged vacuously (now fails closed, see
`TestFlowCompletenessGap::test_foreign_node_present_but_no_flow_to_sink_fails_closed`
and the "_specific" regression fix below): a model with a real
`trust="foreign"` node (`Evil`) and a sink node (`Web`, `may
"html_render"`) whose CWE-79 obligation is discharged by
`NoFlow(src="Evil", dst="Web")` -- with NO `flow` connecting them at
all. Before this fix, `check_discharge_completeness` returned `Ok(())`
(clean) for that model; `Web`'s real inbound path from untrusted input
was never modeled, yet the obligation "PROVED".

Added `_flow_completeness_gap` (`_threat.py`): when a `NoFlow` claim's
source expands to at least one real foreign-trust node, but the claim
still holds with every boundary removed (no path to the sink at all),
this now returns a G2-worded finding instead of `None`, and
`_check_discharge_mitigation_kind` emits it as a THREAT003 violation
BEFORE calling `_mitigation_is_chokepoint` at all.

Deliberately did NOT flag the case where the model has ZERO
`trust="foreign"` nodes anywhere: that is T-0223's documented, tested
"library-mode discharge by absence" mechanism
(docs/strata/threat.md#library-mode-discharge-by-absence,
`TestLibraryModeForeignlessDischarge`), a genuinely foreign-less
library model honestly declaring "no adversary is modeled here" --
re-verified those two litmus fixtures still pass unchanged. G7 as
literally worded in the audit ("no foreign-trust node exists is always
a gap") is this ticket's one disclosed non-fix, narrowed instead to the
mixed-model case (a foreign node exists somewhere in the model, but
this specific obligation's flow to it was never wired up) -- fixing G7
as originally worded would regress T-0223's shipped mechanism, which
this pass judged the wrong tradeoff without a separate design decision
on reconciling the two.

Found (and fixed, not filed) one pre-existing test that was itself an
undetected instance of this exact vacuous discharge:
`TestDischargeChokepointShape::test_noflow_from_a_specific_foreign_trust_node_discharges`
asserted a clean discharge for a model with NO flow and NO boundary
between the named foreign node and the sink -- i.e. it was pinning down
the G2 bug as correct behavior. Updated it to add a real flow plus a
matching ENDORSE mitigation boundary so it now tests the genuine
chokepoint-shape acceptance it was meant to, and added
`TestFlowCompletenessGap` (3 new tests) as the dedicated regression
suite for the fix.

Also merged main mid-ticket (section 1/10b: `main` had advanced with
unrelated T-0332/T-0386/T-0554 landings) to keep the deletion-filter
check clean before finishing -- verified `git diff main --diff-filter=D
--stat` empty after the merge, and `make core` + the full
tests/unit/strata/test_threat.py suite green afterward.

Command output actually run and read:
- `uv run pytest tests/unit/strata/test_threat.py -p no:cacheprovider -q`: 119 passed.
- `uv run pytest tests/unit/strata/ -p no:cacheprovider -q`: 1 pre-existing failure
  (`test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant`,
  SYS102 on src/frob/registry -- confirmed pre-existing on main, not caused by this change),
  all others passed.
- `uv run frob check --ticket T-0501`: 0 errors, 375 warnings, 188 waived (clean).

### Changed
```
 src/frob/strata/_threat.py       |  92 ++++++-
 tests/unit/strata/test_threat.py | 127 +++++++++
 tickets.md                       | 562 ++++++++++++++++++++++++++++++++++++++-
 3 files changed, 767 insertions(+), 14 deletions(-)
```

### Evidence
(no evidence recorded)
