"""Unit tests for `frob.arch._srp` (T-0616): the ARCH1xx SRP/cohesion family
(LCOM4 low-cohesion class, god-module, mixed-concern function), written once
against `frob.arch._normalized.NormalizedModule` (T-0609) so each check is
proven to fire across MULTIPLE `LanguageAdapter`s, not just python -- kept
in its own file per T-0616's coordination note (T-0615/T-0617 concurrently
touch `tests/unit/test_arch.py`).
"""

from __future__ import annotations

from pathlib import Path

from frob.arch._normalized import (
    NormalizedClass,
    NormalizedField,
    NormalizedFieldAccess,
    NormalizedFunction,
    NormalizedModule,
)
from frob.arch._srp import (
    check_god_module,
    check_lcom4,
    check_mixed_concern_function,
    run_srp_checks,
)


def _method(name: str, field_names: list[str]) -> NormalizedFunction:
    """A minimal `NormalizedFunction` method that reads each name in
    `field_names` as a `self.<name>` field access, for hand-building LCOM4
    fixtures without needing a real parse."""
    return NormalizedFunction(
        name=name,
        line=1,
        body_line_count=3,
        is_method=True,
        field_accesses=[NormalizedFieldAccess(name=n, line=1) for n in field_names],
    )


class TestLcom4:
    """ARCH101."""

    def test_disjoint_field_groups_trigger_lcom4(self) -> None:
        cls = NormalizedClass(
            name="BigService",
            line=1,
            fields=[
                NormalizedField(name="conn", line=1),
                NormalizedField(name="cache", line=1),
                NormalizedField(name="report_title", line=1),
                NormalizedField(name="report_footer", line=1),
            ],
            methods=[
                _method("connect", ["conn"]),
                _method("query", ["conn", "cache"]),
                _method("invalidate_cache", ["cache"]),
                _method("render_title", ["report_title"]),
                _method("render_footer", ["report_footer", "report_title"]),
                _method("no_fields_here", []),
            ],
        )
        module = NormalizedModule(
            path="big_service.py", language="python", classes=[cls]
        )
        out: list = []
        check_lcom4(module, out)
        assert len(out) == 1
        s = out[0]
        assert s.category == "low-cohesion-class"
        assert s.severity == "warning"
        assert s.symref == "BigService"
        assert s.metric == 2
        assert "BigService" in s.message

    def test_shared_fields_do_not_trigger_lcom4(self) -> None:
        cls = NormalizedClass(
            name="CohesiveService",
            line=1,
            fields=[NormalizedField(name="conn", line=1)],
            methods=[
                _method("connect", ["conn"]),
                _method("query", ["conn"]),
                _method("close", ["conn"]),
                _method("reconnect", ["conn"]),
                _method("ping", ["conn"]),
                _method("status", ["conn"]),
            ],
        )
        module = NormalizedModule(
            path="cohesive_service.py", language="python", classes=[cls]
        )
        out: list = []
        check_lcom4(module, out)
        assert out == []

    def test_below_min_methods_not_considered(self) -> None:
        cls = NormalizedClass(
            name="Tiny",
            line=1,
            methods=[
                _method("a", ["x"]),
                _method("b", ["y"]),
            ],
        )
        module = NormalizedModule(path="tiny.py", language="python", classes=[cls])
        out: list = []
        check_lcom4(module, out)
        assert out == []


def _free_function(name: str, calls: list[str] | None = None) -> NormalizedFunction:
    """A minimal top-level `NormalizedFunction` with the given call callees,
    for hand-building god-module fixtures."""
    from frob.arch._normalized import NormalizedCall

    return NormalizedFunction(
        name=name,
        line=1,
        body_line_count=3,
        calls=[NormalizedCall(callee=c, line=1) for c in (calls or [])],
    )


class TestGodModule:
    """ARCH102."""

    def test_unrelated_export_clusters_trigger_god_module(self) -> None:
        functions = (
            [_free_function(f"user_{i}") for i in range(4)]
            + [_free_function(f"billing_{i}") for i in range(4)]
            + [_free_function(f"report_{i}") for i in range(4)]
        )
        module = NormalizedModule(
            path="everything.py", language="python", functions=functions
        )
        out: list = []
        check_god_module(module, out)
        assert len(out) == 1
        s = out[0]
        assert s.category == "god-module"
        assert s.severity == "warning"
        assert s.metric is not None and s.metric >= 3

    def test_related_exports_do_not_trigger_god_module(self) -> None:
        # Same naming prefix ("user_") across all exports -> one cluster,
        # regardless of count.
        functions = [_free_function(f"user_{i}") for i in range(12)]
        module = NormalizedModule(
            path="user_ops.py", language="python", functions=functions
        )
        out: list = []
        check_god_module(module, out)
        assert out == []

    def test_usage_edges_merge_clusters_despite_different_prefixes(self) -> None:
        # "alpha" and "beta" have different naming prefixes but "alpha_main"
        # calls "beta_helper" directly -- the usage edge must merge them
        # into one cluster, so only 2 real clusters remain (below the
        # default min_clusters=3 threshold) despite 3 naming groups.
        functions = (
            [_free_function("alpha_main", calls=["beta_helper"])]
            + [_free_function(f"alpha_{i}") for i in range(3)]
            + [_free_function("beta_helper")]
            + [_free_function(f"beta_{i}") for i in range(3)]
            + [_free_function(f"gamma_{i}") for i in range(4)]
        )
        module = NormalizedModule(
            path="merged.py", language="python", functions=functions
        )
        out: list = []
        check_god_module(module, out, min_exports=5, min_clusters=3)
        assert out == []


