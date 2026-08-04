"""Unit tests for frob.strata._multifile (T-1196)."""

from __future__ import annotations

from frob.strata._errors import StrataError
from frob.strata._multifile import (
    check_cross_file_references,
    elaborate_merged,
    merge_modules,
)
from frob.strata._parse import parse_module


def _test_module(text: str):
    parsed = parse_module(text)
    assert parsed.is_ok
    return parsed.danger_ok


class TestCheckCrossFileReferences:
    # frob:tests \
    # tests/unit/strata/test_multifile.py::TestCheckCrossFileReferences.test_no_errors_\
    # when_all_resolve
    def test_no_errors_when_all_resolve(self) -> None:
        """A flow whose src/dst nodes live in a DIFFERENT file is not an
        error -- the whole point of the cross-file join (T-1196)."""
        a = _test_module(
            "module a\nnode client : foreign { clearance Public; }\n"
            "node api : authenticated { clearance Internal; }\n"
        )
        b = _test_module("module b\nflow f_login : client -> api\n")
        errors = check_cross_file_references((("a.strata", a), ("b.strata", b)))
        assert errors == ()

    # frob:tests \
    # tests/unit/strata/test_multifile.py::TestCheckCrossFileReferences.test_missing_no\
    # de_named_per_file
    def test_missing_node_named_per_file(self) -> None:
        """An unresolvable flow src/dst is reported against the file that
        declared the flow, naming the missing id (T-1196 acceptance 1)."""
        b = _test_module("module b\nflow f_ghost : nobody -> nowhere\n")
        errors = check_cross_file_references((("b.strata", b),))
        assert len(errors) == 2
        assert all(e.path == "b.strata" for e in errors)
        assert any("nobody" in e.message for e in errors)
        assert any("nowhere" in e.message for e in errors)

    # frob:tests \
    # tests/unit/strata/test_multifile.py::TestCheckCrossFileReferences.test_boundary_u\
    # nknown_flow_named
    def test_boundary_unknown_flow_named(self) -> None:
        """A boundary naming an unknown flow id is reported the same way."""
        a = _test_module(
            'module a\nboundary b_x endorse f_missing : Public -> Internal when "ok"\n'
        )
        errors = check_cross_file_references((("a.strata", a),))
        assert len(errors) == 1
        assert errors[0].path == "a.strata"
        assert "f_missing" in errors[0].message


class TestMergeModules:
    # frob:tests \
    # tests/unit/strata/test_multifile.py::TestMergeModules.test_concatenates_declarati\
    # ons
    def test_concatenates_declarations(self) -> None:
        """Every declaration from every file lands in the merged `Module`."""
        a = _test_module("module a\nnode client : foreign { clearance Public; }\n")
        b = _test_module("module b\nnode api : authenticated { clearance Internal; }\n")
        merged = merge_modules((("a.strata", a), ("b.strata", b)))
        assert {n.id for n in merged.nodes} == {"client", "api"}


class TestElaborateMerged:
    # frob:tests \
    # tests/unit/strata/test_multifile.py::TestElaborateMerged.test_resolves_cross_file\
    # _flow
    def test_resolves_cross_file_flow(self) -> None:
        """`elaborate_merged` produces one `KernelModel` where a cross-file
        flow reference resolves (T-1196 acceptance 0)."""
        a = _test_module(
            "module a\nnode client : foreign { clearance Public; }\n"
            "node api : authenticated { clearance Internal; }\n"
        )
        b = _test_module("module b\nflow f_login : client -> api\n")
        result = elaborate_merged((("a.strata", a), ("b.strata", b)))
        assert result.is_ok
        assert {f.id for f in result.danger_ok.flows} == {"f_login"}

    # frob:tests \
    # tests/unit/strata/test_multifile.py::TestElaborateMerged.test_fails_closed_on_mis\
    # sing_id
    def test_fails_closed_on_missing_id(self) -> None:
        """A reference to an id declared nowhere fails closed, never a
        partial model (T-1196 acceptance 1)."""
        b = _test_module("module b\nflow f_ghost : nobody -> nowhere\n")
        result = elaborate_merged((("b.strata", b),))
        assert result.is_err
        assert all(e.path == "b.strata" for e in result.danger_err)
        assert all(e.error is StrataError.UnknownReference for e in result.danger_err)
