"""Unit tests for T-2923 (child of the T-2920 shrink-only ratchet epic)
SYS101 auto-tightening writer (`frob.strata._shrink`): drop a declared-
but-never-observed `may` capability atom, and ONLY that direction --
capability escalation (SYS100) and an unbound capability-bearing file
(SYS103) must both stay untouched, hard errors, with no code path here
that could ever widen or bind either."""

from __future__ import annotations

import inspect
from pathlib import Path

from frob.strata._design_load import load_design_ids
from frob.strata._selfconform import check_self_conformance
from frob.strata._selfconform_ids import (
    SYS_COVERAGE_TOTALITY,
    SYS_UNDECLARED_INTERFACE,
)
from frob.strata._shrink import apply_shrink, shrink_report
from frob.strata._sysdoc import merge_models


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _write_design(root: Path, design_dir: str, rel: str, source: str) -> Path:
    path = root / design_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


class TestShrinkReportDropsStaleGrants:
    """The one direction `frob sys shrink` is allowed to write: a
    declared `may` atom with zero observed sites anywhere in its node's
    files."""

    def test_drops_declared_but_never_observed_capability(self, tmp_path: Path):
        """A node declares `eval` but its bound file never performs it
        (a stale SYS101 grant) -- shrink drops the line, leaving every
        other declaration untouched."""
        _write(tmp_path, "api/handler.py", "def handle():\n    return 1\n")
        _write_design(
            tmp_path,
            "design",
            "api.strata",
            "module api\n"
            "node Api : trusted {\n"
            '    code "api/**";\n'
            '    may "eval" via "api/handler.py";\n'
            "}\n",
        )
        result = shrink_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.has_drift
        assert len(report.files) == 1
        f = report.files[0]
        assert f.path == "design/api.strata"
        assert len(f.drops) == 1
        assert f.drops[0].node == "Api"
        assert f.drops[0].kind == "eval"
        assert 'may "eval"' not in f.new_text
        assert 'code "api/**"' in f.new_text  # everything else preserved

    def test_no_drift_when_everything_observed(self, tmp_path: Path):
        """A node whose every declared capability has a real observed
        site reports zero drift -- shrink is a genuine no-op here."""
        _write(tmp_path, "api/net.py", "import requests\nrequests.get('x')\n")
        _write_design(
            tmp_path,
            "design",
            "api.strata",
            "module api\n"
            "node Api : trusted {\n"
            '    code "api/**";\n'
            '    may "net.connect" via "api/net.py";\n'
            "}\n",
        )
        result = shrink_report(tmp_path)
        assert result.is_ok
        assert not result.danger_ok.has_drift

    def test_partially_stale_kind_is_left_untouched(self, tmp_path: Path):
        """Two via-scoped grants for the SAME kind on one node, one
        observed and one stale: shrink must NOT guess which to drop --
        it leaves BOTH alone and records the (node, kind) as a skip."""
        _write(tmp_path, "api/used.py", "import requests\nrequests.get('x')\n")
        _write(tmp_path, "api/unused.py", "def noop():\n    return 1\n")
        _write_design(
            tmp_path,
            "design",
            "api.strata",
            "module api\n"
            "node Api : trusted {\n"
            '    code "api/**";\n'
            '    may "net.connect" via "api/used.py";\n'
            '    may "net.connect" via "api/unused.py";\n'
            "}\n",
        )
        result = shrink_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        # Whichever via-instance is stale is reported as a skip, not a drop.
        assert not report.files or not report.files[0].drops
        assert any(s.node == "Api" and s.kind == "net.connect" for s in report.skipped)

    def test_apply_shrink_writes_only_changed_files(self, tmp_path: Path):
        """`apply_shrink` writes the dropped-grant text back to disk and
        returns the relative path written; a clean report writes
        nothing."""
        _write(tmp_path, "api/handler.py", "def handle():\n    return 1\n")
        design_path = _write_design(
            tmp_path,
            "design",
            "api.strata",
            "module api\n"
            "node Api : trusted {\n"
            '    code "api/**";\n'
            '    may "eval" via "api/handler.py";\n'
            "}\n",
        )
        report = shrink_report(tmp_path).danger_ok
        written = apply_shrink(tmp_path, report)
        assert written == ("design/api.strata",)
        assert 'may "eval"' not in design_path.read_text(encoding="utf-8")

    def test_check_only_report_never_writes(self, tmp_path: Path):
        """`shrink_report` alone never touches disk -- `--check`'s whole
        job is calling this and skipping `apply_shrink`."""
        _write(tmp_path, "api/handler.py", "def handle():\n    return 1\n")
        design_path = _write_design(
            tmp_path,
            "design",
            "api.strata",
            "module api\n"
            "node Api : trusted {\n"
            '    code "api/**";\n'
            '    may "eval" via "api/handler.py";\n'
            "}\n",
        )
        before = design_path.read_text(encoding="utf-8")
        shrink_report(tmp_path)
        assert design_path.read_text(encoding="utf-8") == before


