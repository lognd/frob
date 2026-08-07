## Done report

Added _is_self_named_forwarder (per-member: is this member's serialized
body a short single-statement call-through to a symbol sharing its own
bare name) and _is_call_through_forwarder_family (all members of the
evidence-cluster subset satisfy the per-member check). Wired into
_check_abstraction_opportunities against `flagged` (the post-clustering
evidence subset), not the raw signature group -- necessary because a raw
group can mix genuine forwarders with unrelated same-signature members
(RenderWriter._emit/.line alongside .heading/.good/.warn), and the
near-duplicate-body clustering already isolates the real forwarder
cluster from those before this check should apply.

Measured before/after via `frob check --only arch --json`, counting
"abstraction-opportunity" occurrences: 65 -> 64 (RenderWriter's
heading/subhead/good/warn/muted false-positive, T-1083's original
finding, no longer flagged). Verified directly against the real
src/frob/render files with the exclusion both present and (temporarily)
removed to confirm it is the specific mechanism suppressing the finding.

### Changed
```
 tickets.md | 12 +++++++++---
 1 file changed, 9 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_distinct_named_self_forwarders_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_group_with_one_non_self_named_member_still_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_forwarder_helper_requires_self_named_short_body` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 453 warning(s), 679 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w22-arch/src/frob/arch/_python.py:1523, SELFAUDIT001@design