class TestMixedConcernFunction:
    """ARCH103."""

    def test_io_compute_and_formatting_together_trigger(self) -> None:
        from frob.arch._normalized import NormalizedBranch, NormalizedCall

        func = NormalizedFunction(
            name="build_report",
            line=10,
            body_line_count=20,
            calls=[
                NormalizedCall(callee="open", line=11),
                NormalizedCall(callee="title.format", line=15),
            ],
            branches=[
                NormalizedBranch(line=12, condition_text="x > 0"),
                NormalizedBranch(line=13, condition_text="y < 0"),
            ],
        )
        module = NormalizedModule(path="report.py", language="python", functions=[func])
        out: list = []
        check_mixed_concern_function(module, out)
        assert len(out) == 1
        s = out[0]
        assert s.category == "mixed-concern-function"
        assert s.severity == "suggestion"
        assert s.symref == "build_report"

    def test_single_concern_does_not_trigger(self) -> None:
        from frob.arch._normalized import NormalizedBranch, NormalizedCall

        # I/O and compute, but no formatting call -- must not trigger.
        func = NormalizedFunction(
            name="read_only",
            line=10,
            body_line_count=20,
            calls=[NormalizedCall(callee="open", line=11)],
            branches=[
                NormalizedBranch(line=12, condition_text="x > 0"),
                NormalizedBranch(line=13, condition_text="y < 0"),
            ],
        )
        module = NormalizedModule(path="reader.py", language="python", functions=[func])
        out: list = []
        check_mixed_concern_function(module, out)
        assert out == []


class TestRunSrpChecks:
    def test_empty_module_produces_no_suggestions(self) -> None:
        module = NormalizedModule(path="empty.py", language="python")
        assert run_srp_checks(module) == []

    def test_combines_all_three_checks(self) -> None:
        from frob.arch._normalized import NormalizedBranch, NormalizedCall

        cls = NormalizedClass(
            name="BigService",
            line=1,
            methods=[
                _method("connect", ["conn"]),
                _method("query", ["conn", "cache"]),
                _method("invalidate_cache", ["cache"]),
                _method("render_title", ["report_title"]),
                _method("render_footer", ["report_footer", "report_title"]),
                _method("no_fields_here", []),
            ],
        )
        mixed_func = NormalizedFunction(
            name="build_report",
            line=10,
            body_line_count=20,
            calls=[
                NormalizedCall(callee="open", line=11),
                NormalizedCall(callee="title.format", line=15),
            ],
            branches=[
                NormalizedBranch(line=12, condition_text="x > 0"),
                NormalizedBranch(line=13, condition_text="y < 0"),
            ],
        )
        module = NormalizedModule(
            path="mixed.py",
            language="python",
            classes=[cls],
            functions=[mixed_func],
        )
        suggestions = run_srp_checks(module)
        categories = {s.category for s in suggestions}
        assert categories == {"low-cohesion-class", "mixed-concern-function"}


# ---------------------------------------------------------------------------
# Cross-language proof (T-0616's coordination requirement): the same check
# functions fire identically over a NormalizedModule built by a NON-python
# LanguageAdapter -- TypeScriptAdapter here -- with no per-language branch
# in `frob.arch._srp` itself.
# ---------------------------------------------------------------------------


class TestCrossLanguage:
    def _ts_module(self, tmp_path: Path, source: str) -> NormalizedModule:
        from frob.arch._typescript import TypeScriptAdapter
        from frob.lang import raw_tree

        path = tmp_path / "mod.ts"
        path.write_text(source)
        parsed = raw_tree(path)
        assert parsed.is_ok
        tree, src, language = parsed.danger_ok
        assert language == "typescript"
        return TypeScriptAdapter().adapt(tree, src, "mod.ts")

    def test_lcom4_fires_on_typescript_adapter_output(self, tmp_path: Path) -> None:
        source = (
            "class BigService {\n"
            '  conn: string = "";\n'
            '  cache: string = "";\n'
            '  title: string = "";\n'
            '  footer: string = "";\n'
            '  connect() { this.conn = "x"; }\n'
            "  query() { this.conn = this.cache; }\n"
            '  invalidateCache() { this.cache = ""; }\n'
            '  renderTitle() { this.title = ""; }\n'
            "  renderFooter() { this.footer = this.title; }\n"
            "  noop() { return 1; }\n"
            "}\n"
        )
        module = self._ts_module(tmp_path, source)
        assert module.language == "typescript"
        out: list = []
        check_lcom4(module, out)
        assert len(out) == 1
        assert out[0].category == "low-cohesion-class"
        assert out[0].metric == 2

    def test_lcom4_does_not_fire_on_cohesive_typescript_class(
        self, tmp_path: Path
    ) -> None:
        source = (
            "class CohesiveService {\n"
            '  conn: string = "";\n'
            '  connect() { this.conn = "a"; }\n'
            "  query() { this.conn = this.conn; }\n"
            '  close() { this.conn = ""; }\n'
            '  reconnect() { this.conn = "b"; }\n'
            "  ping() { this.conn = this.conn; }\n"
            "  status() { this.conn = this.conn; }\n"
            "}\n"
        )
        module = self._ts_module(tmp_path, source)
        out: list = []
        check_lcom4(module, out)
        assert out == []