class TestShrinkNeverWidensOrBinds:
    """T-2920's own hard constraint: capability escalation (SYS100) and
    an unbound capability-bearing file (SYS103) both stay untouched,
    hard errors -- must-fire fixtures per the epic's own acceptance
    criteria."""

    # frob:tests \
    # tests/unit/strata/test_shrink.py::TestShrinkNeverWidensOrBinds.test_capability_es\
    # calation_stays_an_error_and_shrink_does_not_widen
    def test_capability_escalation_stays_an_error_and_shrink_does_not_widen(
        self, tmp_path: Path
    ):
        """MUST-FIRE fixture: a node acquires `net` it never declared.
        `check_self_conformance` (the same join every strata gate trusts)
        keeps reporting SYS100 for it, and `shrink_report` makes NO
        change to that node's declaration -- the `.strata` text is
        byte-for-byte unchanged."""
        _write(tmp_path, "api/net.py", "import requests\nrequests.get('x')\n")
        design_path = _write_design(
            tmp_path,
            "design",
            "api.strata",
            "module api\n"
            "node Api : trusted {\n"
            '    code "api/**";\n'
            "}\n",
        )
        before = design_path.read_text(encoding="utf-8")

        ids = load_design_ids(tmp_path, "design")
        model = merge_models(ids.models)
        conformance = check_self_conformance(model, tmp_path)
        assert conformance.is_ok
        assert any(
            v.rule == SYS_UNDECLARED_INTERFACE and v.node == "Api"
            for v in conformance.danger_ok.violations
        )

        result = shrink_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not report.has_drift
        assert design_path.read_text(encoding="utf-8") == before

    # frob:tests \
    # tests/unit/strata/test_shrink.py::TestShrinkNeverWidensOrBinds.test_unbound_capab\
    # ility_file_stays_an_error_and_shrink_does_not_bind_it
    def test_unbound_capability_file_stays_an_error_and_shrink_does_not_bind_it(
        self, tmp_path: Path
    ):
        """MUST-FIRE fixture: a capability-bearing file no node's `code=`
        glob binds. `check_self_conformance` keeps reporting SYS103 for
        it, and `shrink_report` never invents a binding -- it has no
        branch that could even attempt one (`_stale_counts_by_node_kind`
        only ever looks at SYS_STALE_DESIGN findings, never
        SYS_COVERAGE_TOTALITY)."""
        _write(tmp_path, "orphan/_io.py", "import requests\nrequests.get('x')\n")
        design_path = _write_design(
            tmp_path,
            "design",
            "api.strata",
            "module api\n"
            "node Api : trusted {\n"
            '    code "api/**";\n'
            "}\n",
        )
        before = design_path.read_text(encoding="utf-8")

        ids = load_design_ids(tmp_path, "design")
        model = merge_models(ids.models)
        conformance = check_self_conformance(model, tmp_path)
        assert conformance.is_ok
        assert any(
            v.rule == SYS_COVERAGE_TOTALITY and "orphan" in v.node
            for v in conformance.danger_ok.violations
        )

        result = shrink_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not report.has_drift
        assert design_path.read_text(encoding="utf-8") == before
        # No node anywhere gained a code= glob covering the orphan file.
        assert "orphan" not in design_path.read_text(encoding="utf-8")


class TestNoWideningPath:
    """T-2920's hard constraint, proved against the actual module
    surface: no flag, env var, or config key on this module's public API
    can ever WIDEN a node's declared capability surface. This is scoped
    HONESTLY to what this ticket built -- it does NOT, and must not
    claim to, prove `frob.strata._sync_may`'s pre-existing widening
    functions are unreachable (T-2922, blocking the parent epic, is the
    ticket that unwires their caller; this module never imports or calls
    them)."""

    def test_module_has_no_widen_or_bind_named_symbol(self):
        """No public or private symbol in this module is named in a way
        that suggests a widening/binding operation -- a purely
        structural check that the surface itself carries no such
        capability, not a claim about the whole repo."""
        import frob.strata._shrink as shrink_mod

        names = [n for n in dir(shrink_mod) if not n.startswith("__")]
        forbidden_substrings = ("widen", "bind_file", "add_grant", "escalate")
        offending = [
            n
            for n in names
            if any(bad in n.lower() for bad in forbidden_substrings)
        ]
        assert offending == []

    def test_shrink_report_signature_has_no_widening_parameter(self):
        """`shrink_report`'s full parameter list is `(root, design_dir)`
        -- no flag/env-var-shaped parameter exists that could plausibly
        gate a widening branch. A future parameter here would need a
        new test asserting what it does NOT do."""
        sig = inspect.signature(shrink_report)
        assert list(sig.parameters) == ["root", "design_dir"]

    def test_apply_shrink_signature_has_no_widening_parameter(self):
        """Same check for `apply_shrink`: `(root, report)` only."""
        sig = inspect.signature(apply_shrink)
        assert list(sig.parameters) == ["root", "report"]

    def test_this_module_never_imports_sync_may_widening_functions(self):
        """This module must never IMPORT `_sync_may`'s widening surface
        -- doing so would create exactly the reachable-widening-through-
        shrink path T-2920 forbids. `node_body_span` (a pure brace-depth
        scanner shared read-only helper, T-1895) is the ONLY `_sync_may`
        import this module is allowed to carry. Parsed via `ast` against
        the real `ImportFrom` nodes, never a substring/regex scan of the
        source text -- a lexical scan would also match this module's OWN
        docstring, which names those functions in prose while importing
        none of them (the exact false-positive a token/grammar check
        avoids, this repo's own standing lexical-vs-grammar rule)."""
        import ast

        import frob.strata._shrink as shrink_mod

        tree = ast.parse(inspect.getsource(shrink_mod))
        forbidden = {
            "sync_may_report",
            "apply_sync_may",
            "sync_may_extended_report",
            "apply_sync_may_extended",
        }
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "_sync_may":
                imported.update(alias.name for alias in node.names)
        assert imported == {"node_body_span"}
        assert not (imported & forbidden)
