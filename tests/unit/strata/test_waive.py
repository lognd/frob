"""Direct unit coverage for `_waive.py`'s pure helpers (T-0174): the shared
`_stale_detail` message formatter, and (T-0174 REJECT round)
`_split_waiver_rule`/`_validate_waiver_fields`, the sub-target grammar and
mandatory-reason validation both `_elaborate.py` and `apply_waivers` rely
on, tested in isolation from either caller."""

from __future__ import annotations

from datetime import date

from frob.strata._errors import StrataError
from frob.strata._waive import (
    MULTI_INSTANCE_WAIVER_FAMILIES,
    WaiverMatch,
    _split_waiver_rule,
    _stale_detail,
    _validate_waiver_fields,
    parse_waiver_expiry,
    stale_relwaive_violations,
)


class _DummyViolation:
    """Minimal stand-in for a strata violation `BaseModel` (T-1938): only
    what `stale_relwaive_violations` writes into it, so this test does not
    depend on any one real family's dataclass shape."""

    def __init__(self, *, rule: str, node: str, sub_target: str | None, detail: str):
        self.rule = rule
        self.node = node
        self.sub_target = sub_target
        self.detail = detail


class TestStaleDetail:
    # frob:tests src/frob/strata/_waive.py::_stale_detail kind="unit"
    def test_names_rule_node_and_reason(self):
        match = WaiverMatch(
            node="checker", rule="LINT004", reason="pending T-0200", ticket="T-0200"
        )
        detail = _stale_detail(match)
        assert "LINT004" in detail
        assert "checker" in detail
        assert "pending T-0200" in detail
        assert "stale" in detail


class TestStaleRelwaiveViolations:
    # frob:tests src/frob/strata/_waive.py::stale_relwaive_violations kind="unit"
    def test_builds_one_violation_per_stale_waiver(self):
        stale = (
            WaiverMatch(node="n1", rule="REL260", reason="pending T-1"),
            WaiverMatch(node="n2", rule="REL261", reason="pending T-2"),
        )
        result = stale_relwaive_violations(stale, _DummyViolation)
        assert len(result) == 2
        assert result[0].rule == "RELWAIVE002"
        assert result[0].node == "n1"
        assert result[0].sub_target == "REL260"
        assert result[1].node == "n2"
        assert result[1].sub_target == "REL261"

    # frob:tests src/frob/strata/_waive.py::stale_relwaive_violations kind="unit"
    def test_uses_stale_detail_message(self):
        match = WaiverMatch(node="n1", rule="REL260", reason="pending T-1")
        result = stale_relwaive_violations((match,), _DummyViolation)
        assert result[0].detail == _stale_detail(match)

    # frob:tests src/frob/strata/_waive.py::stale_relwaive_violations kind="unit"
    def test_empty_stale_yields_empty_tuple(self):
        assert stale_relwaive_violations((), _DummyViolation) == ()

    # frob:tests src/frob/strata/_waive.py::stale_relwaive_violations kind="unit"
    def test_factory_lambda_can_add_extra_fields(self):
        match = WaiverMatch(node="n1", rule="REL260", reason="pending T-3")
        made = stale_relwaive_violations(
            (match,), lambda **kw: _DummyViolation(**kw)
        )
        assert made[0].rule == "RELWAIVE002"


class TestSplitWaiverRule:
    # frob:tests src/frob/strata/_waive.py::_split_waiver_rule kind="unit"
    def test_bare_rule_has_no_sub_target(self):
        assert _split_waiver_rule("LINT004") == ("LINT004", None)

    # frob:tests src/frob/strata/_waive.py::_split_waiver_rule kind="unit"
    def test_qualified_rule_splits_on_first_colon(self):
        assert _split_waiver_rule("SYS100:fs-write") == ("SYS100", "fs-write")

    # frob:tests src/frob/strata/_waive.py::_split_waiver_rule kind="unit"
    def test_cwe_sub_target_with_its_own_dash(self):
        assert _split_waiver_rule("THREAT003:CWE-78") == ("THREAT003", "CWE-78")

    # frob:tests src/frob/strata/_waive.py::_split_waiver_rule kind="unit"
    def test_trailing_colon_with_nothing_after_it_is_no_sub_target(self):
        assert _split_waiver_rule("SYS100:") == ("SYS100", None)

    # frob:tests src/frob/strata/_waive.py::_split_waiver_rule kind="unit"
    def test_whitespace_only_after_colon_is_no_sub_target(self):
        assert _split_waiver_rule("SYS100:   ") == ("SYS100", None)


class TestValidateWaiverFields:
    # frob:tests src/frob/strata/_waive.py::_validate_waiver_fields kind="unit"
    def test_bare_single_instance_rule_with_reason_is_ok(self):
        assert _validate_waiver_fields("LINT004", "a real reason").is_ok

    # frob:tests src/frob/strata/_waive.py::_validate_waiver_fields kind="unit"
    def test_qualified_multi_instance_rule_with_reason_is_ok(self):
        assert _validate_waiver_fields("SYS100:fs-write", "a real reason").is_ok

    # frob:tests src/frob/strata/_waive.py::_validate_waiver_fields kind="unit"
    def test_empty_reason_rejected(self):
        result = _validate_waiver_fields("LINT004", "")
        assert result.is_err
        assert result.danger_err is StrataError.MalformedWaiver

    # frob:tests src/frob/strata/_waive.py::_validate_waiver_fields kind="unit"
    def test_whitespace_reason_rejected(self):
        result = _validate_waiver_fields("LINT004", "   \t  ")
        assert result.is_err
        assert result.danger_err is StrataError.MalformedWaiver

    # frob:tests src/frob/strata/_waive.py::_validate_waiver_fields kind="unit"
    def test_bare_multi_instance_rule_rejected(self):
        result = _validate_waiver_fields("THREAT003", "a real reason")
        assert result.is_err
        assert result.danger_err is StrataError.MalformedWaiver

    # frob:tests src/frob/strata/_waive.py::_validate_waiver_fields kind="unit"
    def test_every_multi_instance_family_requires_sub_target(self):
        for family in sorted(MULTI_INSTANCE_WAIVER_FAMILIES):
            result = _validate_waiver_fields(family, "a real reason")
            assert result.is_err, f"{family} should require a sub-target"
            result_qualified = _validate_waiver_fields(f"{family}:x", "a real reason")
            assert result_qualified.is_ok, f"{family}:x should elaborate cleanly"


class TestConformanceWaiverExpiry:
    """T-0671: `parse_waiver_expiry` extracts an `expires:YYYY-MM-DD`
    marker embedded in a waiver's `reason` string."""

    # frob:tests src/frob/strata/_waive.py::parse_waiver_expiry kind="unit"
    def test_parses_embedded_expiry_date(self):
        assert parse_waiver_expiry("a real reason, expires:2026-12-31") == date(
            2026, 12, 31
        )

    # frob:tests src/frob/strata/_waive.py::parse_waiver_expiry kind="unit"
    def test_no_marker_returns_none(self):
        assert parse_waiver_expiry("a real reason with no date") is None

    # frob:tests src/frob/strata/_waive.py::parse_waiver_expiry kind="unit"
    def test_malformed_date_returns_none(self):
        assert parse_waiver_expiry("a real reason, expires:2026-13-40") is None
