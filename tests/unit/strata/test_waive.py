"""Direct unit coverage for `_waive.py`'s pure helpers (T-0174): the shared
`_stale_detail` message formatter, and (T-0174 REJECT round)
`_split_waiver_rule`/`_validate_waiver_fields`, the sub-target grammar and
mandatory-reason validation both `_elaborate.py` and `apply_waivers` rely
on, tested in isolation from either caller."""

from __future__ import annotations

from frob.strata._errors import StrataError
from frob.strata._waive import (
    MULTI_INSTANCE_WAIVER_FAMILIES,
    WaiverMatch,
    _split_waiver_rule,
    _stale_detail,
    _validate_waiver_fields,
)


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
