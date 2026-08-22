"""`SelfConformViolation`/`SelfConformReport` (T-2729 layer 0): the two
result models every SYS1xx rule function and `_selfconform.py`'s own
orchestration build and pass around. Kept as their own leaf module so
every split-out rule module can construct a `SelfConformViolation`
without importing `_selfconform.py` itself (that would invert the split's
import direction back into a cycle)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

# frob:doc docs/strata/selfconform.md#the-three-rules
# frob:tests tests/unit/strata/test_native_test.py::TestSummarize.test_format_selfconform_one_line_per_violation  # noqa: E501
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
class SelfConformViolation(BaseModel):
    """One SYS100/SYS101/SYS102 finding: rule id, the node (or directory,
    for SYS102) it concerns, a human-readable detail string, and (SYS100/
    SYS101 only) the capability kind this specific instance fired for.
    `capability` is T-0174's multi-instance sub-target: SYS100/SYS101 can
    each fire more than once per node (once per capability kind), so a
    `waive` clause targeting one of them must name a sub-target
    (`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`) and matching needs a
    structured field to compare against -- never parsed back out of
    `detail`'s free text."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    capability: str | None = None


# frob:doc docs/strata/selfconform.md#the-three-rules
# frob:tests tests/unit/strata/test_native_test.py::TestSummarize.test_no_gaps_reports_proved  # noqa: E501
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
class SelfConformReport(BaseModel):
    """Every UNWAIVED self-conformance violation, in rule-then-node order
    (module docstring), plus `waived` (T-0174: findings suppressed by a
    matching `waive` clause, kept here for report visibility -- never
    silently dropped, `_waive.py` module docstring). A stale waiver (its
    `(node, rule)` matched zero findings) is folded back INTO `violations`
    as a `SYSWAIVE002` entry rather than a separate field, so the existing
    `not selfconform.danger_ok.violations` gate condition (`sys_runner.py::
    _run_audit`) fails closed on drift without a second check to forget."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[SelfConformViolation, ...] = ()
    waived: tuple[SelfConformViolation, ...] = ()


