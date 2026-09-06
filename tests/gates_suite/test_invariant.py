from pathlib import Path

import pytest

from frob.gates import (
    Severity,
    coverage_gate,
    env_var_doc_gate,
    exclude_hazard_gate,
    inv003_gate,
    inv004_gate,
    invariant_gate,
    root_asset_dir_gate,
)
from frob.gates.invariants import (
    InvariantError,
    InvariantLoadError,
    _Criticality,
    load_invariants,
)
from frob.gitio import Diff
from frob.testing import CollectedTests
from frob.tickets import TicketQueue
from tests.conftest import (
    _first_rule,
    _git_init,
    _snapshot,
    _write,
)


# frob:ticket T-0543
class TestInvariantGate:
    def test_inv001_no_evidence(self, tmp_path: Path) -> None:
        from frob.gates.invariants import Invariant

        snap = _snapshot(tmp_path)
        inv = Invariant(
            id="INV-001", statement="x", criticality=_Criticality.HIGH, evidence=()
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = invariant_gate((inv,), snap, tests)
        assert any(v.rule == "INV001" for v in violations)

    def test_inv001_uncollected_node_id(self, tmp_path: Path) -> None:
        from frob.gates.invariants import Invariant

        snap = _snapshot(tmp_path)
        inv = Invariant(
            id="INV-001",
            statement="x",
            criticality=_Criticality.HIGH,
            evidence=("tests/test_x.py::test_y",),
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = invariant_gate((inv,), snap, tests)
        assert any(v.rule == "INV001" for v in violations)

    # frob:tests src/frob/gates/_inv.py::invariant_gate
    # frob:ticket T-0543
    def test_inv001_passes_with_collected_evidence(self, tmp_path: Path) -> None:
        """The evidence test lives in the SAME FILE as the invariant's
        anchor (B12's same-file binding route) -- a genuine binding, not
        merely a collected node id."""
        source = (
            "def f(x):\n"
            "    # frob:invariant INV-001\n"
            "    return x\n"
            "\n"
            "def test_y():\n"
            "    assert f(1) == 1\n"
        )
        _write(tmp_path, "tests/test_x.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates.invariants import Invariant

        node = "tests/test_x.py::test_y"
        inv = Invariant(
            id="INV-001", statement="x", criticality=_Criticality.HIGH, evidence=(node,)
        )
        tests = CollectedTests(node_ids=frozenset({node}))
        violations = invariant_gate((inv,), snap, tests)
        assert violations == ()

    # frob:tests src/frob/gates/_inv.py::_invariant_evidence_proves_anchor
    # frob:ticket T-0543
    def test_inv001_collected_but_unbound_evidence_warns_inv005(
        self, tmp_path: Path
    ) -> None:
        """B12 counterexample: a collected test node id that has NO edge
        to, and lives in a different file than, the invariant's anchor
        used to clear INV001 by mere existence (`def test_y(): pass`
        anywhere in the repo). It still passes INV001 (a legacy-adoption
        mass-break across this repo's own invariants is out of budget --
        see `invariant_gate`'s docstring) but now WARNs via the new INV005
        instead of silently proving nothing."""
        source = "def f(x):\n    # frob:invariant INV-001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        _write(tmp_path, "tests/test_unrelated.py", "def test_y():\n    pass\n")
        snap = _snapshot(tmp_path)
        from frob.gates.invariants import Invariant

        node = "tests/test_unrelated.py::test_y"
        inv = Invariant(
            id="INV-001", statement="x", criticality=_Criticality.HIGH, evidence=(node,)
        )
        tests = CollectedTests(node_ids=frozenset({node}))
        violations = invariant_gate((inv,), snap, tests)
        assert not any(v.rule == "INV001" for v in violations)
        assert any(v.rule == "INV005" for v in violations)

    # frob:tests src/frob/gates/_inv.py::_evidence_binds_to_symrefs
    # frob:ticket T-0543
    def test_inv001_passes_via_explicit_tests_edge_to_anchor(
        self, tmp_path: Path
    ) -> None:
        """B12: an evidence test bound to the anchor via an explicit
        `frob:tests` edge (not merely same-file) also satisfies INV001."""
        source = "def f(x):\n    # frob:invariant INV-001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        _write(
            tmp_path,
            "tests/test_a.py",
            "# frob:tests src/a.py::f\ndef test_f():\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        from frob.gates.invariants import Invariant

        node = "tests/test_a.py::test_f"
        inv = Invariant(
            id="INV-001", statement="x", criticality=_Criticality.HIGH, evidence=(node,)
        )
        tests = CollectedTests(node_ids=frozenset({node}))
        violations = invariant_gate((inv,), snap, tests)
        assert violations == ()

    def test_inv002_no_anchor(self, tmp_path: Path) -> None:
        from frob.gates.invariants import Invariant

        snap = _snapshot(tmp_path)
        node = "tests/test_x.py::test_y"
        inv = Invariant(
            id="INV-001", statement="x", criticality=_Criticality.HIGH, evidence=(node,)
        )
        tests = CollectedTests(node_ids=frozenset({node}))
        violations = invariant_gate((inv,), snap, tests)
        assert any(v.rule == "INV002" for v in violations)

    def test_inv001_evidence_via_policy_rule_id(self, tmp_path: Path) -> None:
        from frob.gates.invariants import Invariant

        snap = _snapshot(tmp_path)
        inv = Invariant(
            id="INV-001",
            statement="x",
            criticality=_Criticality.HIGH,
            evidence=("POL-thing",),
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = invariant_gate((inv,), snap, tests, frozenset({"POL-thing"}))
        assert not any(v.rule == "INV001" for v in violations)


class TestInv003Gate:
    # frob:tests src/frob/gates/_inv.py::inv003_gate
    def test_exclusivity_claim_without_marker_warns(self, tmp_path: Path) -> None:
        # T-0509: INV003 is scoped to INV003_SPEC_DIRS (docs/modules,
        # docs/strata), not all of docs/**.md -- fixture must live there.
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\nThe only writer of this file is the daemon.\n",
        )
        violations = inv003_gate(tmp_path, ())
        assert len(violations) == 1
        assert violations[0].rule == "INV003"
        assert violations[0].severity == Severity.WARN
        assert violations[0].file == "docs/modules/x.md"

    def test_exclusivity_claim_with_bound_known_invariant_is_silent(
        self, tmp_path: Path
    ) -> None:
        from frob.gates.invariants import Invariant

        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\n<!-- frob:invariant INV-001 -->\n"
            "The only writer of this file is the daemon.\n",
        )
        inv = Invariant(
            id="INV-001", statement="x", criticality=_Criticality.HIGH, evidence=()
        )
        violations = inv003_gate(tmp_path, (inv,))
        assert violations == ()

    def test_marker_naming_unknown_invariant_still_warns(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\n<!-- frob:invariant INV-999 -->\n"
            "The only writer of this file is the daemon.\n",
        )
        violations = inv003_gate(tmp_path, ())
        assert len(violations) == 1

    def test_no_exclusivity_language_is_silent(self, tmp_path: Path) -> None:
        _write(tmp_path, "docs/modules/x.md", "# X\n\nThe daemon writes this file.\n")
        violations = inv003_gate(tmp_path, ())
        assert violations == ()

    def test_missing_docs_dir_is_silent(self, tmp_path: Path) -> None:
        assert inv003_gate(tmp_path, ()) == ()

    def test_claim_without_verb_in_sentence_is_silent(self, tmp_path: Path) -> None:
        """T-0509: a bare heading/fragment containing the trigger word but
        no claim-verb in the same sentence is not a claim (e.g. a
        '## Schema' style heading, or a dangling noun phrase)."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\n## Only child nodes\n\nSee below.\n",
        )
        assert inv003_gate(tmp_path, ()) == ()

    def test_claim_in_code_fence_is_silent(self, tmp_path: Path) -> None:
        """T-0509: `_strip_markdown_noise` drops fenced code before
        scanning -- a code sample using "only" in a comment is not prose."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\n```python\n# only the daemon is allowed to write here\n```\n",
        )
        assert inv003_gate(tmp_path, ()) == ()

    def test_outside_spec_dirs_is_silent(self, tmp_path: Path) -> None:
        """T-0509: INV003 is scoped to `INV003_SPEC_DIRS`
        (docs/modules, docs/strata) -- a claim in another docs/ subtree
        (e.g. docs/design) is out of scope for this gate."""
        _write(
            tmp_path,
            "docs/design/x.md",
            "# X\n\nThe only writer of this file is the daemon.\n",
        )
        assert inv003_gate(tmp_path, ()) == ()

    def test_markdown_waive_marker_with_reason_is_silent(self, tmp_path: Path) -> None:
        """T-0509: a `<!-- frob:waive INV003 reason="..." -->` marker
        dispositions a genuine-but-unprovable exclusivity claim without
        requiring a fake bound invariant."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            '# X\n\n<!-- frob:waive INV003 reason="design intent, not enforced" -->\n'
            "The only writer of this file is the daemon.\n",
        )
        assert inv003_gate(tmp_path, ()) == ()

    def test_markdown_waive_marker_without_reason_still_warns(
        self, tmp_path: Path
    ) -> None:
        """T-0509: a waiver marker with no `reason=` is not honored --
        same honesty requirement as the code-side `frob:waive` WAIVE001."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\n<!-- frob:waive INV003 -->\n"
            "The only writer of this file is the daemon.\n",
        )
        violations = inv003_gate(tmp_path, ())
        assert len(violations) == 1

    def test_illustrative_example_reason_does_not_self_waive(
        self, tmp_path: Path
    ) -> None:
        """T-0522: gates.md's OWN INV003 documentation necessarily spells
        out the marker syntax by illustrative example, using a literal
        `reason="..."` placeholder -- this must not be mistaken for a
        real, reasoned waiver of that same file's genuine findings. Uses
        the exact example text from docs/modules/gates.md."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\nMarkdown-side `frob:waive` support: "
            '`<!-- frob:waive INV003 reason="..." -->` anywhere in a file '
            "dispositions that file's INV003 findings.\n\n"
            "The only writer of this file is the daemon.\n",
        )
        violations = inv003_gate(tmp_path, ())
        assert len(violations) == 1


class TestInv004Gate:
    # frob:tests src/frob/gates/_inv.py::inv004_gate
    def test_section_with_normative_language_and_no_invariant_is_advisory(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\nThe daemon must never write to this file directly.\n",
        )
        violations = inv004_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "INV004"
        assert violations[0].severity == Severity.WARN
        assert violations[0].file == "docs/modules/x.md"

    def test_section_with_any_invariant_marker_is_silent(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\n<!-- frob:invariant INV-999 -->\n"
            "The daemon must never write to this file directly.\n",
        )
        # A marker naming an UNKNOWN invariant still counts here (T-0452's
        # signal is "anchors zero invariants at all", the coarser inverse
        # of INV003's "anchors a REAL one").
        violations = inv004_gate(tmp_path)
        assert violations == ()

    def test_section_with_no_normative_language_is_silent(self, tmp_path: Path) -> None:
        _write(tmp_path, "docs/modules/x.md", "# X\n\nThe daemon writes this file.\n")
        assert inv004_gate(tmp_path) == ()

    def test_two_sections_only_flags_the_underspecified_one(
        self, tmp_path: Path
    ) -> None:
        """T-0515: file-granularity -- two claim-bearing, unbound sections
        in the same file produce ONE advisory, not one per section (the
        T-0452 per-section scan was the source of most of the 573-warning
        pool this ticket burned down)."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# A\n\nThe daemon must never write to this file directly.\n"
            "# B\n\nThis section always holds too.\n",
        )
        violations = inv004_gate(tmp_path)
        assert len(violations) == 1
        assert "'# A" in violations[0].message

    def test_any_bound_invariant_anywhere_in_file_silences_every_section(
        self, tmp_path: Path
    ) -> None:
        """T-0515: file-granularity means a marker in section B silences
        an unbound claim in section A too -- the file as a whole is no
        longer "anchors zero invariants"."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# A\n\nThe daemon must never write to this file directly.\n"
            "# B\n\n<!-- frob:invariant INV-001 -->\n"
            "This section always holds too.\n",
        )
        assert inv004_gate(tmp_path) == ()

    def test_missing_docs_dir_is_silent(self, tmp_path: Path) -> None:
        assert inv004_gate(tmp_path) == ()

    def test_outside_spec_dirs_is_silent(self, tmp_path: Path) -> None:
        """T-0515: INV004 is now scoped to `INV003_SPEC_DIRS`, matching
        INV003 -- a narrative doc outside docs/modules and docs/strata
        making a passing normative remark is not the failure mode."""
        _write(
            tmp_path,
            "docs/design/notes.md",
            "# X\n\nThe daemon must never write to this file directly.\n",
        )
        assert inv004_gate(tmp_path) == ()

    def test_markdown_waive_marker_with_reason_is_silent(self, tmp_path: Path) -> None:
        """T-0509/T-0515: a `<!-- frob:waive INV004 reason="..." -->`
        marker anywhere in the file dispositions it without a fake bound
        invariant."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            '# X\n\n<!-- frob:waive INV004 reason="design note, not a gate" -->\n'
            "The daemon must never write to this file directly.\n",
        )
        assert inv004_gate(tmp_path) == ()

    def test_markdown_waive_marker_without_reason_still_warns(
        self, tmp_path: Path
    ) -> None:
        """T-0515: an empty `reason=""` does not count as a waiver, same
        honesty requirement as code-side WAIVE001."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            '# X\n\n<!-- frob:waive INV004 reason="" -->\n'
            "The daemon must never write to this file directly.\n",
        )
        violations = inv004_gate(tmp_path)
        assert len(violations) == 1

    def test_claim_without_verb_in_sentence_is_silent(self, tmp_path: Path) -> None:
        """T-0509: a heading using trigger vocabulary with no claim-verb
        in the same sentence is not a claim."""
        _write(
            tmp_path, "docs/modules/x.md", "# X\n\n## Always current\n\nSee below.\n"
        )
        assert inv004_gate(tmp_path) == ()


class TestPlace001Gate:
    """T-0504: PLACE001 replaces the dropped T-0470 "distance from the
    class's own span start" prototype (proven noisy against this repo's
    own per-field pydantic idiom) with a materially different signal --
    a nearby real symbol the directive plausibly missed via `following`,
    not raw distance. See `_place001_missed_symbol`'s docstring."""

    # frob:tests src/frob/gates/__init__.py::coverage_gate
    def test_missed_following_binding_fires(self, tmp_path: Path) -> None:
        """A directive separated from its intended `def` by more blank
        lines than `_find_following_symbol`'s window (3), with NOTHING
        but blank lines in between, is a genuine placement miss."""
        _write(
            tmp_path,
            "src/a.py",
            "class Foo:\n"
            "    # frob:ticket T-0001\n"
            "\n"
            "\n"
            "\n"
            "\n"
            "    def bar(self):\n"
            "        return 1\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        v = _first_rule(violations, "PLACE001")
        assert v is not None
        # frob:ticket T-2368
        # T-2368: PLACE001 promoted WARN -> ERROR once repo-wide findings
        # reached zero.
        assert v.severity == Severity.ERROR
        assert "Foo" in v.message
        assert "bar" in v.message

    def test_per_field_pydantic_idiom_is_silent(self, tmp_path: Path) -> None:
        """T-0470's counterexample: a directive above one field deep in a
        class, with more real field-assignment code (not blank lines)
        before the next real method, must NOT fire -- this is exactly
        the shape the dropped raw-distance prototype false-positived on
        (`AppConfig`'s `frob:waive SCOPE001` 150+ lines past the class
        line)."""
        _write(
            tmp_path,
            "src/a.py",
            "class AppConfig:\n"
            "    name: str\n"
            '    # frob:waive SCOPE001 reason="test"\n'
            "    value: int = 0\n"
            "    another: str = ''\n"
            "    more: int = 1\n"
            "    yet_more: bool = False\n"
            "    def other(self):\n"
            "        return self.value\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert _first_rule(violations, "PLACE001") is None

    def test_directive_directly_above_def_is_silent(self, tmp_path: Path) -> None:
        """A directive that resolves via `following` in the ordinary way
        (immediately above its `def`) never class-falls-back at all, so
        PLACE001 has nothing to say about it."""
        _write(
            tmp_path,
            "src/a.py",
            "class Foo:\n    # frob:ticket T-0001\n    def bar(self):\n        return 1\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert _first_rule(violations, "PLACE001") is None

    def test_no_nearby_symbol_at_all_is_silent(self, tmp_path: Path) -> None:
        """A class-fallback directive with no real symbol within the
        lookahead window at all has nothing to flag as "missed"."""
        _write(
            tmp_path,
            "src/a.py",
            "class Foo:\n    # frob:ticket T-0001\n    x = 1\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert _first_rule(violations, "PLACE001") is None


class TestExcludeHazardGate:
    # frob:tests src/frob/gates/_exclude_hazard.py::exclude_hazard_gate
    def test_entry_shadowing_tracked_dir_fires(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", "x = 1\n")
        _git_init(tmp_path)
        (tmp_path / ".git" / "info" / "exclude").write_text("src/pkg/\n")
        violations = exclude_hazard_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "EXCL001"
        assert violations[0].severity == Severity.ERROR
        assert "src/pkg" in violations[0].message

    def test_entry_matching_no_tracked_path_is_silent(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", "x = 1\n")
        _git_init(tmp_path)
        (tmp_path / ".git" / "info" / "exclude").write_text("*.pyc\nbuild/\n")
        assert exclude_hazard_gate(tmp_path) == ()

    def test_comment_and_negated_lines_are_ignored(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", "x = 1\n")
        _git_init(tmp_path)
        (tmp_path / ".git" / "info" / "exclude").write_text("# src/pkg/\n!src/pkg/\n")
        assert exclude_hazard_gate(tmp_path) == ()

    def test_exact_tracked_file_entry_fires(self, tmp_path: Path) -> None:
        _write(tmp_path, "README.md", "hi\n")
        _git_init(tmp_path)
        (tmp_path / ".git" / "info" / "exclude").write_text("README.md\n")
        violations = exclude_hazard_gate(tmp_path)
        assert len(violations) == 1

    def test_empty_exclude_file_is_silent(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", "x = 1\n")
        _git_init(tmp_path)
        assert exclude_hazard_gate(tmp_path) == ()

    def test_non_git_root_is_silent(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", "x = 1\n")
        assert exclude_hazard_gate(tmp_path) == ()


class TestRootAssetDirGate:
    """T-1784: ROOT001 -- a repo-root top-level directory with zero code
    references (docs/modules/gates.md#root001-t-1784).

    Acceptance-fixture pair (T-0756 new-gate-rule policy): before this
    rule existed, an orphan repo-root directory like the one these tests
    build was invisible to `frob check` -- nothing FAILED on it. After
    (`root_asset_dir_gate` wired into `_KNOWN_GATE_RULES` and the gate
    dispatch table), the exact same fixture PASSES this test's assertion
    that the violation IS reported -- proving the rule fires through the
    production gate function, not merely a hypothetical.

    T-2389: every fixture writes its own `pyproject.toml` (via
    `_pyproject`, declaring both `[project].name` and a src-layout
    `[tool.setuptools]` block) -- check (a)'s retargeted source-root scan
    resolves both from there (T-2391 fail-loudly: no pyproject.toml means
    UNRESOLVED, not an assumed "frob" default)."""

    @staticmethod
    def _pyproject(tmp_path: Path, name: str = "frob", extra: str = "") -> None:
        """`pyproject.toml` declaring `[project].name = name`, a
        src-layout `[tool.setuptools]` block, and any `extra` TOML text
        appended (e.g. a `[tool.hatch.build]` table for check (b)'s own
        fixtures) -- see `TestEnvVarDocGate._pyproject`'s identical
        reasoning for why the src-layout declaration is required."""
        _write(
            tmp_path,
            "pyproject.toml",
            f'[project]\nname = "{name}"\n\n'
            f'[tool.setuptools]\npackages = {{ find = {{ where = ["src"] }} }}\n'
            f"{extra}",
        )

    # frob:tests src/frob/gates/_root_asset_dirs.py::root_asset_dir_gate
    def test_unreferenced_root_directory_fires(self, tmp_path: Path) -> None:
        """FAIL before this rule exists (`frob.gates._root_asset_dirs`
        did not exist at all -- the repro commit imported it locally and
        got a ModuleNotFoundError); PASS after (`root_asset_dir_gate`
        reports ROOT001 for it) -- the T-1611 agents/skills incident's
        exact shape, mechanized."""
        self._pyproject(tmp_path)
        _write(tmp_path, "src/frob/x.py", "x = 1\n")
        _write(tmp_path, "orphan/file.txt", "x\n")
        _git_init(tmp_path)
        violations = root_asset_dir_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "ROOT001"
        assert violations[0].severity == Severity.WARN
        assert violations[0].file == "orphan"

    # frob:tests src/frob/gates/_root_asset_dirs.py::root_asset_dir_gate
    def test_unreferenced_root_directory_fires_for_a_differently_named_project(
        self, tmp_path: Path
    ) -> None:
        """T-2384/T-2389 must-now-fire: check (a) still catches a
        legitimately-unreferenced directory in a `lograder`-named
        project's own layout -- BEFORE this retarget, the hardcoded
        `src/frob/` prefix meant check (a) always scanned the WRONG
        (nonexistent) directory off-repo, so its "not referenced" verdict
        was not even a real answer, just an artifact of scanning nothing.
        `src/frob/...` is deliberately absent from this fixture."""
        self._pyproject(tmp_path, name="lograder")
        _write(tmp_path, "src/lograder/x.py", "x = 1\n")
        _write(tmp_path, "orphan/file.txt", "x\n")
        _git_init(tmp_path)
        violations = root_asset_dir_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "ROOT001"
        assert violations[0].file == "orphan"

    # frob:tests src/frob/gates/_root_asset_dirs.py::root_asset_dir_gate
    def test_directory_referenced_under_src_frob_is_silent(
        self, tmp_path: Path
    ) -> None:
        """Check (a): a repo-root directory whose name appears literally
        as a path token anywhere under this project's own declared
        source roots is not flagged -- proving check (a) is genuinely
        FALSE-POSITIVE-FIXED, not just true-positive-fixed: a
        legitimately referenced directory in a `lograder`-named project
        (T-2384's own measured false-positive class) is not flagged
        either, the SAME must-now-fire/must-not-false-fire pair the
        `frob`-named cases above already prove from the other side."""
        self._pyproject(tmp_path, name="lograder")
        _write(tmp_path, "src/lograder/x.py", 'REF = "known/f.txt"\n')
        _write(tmp_path, "known/f.txt", "x\n")
        _git_init(tmp_path)
        assert root_asset_dir_gate(tmp_path) == ()

    def test_directory_referenced_in_pyproject_is_silent(self, tmp_path: Path) -> None:
        """Check (b): a repo-root directory named in `pyproject.toml`'s
        own text is not flagged."""
        self._pyproject(tmp_path, extra='[tool.hatch.build]\ninclude = ["packaged/"]\n')
        _write(tmp_path, "src/frob/x.py", "x = 1\n")
        _write(tmp_path, "packaged/data.txt", "x\n")
        _git_init(tmp_path)
        assert root_asset_dir_gate(tmp_path) == ()

    def test_directory_with_external_reader_declaration_is_silent(
        self, tmp_path: Path
    ) -> None:
        """Check (c): a repo-root directory with an explicit
        `frob:external-reader dir="name"` declaration in ANY tracked
        markdown file is not flagged -- the real, checkable-claim escape
        hatch for something genuinely read only by a process outside this
        repo's own code (the harness-config case)."""
        self._pyproject(tmp_path)
        _write(tmp_path, "src/frob/x.py", "x = 1\n")
        _write(tmp_path, "harness_config/skill.md", "hi\n")
        _write(
            tmp_path,
            "docs/notes.md",
            '<!-- frob:external-reader dir="harness_config" '
            'reason="read by the external dispatch harness" -->\n',
        )
        _git_init(tmp_path)
        assert root_asset_dir_gate(tmp_path) == ()

    def test_makefile_referenced_directory_is_silent(self, tmp_path: Path) -> None:
        """The ticket's own "scripts a Makefile target actually invokes"
        exemption clause: a directory literally named in the Makefile is
        not flagged even with no other reference."""
        self._pyproject(tmp_path)
        _write(tmp_path, "src/frob/x.py", "x = 1\n")
        _write(tmp_path, "scripts/run.sh", "#!/bin/sh\n")
        _write(tmp_path, "Makefile", "deploy:\n\tsh scripts/run.sh\n")
        _git_init(tmp_path)
        assert root_asset_dir_gate(tmp_path) == ()

    def test_allowlisted_directories_are_silent(self, tmp_path: Path) -> None:
        """`docs/`, `tickets/`, `design/` are exempt by the ticket's own
        named allowlist, with no reference of any kind."""
        self._pyproject(tmp_path)
        _write(tmp_path, "src/frob/x.py", "x = 1\n")
        _write(tmp_path, "docs/readme.md", "hi\n")
        _write(tmp_path, "tickets/T-0001/ticket.md", "hi\n")
        _write(tmp_path, "design/frob.strata", "hi\n")
        _git_init(tmp_path)
        assert root_asset_dir_gate(tmp_path) == ()

    def test_src_and_tests_dirs_are_never_flagged(self, tmp_path: Path) -> None:
        """`src/` and `tests/` are the structural code/test roots -- never
        candidates for this gate regardless of reference evidence."""
        self._pyproject(tmp_path)
        _write(tmp_path, "src/frob/x.py", "x = 1\n")
        _write(tmp_path, "tests/test_x.py", "pass\n")
        _git_init(tmp_path)
        assert root_asset_dir_gate(tmp_path) == ()

    def test_non_git_root_is_silent(self, tmp_path: Path) -> None:
        _write(tmp_path, "orphan/file.txt", "x\n")
        assert root_asset_dir_gate(tmp_path) == ()

    # frob:tests src/frob/gates/_root_asset_dirs.py::root_asset_dir_gate
    def test_missing_pyproject_is_unresolved_not_a_clean_pass(
        self, tmp_path: Path
    ) -> None:
        """T-2391 fail-loudly doctrine: a git-tracked repo with no
        `pyproject.toml` (so no declared package name for check (a)'s
        source-root prefix) produces an UNRESOLVED finding, never a
        silent, clean-looking empty violation list."""
        _write(tmp_path, "src/frob/x.py", "x = 1\n")
        _write(tmp_path, "orphan/file.txt", "x\n")
        _git_init(tmp_path)
        violations = root_asset_dir_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "ROOT001"
        assert violations[0].severity == Severity.UNRESOLVED


class TestEnvVarDocGate:
    """T-1782: ENV001 -- a `FROB_*` env var with no doc anchor or waiver
    (docs/modules/gates.md#env001-t-1782).

    Acceptance-fixture pair (T-0756 new-gate-rule policy): before this
    rule existed, an undocumented `FROB_*` constant like the ones these
    tests build was invisible to `frob check` -- the T-1610 audit found
    `FROB_WORKER_STDOUT_LOG_LEVEL` undocumented for two weeks precisely
    because nothing FAILED on it. After (`env_var_doc_gate` wired into
    `_KNOWN_GATE_RULES` and the gate dispatch table), the exact same
    fixture PASSES this test's assertion that the violation IS reported.

    T-2389: every fixture now writes its own `pyproject.toml` -- the
    retargeted gate resolves the env-var prefix/source-root scope from
    `[project].name` (T-2391 fail-loudly: no pyproject.toml means
    UNRESOLVED, not an assumed "frob" default), so a fixture with none
    would silently stop exercising the WARN path these tests assert."""

    @staticmethod
    def _pyproject(tmp_path: Path, name: str = "frob") -> None:
        """`pyproject.toml` declaring `[project].name = name` AND a
        src-layout `[tool.setuptools]` block (matching this repo's own
        real pyproject.toml) -- the denominator `declared_project_
        package_name`/`declared_source_prefixes` (T-2389, `frob.lang`)
        resolve the env-var prefix and scanned source roots from. Without
        the setuptools src declaration, `_declared_python_source_roots`
        (T-2195) has no way to know these fixtures use `src/<pkg>/`
        layout and falls back to bare-root-relative prefixes only,
        silently missing every `src/<pkg>/...` fixture path below."""
        _write(
            tmp_path,
            "pyproject.toml",
            f'[project]\nname = "{name}"\n\n'
            f'[tool.setuptools]\npackages = {{ find = {{ where = ["src"] }} }}\n',
        )

    # frob:tests src/frob/gates/_env_var_docs.py::env_var_doc_gate
    def test_undocumented_env_var_fires(self, tmp_path: Path) -> None:
        """FAIL before this rule exists (`frob.gates._env_var_docs` did
        not exist at all -- the repro commit's import raised
        `ModuleNotFoundError`); PASS after (`env_var_doc_gate` reports
        ENV001 for it) -- the T-1610 undocumented-env-var incident,
        mechanized."""
        self._pyproject(tmp_path)
        _write(tmp_path, "src/frob/x.py", '_UNDOC_ENV = "FROB_UNDOCUMENTED"\n')
        _git_init(tmp_path)
        violations = env_var_doc_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "ENV001"
        assert violations[0].severity == Severity.WARN
        assert violations[0].file == "src/frob/x.py"
        assert violations[0].line == 1

    # frob:tests src/frob/gates/_env_var_docs.py::env_var_doc_gate
    def test_undocumented_env_var_fires_for_a_differently_named_project(
        self, tmp_path: Path
    ) -> None:
        """T-2384/T-2389 must-now-fire: a `lograder`-named project's OWN
        `LOGRADER_*` env var, undocumented, is caught the same way --
        BEFORE this retarget, the hardcoded `FROB_`/`src/frob/` literals
        made this silently invisible (zero candidates: neither the
        source-root scan nor the env-var prefix pattern ever matched a
        non-`frob` project). `src/frob/...` is deliberately absent from
        this fixture to prove the scan is not silently falling back to
        it."""
        self._pyproject(tmp_path, name="lograder")
        _write(tmp_path, "src/lograder/x.py", '_UNDOC_ENV = "LOGRADER_UNDOCUMENTED"\n')
        _git_init(tmp_path)
        violations = env_var_doc_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "ENV001"
        assert violations[0].file == "src/lograder/x.py"

    def test_documented_by_literal_string_is_silent(self, tmp_path: Path) -> None:
        """Check (a), literal form: the env-var string itself appears
        somewhere under `docs/`."""
        self._pyproject(tmp_path)
        _write(tmp_path, "src/frob/x.py", '_DOC_ENV = "FROB_DOCUMENTED"\n')
        _write(tmp_path, "docs/config.md", "Set FROB_DOCUMENTED to enable X.\n")
        _git_init(tmp_path)
        assert env_var_doc_gate(tmp_path) == ()

    def test_documented_by_constant_name_is_silent(self, tmp_path: Path) -> None:
        """Check (a), constant-name form: the T-1610-established
        allowance -- documented by the Python constant's own name instead
        of the literal env-var string."""
        self._pyproject(tmp_path)
        _write(
            tmp_path, "src/frob/x.py", '_ARTIFACT_CACHE_ENV = "FROB_ARTIFACT_CACHE"\n'
        )
        _write(
            tmp_path,
            "docs/config.md",
            "See `_ARTIFACT_CACHE_ENV` for the cache override.\n",
        )
        _git_init(tmp_path)
        assert env_var_doc_gate(tmp_path) == ()

    def test_file_scoped_waiver_covers_it(self, tmp_path: Path) -> None:
        """Check (b): a `frob:waive ENV001` directive anywhere in the same
        source file waives every `FROB_*` constant in it -- the
        genuinely-internal/test-only/worker-internal escape hatch."""
        self._pyproject(tmp_path)
        _write(
            tmp_path,
            "src/frob/worker.py",
            '# frob:waive ENV001 reason="worker-internal flag, not user-facing"\n'
            '_WORKER_FLAG = "FROB_WORKER_INTERNAL"\n',
        )
        _git_init(tmp_path)
        from frob.gates import _apply_waivers  # noqa: PLC0415 - internal, test-only

        snapshot = _snapshot(tmp_path)
        raw = env_var_doc_gate(tmp_path)
        assert len(raw) == 1
        kept, waived = _apply_waivers(raw, snapshot)
        assert kept == ()
        assert len(waived) == 1

    def test_non_frob_env_prefixed_constants_are_ignored(self, tmp_path: Path) -> None:
        """A constant assigned some OTHER string entirely is not this
        gate's concern -- only `FROB_*`-prefixed literal values count."""
        self._pyproject(tmp_path)
        _write(tmp_path, "src/frob/x.py", '_OTHER = "SOME_OTHER_VALUE"\n')
        _git_init(tmp_path)
        assert env_var_doc_gate(tmp_path) == ()

    def test_no_env_assignments_is_silent(self, tmp_path: Path) -> None:
        self._pyproject(tmp_path)
        _write(tmp_path, "src/frob/x.py", "x = 1\n")
        _git_init(tmp_path)
        assert env_var_doc_gate(tmp_path) == ()

    def test_non_git_root_is_silent(self, tmp_path: Path) -> None:
        self._pyproject(tmp_path)
        _write(tmp_path, "src/frob/x.py", '_UNDOC_ENV = "FROB_UNDOCUMENTED"\n')
        assert env_var_doc_gate(tmp_path) == ()

    # frob:tests src/frob/gates/_env_var_docs.py::env_var_doc_gate
    def test_missing_pyproject_is_unresolved_not_a_clean_pass(
        self, tmp_path: Path
    ) -> None:
        """T-2391 fail-loudly doctrine: a repo with no `pyproject.toml`
        (so no declared package name to resolve an env-var prefix from)
        produces an UNRESOLVED finding, never a silent, clean-looking
        empty violation list."""
        _write(tmp_path, "src/frob/x.py", '_UNDOC_ENV = "FROB_UNDOCUMENTED"\n')
        _git_init(tmp_path)
        violations = env_var_doc_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "ENV001"
        assert violations[0].severity == Severity.UNRESOLVED


class TestInvariantLoad:
    """T-4019: `load_invariants` returns a plain `LoadedInvariants` (never
    `Result`) -- ONE malformed file becomes its own `InvariantLoadError`
    in `.errors`, never a whole-load failure, and never silently dropped
    either (`.errors` always names it)."""

    def test_malformed_bad_id(self, tmp_path: Path) -> None:
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-abc.md").write_text(
            "---\nid: INV-abc\nstatement: x\ncriticality: high\nevidence: []\n---\nprose\n"
        )
        loaded = load_invariants(tmp_path)
        assert loaded.invariants == ()
        assert loaded.errors == (
            InvariantLoadError(
                path="invariants/INV-abc.md", error=InvariantError.Malformed
            ),
        )

    def test_duplicate_id(self, tmp_path: Path) -> None:
        """The FIRST file in sorted path order ("INV-001-dup.md" < "INV-001.md",
        `-` sorts before `.`) keeps its invariant; the SECOND becomes its
        own `InvariantLoadError` naming its own path -- both files are
        distinguishable in the result, never a single undifferentiated
        `DuplicateId`."""
        (tmp_path / "invariants").mkdir()
        text = "---\nid: INV-001\nstatement: x\ncriticality: high\nevidence: []\n---\nprose\n"
        (tmp_path / "invariants" / "INV-001.md").write_text(text)
        (tmp_path / "invariants" / "INV-001-dup.md").write_text(text)
        loaded = load_invariants(tmp_path)
        assert [inv.id for inv in loaded.invariants] == ["INV-001"]
        assert loaded.errors == (
            InvariantLoadError(
                path="invariants/INV-001.md", error=InvariantError.DuplicateId
            ),
        )

    def test_missing_directory_ok(self, tmp_path: Path) -> None:
        loaded = load_invariants(tmp_path)
        assert loaded.invariants == ()
        assert loaded.errors == ()

    def test_loads_valid(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/invariants.py::load_invariants
        (tmp_path / "invariants").mkdir()
        text = (
            "---\nid: INV-007\nstatement: locks are atomic\ncriticality: high\n"
            "evidence:\n  - tests/test_lock.py::test_atomic\n---\nRationale.\n"
        )
        (tmp_path / "invariants" / "INV-007.md").write_text(text)
        loaded = load_invariants(tmp_path)
        assert loaded.errors == ()
        assert loaded.invariants[0].id == "INV-007"
        assert loaded.invariants[0].evidence == ("tests/test_lock.py::test_atomic",)

    def test_descriptive_id_loads(self, tmp_path: Path) -> None:
        """T-4019 defect 3: a descriptive id (the shape the `frob:invariant`
        code directive already accepts with no restriction of its own --
        `INV-RENDER-SOLE-STDOUT` is a real, working example in this repo)
        is accepted by the file loader too, not just three digits."""
        (tmp_path / "invariants").mkdir()
        text = (
            "---\nid: INV-ADMIN-DATA-001\nstatement: admin data is scoped\n"
            "criticality: high\nevidence:\n  - tests/test_admin.py::test_scope\n"
            "---\nRationale.\n"
        )
        (tmp_path / "invariants" / "INV-ADMIN-DATA-001.md").write_text(text)
        loaded = load_invariants(tmp_path)
        assert loaded.errors == ()
        assert loaded.invariants[0].id == "INV-ADMIN-DATA-001"

    def test_one_malformed_file_does_not_block_others(self, tmp_path: Path) -> None:
        """T-4019 defect 2 (blast radius): a malformed file alongside a
        valid one produces exactly one `InvariantLoadError` for the bad
        file, while the valid file's invariant still loads."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-bad.md").write_text("no frontmatter at all\n")
        (tmp_path / "invariants" / "INV-002.md").write_text(
            "---\nid: INV-002\nstatement: x\ncriticality: high\n"
            "evidence:\n  - tests/test_x.py::test_x\n---\nRationale.\n"
        )
        loaded = load_invariants(tmp_path)
        assert [inv.id for inv in loaded.invariants] == ["INV-002"]
        assert len(loaded.errors) == 1
        assert loaded.errors[0].path == "invariants/INV-bad.md"
        assert loaded.errors[0].error == InvariantError.Malformed

    def test_unreadable_file_is_malformed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An `OSError` reading the invariant file becomes a per-file
        `InvariantLoadError(error=Malformed)`, not a crash -- proves
        `_frontmatter_dict`'s read-failure branch."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-001.md").write_text(
            "---\nid: INV-001\nstatement: x\ncriticality: high\nevidence: []\n---\n"
        )
        real_read_text = Path.read_text

        def _boom(self: Path, *a, **kw):  # noqa: ANN001, ANN002, ANN003
            if self.name == "INV-001.md":
                raise OSError("permission denied")
            return real_read_text(self, *a, **kw)

        monkeypatch.setattr(Path, "read_text", _boom)
        loaded = load_invariants(tmp_path)
        assert loaded.invariants == ()
        assert loaded.errors[0].error == InvariantError.Malformed

    def test_no_frontmatter_block_is_malformed(self, tmp_path: Path) -> None:
        """A file with no `---`-delimited frontmatter block at all becomes
        a per-file `Malformed` error -- proves the no-match regex branch."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-001.md").write_text("just prose, no yaml\n")
        loaded = load_invariants(tmp_path)
        assert loaded.errors[0].error == InvariantError.Malformed

    def test_bad_yaml_frontmatter_is_malformed(self, tmp_path: Path) -> None:
        """Unparseable YAML inside the frontmatter block becomes a
        per-file `Malformed` error -- proves the `yaml.YAMLError` branch."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-001.md").write_text(
            "---\nid: [unterminated\n---\nprose\n"
        )
        loaded = load_invariants(tmp_path)
        assert loaded.errors[0].error == InvariantError.Malformed

    def test_non_mapping_frontmatter_is_malformed(self, tmp_path: Path) -> None:
        """A frontmatter block that parses to a YAML scalar/list, not a
        mapping, becomes a per-file `Malformed` error -- proves the
        not-a-dict branch."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-001.md").write_text(
            "---\n- one\n- two\n---\nprose\n"
        )
        loaded = load_invariants(tmp_path)
        assert loaded.errors[0].error == InvariantError.Malformed

    # frob:waive DUP002 reason="T-0160's own evidence cites these three test node ids \
    # by name (test_empty_statement_is_malformed, \
    # test_evidence_not_a_list_is_malformed, test_bad_criticality_is_malformed) -- \
    # consolidating them into one parametrized test (tried, then reverted) orphans \
    # that evidence (COV003), the exact test-deletion-breaks-other-tickets'-evidence \
    # class; each proves a DIFFERENT _build_invariant/_validate_invariant_shape \
    # field-shape branch (statement/evidence/criticality) even though the bodies read \
    # alike"
    def test_empty_statement_is_malformed(self, tmp_path: Path) -> None:
        """An empty `statement` field fails `_validate_invariant_shape`'s
        non-empty check."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-001.md").write_text(
            "---\nid: INV-001\nstatement: ''\ncriticality: high\nevidence: []\n---\n"
        )
        loaded = load_invariants(tmp_path)
        assert loaded.errors[0].error == InvariantError.Malformed

    def test_evidence_not_a_list_is_malformed(self, tmp_path: Path) -> None:
        """A non-list `evidence` field becomes a per-file `Malformed`
        error -- proves `_build_invariant`'s evidence-shape branch."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-001.md").write_text(
            "---\nid: INV-001\nstatement: x\ncriticality: high\nevidence: notalist\n---\n"
        )
        loaded = load_invariants(tmp_path)
        assert loaded.errors[0].error == InvariantError.Malformed

    def test_bad_criticality_is_malformed(self, tmp_path: Path) -> None:
        """A `criticality` value outside the `_Criticality` enum becomes a
        per-file `Malformed` error -- proves the criticality-membership
        branch."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-001.md").write_text(
            "---\nid: INV-001\nstatement: x\ncriticality: catastrophic\nevidence: []\n---\n"
        )
        loaded = load_invariants(tmp_path)
        assert loaded.errors[0].error == InvariantError.Malformed
