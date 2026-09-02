import builtins
import json
import subprocess
from pathlib import Path

import pytest

from frob.gates import (
    _KNOWN_RULE_FIXABILITY,
    Severity,
    Violation,
    generated_fixability,
    known_gate_rule_ids,
    sys_gate,
)
from frob.gates._fixability_scan import FixabilityConflict
from frob.gates._rule_id_scan import (
    generated_gate_rule_ids,
    scan_emitted_rule_ids,
)
from frob.gates._sys import selfaudit_findings_touching  # noqa: E402
from tests.conftest import (
    _DESIGN_STRATA,
    _by_rule,
    _complex_function_source,
    _git_init,
    _snapshot,
    _write,
)

_SELFAUDIT_DESIGN_STRATA_UNDECLARED = """module m
node widget : trusted { code "src/frob/widget/**"; }
"""


# frob:ticket T-2407
class TestSysGate:
    # frob:tests src/frob/gates/_sys.py::sys_gate kind="unit"
    def test_noop_no_design_dir(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", "def f(): pass\n")
        snapshot = _snapshot(tmp_path)
        assert sys_gate(tmp_path, snapshot) == ()

    def test_sys001_dangling(self, tmp_path: Path) -> None:
        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        _write(
            tmp_path,
            "src/a.py",
            "def send():\n    # frob:channel f_does_not_exist\n    pass\n",
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys001 = _by_rule(violations, "SYS001")
        assert len(sys001) == 1
        assert sys001[0].severity == Severity.ERROR

    def test_sys001_valid(self, tmp_path: Path) -> None:
        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        _write(
            tmp_path, "src/a.py", "def send():\n    # frob:channel f_login\n    pass\n"
        )
        snapshot = _snapshot(tmp_path)
        assert _by_rule(sys_gate(tmp_path, snapshot), "SYS001") == []

    def test_sys002_unbound(self, tmp_path: Path) -> None:
        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        _write(tmp_path, "src/a.py", "def f(): pass\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys002 = _by_rule(violations, "SYS002")
        assert {v.message.split()[2] for v in sys002} == {"b_login", "vault"}
        assert all(v.severity == Severity.WARN for v in sys002)

    def test_sys002_bound(self, tmp_path: Path) -> None:
        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        _write(
            tmp_path,
            "src/a.py",
            "def verify():\n"
            "    # frob:boundary b_login\n"
            "    pass\n\n"
            "def rotate():\n"
            "    # frob:secret vault\n"
            "    pass\n",
        )
        snapshot = _snapshot(tmp_path)
        assert _by_rule(sys_gate(tmp_path, snapshot), "SYS002") == []

    # frob:ticket T-2407
    def test_sys003_import(self, tmp_path: Path, monkeypatch) -> None:
        """T-0080: SYS003 surfaces `check_import_conformance`'s tier-2
        violations through `sys_gate`. The surface grammar does not lex
        `code=` globs yet (docs/strata/surface.md#code-binding-tier-2-v0-
        implementation), so this wires a `KernelModel` built via the Python
        API directly, monkeypatching `frob.strata.load_design_ids` the way
        `test_load_tests_merges_python_and_rust_node_ids` monkeypatches
        collectors -- the design/ dir only needs to exist for `sys_gate`'s
        opt-in check.
        """
        import frob.strata as strata_mod
        from frob.strata import DesignIds, Node

        _write(tmp_path, "design/.gitkeep", "")
        _write(tmp_path, "pkg_a/mod.py", "import pkg_b.mod\n")
        _write(tmp_path, "pkg_b/mod.py", "x = 1\n")
        model = strata_mod.KernelModel(
            nodes=(
                Node(id="a", trust="trusted", attrs=("code=pkg_a/*.py",)),
                Node(id="b", trust="trusted", attrs=("code=pkg_b/*.py",)),
            )
        )
        monkeypatch.setattr(
            strata_mod,
            "load_design_ids",
            lambda root, design_dir: DesignIds(models=(model,)),
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys003 = _by_rule(violations, "SYS003")
        assert len(sys003) == 1
        assert sys003[0].file == "pkg_a/mod.py"
        # T-2407: SYS003 promoted WARN -> ERROR after the T-2380/T-2403/
        # T-2407 calibration burned genuine findings to zero (was WARN
        # for warn-first adoption per T-0080 REJECT round 1, same
        # posture COV001 started from).
        assert sys003[0].severity == Severity.ERROR

    def test_sys004_load_failure(self, tmp_path: Path) -> None:
        # T-0080 REJECT round 1: a malformed .strata file must be reported
        # as its own SYS004 violation naming the file, not silently dropped.
        _write(tmp_path, "design/bad.strata", "this is not valid strata {{{")
        _write(tmp_path, "src/a.py", "def f(): pass\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys004 = _by_rule(violations, "SYS004")
        assert len(sys004) == 1
        assert sys004[0].file == "design/bad.strata"
        assert sys004[0].severity == Severity.ERROR

    def test_sys004_suppresses_sys001(self, tmp_path: Path) -> None:
        # T-0080 REJECT round 1: when a sibling .strata file fails to load,
        # ids are merged with no per-file provenance, so a directive
        # referencing an id that WOULD have come from the broken file must
        # not be misdiagnosed as SYS001 dangling -- SYS001 is suppressed for
        # the whole run and SYS004 alone reports the real problem.
        _write(tmp_path, "design/good.strata", _DESIGN_STRATA)
        _write(tmp_path, "design/bad.strata", "this is not valid strata {{{")
        _write(
            tmp_path,
            "src/a.py",
            "def send():\n    # frob:channel f_login\n    pass\n",
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        assert _by_rule(violations, "SYS001") == []
        assert len(_by_rule(violations, "SYS004")) == 1

    def test_sys004_names_stale_native_as_likely_remedy(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # T-0347 (T-0248 follow-up, T-0166 incident precedent): a `.strata`
        # load failure caused by a grammar-ahead-of-native mismatch must
        # name `make core` as the likely remedy, not just say "fix the
        # .strata file" -- that message alone sent a reviewer chasing a
        # nonexistent syntax error during T-0166.
        import frob.strata as strata_mod
        from frob.strata import StaleNative
        from frob.testing._models import NativeSpec

        _write(tmp_path, "design/bad.strata", "this is not valid strata {{{")
        _write(tmp_path, "src/a.py", "def f(): pass\n")
        fake_stale = StaleNative(
            spec=NativeSpec(name="strata_core", build_cmd="make core"),
            source_dir="strata-core",
            artifact_mtime=1.0,
            source_mtime=2.0,
        )
        monkeypatch.setattr(strata_mod, "stale_natives", lambda root: (fake_stale,))
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys004 = _by_rule(violations, "SYS004")
        assert len(sys004) == 1
        assert "make core" in sys004[0].message
        assert "strata_core" in sys004[0].message

    # frob:ticket T-2707
    def test_sys004_names_missing_native_hint_when_genuinely_absent(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """POSITIVE CONTROL (genuinely-absent direction, T-2707): with
        `strata_core` truly missing and NO import error captured, SYS004
        still names the friendly not-installed hint -- the common,
        useful case must not be lost by naming the real exception."""
        import frob.strata._parse as parse_mod

        monkeypatch.setattr(parse_mod, "strata_core", None)
        monkeypatch.setattr(parse_mod, "_import_error", None)
        _write(tmp_path, "design/bad.strata", "module m")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys004 = _by_rule(violations, "SYS004")
        assert len(sys004) == 1
        assert "not installed" in sys004[0].message
        assert "actual import error" not in sys004[0].message

    # frob:ticket T-2707
    def test_sys004_names_real_exception_when_strata_core_fails_differently(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """MUST-FAIL POSITIVE CONTROL (T-2707's critical control): a
        `strata_core` that raised a DIFFERENT `ImportError` (ABI/symbol
        mismatch or a failing secondary import) must have SYS004 report
        THAT exception, not silently relabel it as the generic
        not-installed guess -- the exact masking defect a downstream
        consumer (aprog-public) hit and was misdirected by."""
        import frob.strata._parse as parse_mod

        monkeypatch.setattr(parse_mod, "strata_core", None)
        monkeypatch.setattr(
            parse_mod,
            "_import_error",
            "ImportError: libstrata_core.abi3.so: undefined symbol: some_native_fn",
        )
        _write(tmp_path, "design/bad.strata", "module m")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys004 = _by_rule(violations, "SYS004")
        assert len(sys004) == 1
        assert "undefined symbol" in sys004[0].message

    def test_doc003_proved_claim_passes(self, tmp_path: Path, monkeypatch) -> None:
        """T-0085: a `frob:claims <view>` marker whose obligations are all
        discharged produces no DOC003 violation."""
        import frob.strata as strata_mod
        from frob.strata import Claim, DesignIds, Node, NoFlow, Rung
        from frob.strata._threat_discharge import _discharge_claim_id

        node = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = strata_mod.KernelModel(
            nodes=(node,),
            claims=(
                Claim(
                    id=claim_id,
                    body=NoFlow(src="foreign", dst="Web"),
                    required_rung=Rung.L4,
                ),
            ),
        )
        _write(tmp_path, "design/.gitkeep", "")
        _write(tmp_path, "README.md", "<!-- frob:claims owasp-top-10 -->\n")
        monkeypatch.setattr(
            strata_mod,
            "load_design_ids",
            lambda root, design_dir: DesignIds(models=(model,)),
        )
        snapshot = _snapshot(tmp_path)
        assert _by_rule(sys_gate(tmp_path, snapshot), "DOC003") == []

    def test_doc003_refutes_names_obligations(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """T-0085: an undischarged obligation for the claimed view is a
        DOC003 error naming the failing obligation (the CWE id)."""
        import frob.strata as strata_mod
        from frob.strata import DesignIds, Node

        model = strata_mod.KernelModel(
            nodes=(Node(id="Web", trust="trusted", may=("html_render",)),)
        )
        _write(tmp_path, "design/.gitkeep", "")
        _write(tmp_path, "README.md", "<!-- frob:claims owasp-top-10 -->\n")
        monkeypatch.setattr(
            strata_mod,
            "load_design_ids",
            lambda root, design_dir: DesignIds(models=(model,)),
        )
        snapshot = _snapshot(tmp_path)
        doc003 = _by_rule(sys_gate(tmp_path, snapshot), "DOC003")
        assert len(doc003) == 1
        assert "CWE-79" in doc003[0].message
        assert doc003[0].file == "README.md"
        assert doc003[0].severity == Severity.ERROR

    def test_doc003_unclaimed_view_ignored(self, tmp_path: Path, monkeypatch) -> None:
        """T-0085: no `frob:claims` marker anywhere means DOC003 does not
        even evaluate the model -- an unclaimed view is silent, by design."""
        import frob.strata as strata_mod
        from frob.strata import DesignIds, Node

        model = strata_mod.KernelModel(
            nodes=(Node(id="Web", trust="trusted", may=("html_render",)),)
        )
        _write(tmp_path, "design/.gitkeep", "")
        _write(tmp_path, "README.md", "no claims marker here\n")
        monkeypatch.setattr(
            strata_mod,
            "load_design_ids",
            lambda root, design_dir: DesignIds(models=(model,)),
        )
        snapshot = _snapshot(tmp_path)
        assert _by_rule(sys_gate(tmp_path, snapshot), "DOC003") == []

    def test_doc003_unknown_view(self, tmp_path: Path, monkeypatch) -> None:
        """T-0085: a `frob:claims` marker naming a view the catalog does
        not ship is its own DOC003 error, not a silent pass."""
        import frob.strata as strata_mod
        from frob.strata import DesignIds

        model = strata_mod.KernelModel()
        _write(tmp_path, "design/.gitkeep", "")
        _write(tmp_path, "README.md", "<!-- frob:claims no-such-view -->\n")
        monkeypatch.setattr(
            strata_mod,
            "load_design_ids",
            lambda root, design_dir: DesignIds(models=(model,)),
        )
        snapshot = _snapshot(tmp_path)
        doc003 = _by_rule(sys_gate(tmp_path, snapshot), "DOC003")
        assert len(doc003) == 1
        assert "unknown baseline view" in doc003[0].message

    def test_doc003_marker_in_fenced_block_ignored(self, tmp_path: Path) -> None:
        """T-0085 round 2 (reviewer REJECT): a `frob:claims` marker inside a
        ```-fenced block documents the directive, it does not claim
        anything -- must not be extracted."""
        import frob.gates as gates_mod

        _write(
            tmp_path,
            "README.md",
            "# Example\n\n```markdown\n<!-- frob:claims owasp-top-10 -->\n```\n",
        )
        assert gates_mod._claims_markers(tmp_path) == []

    def test_doc003_marker_in_inline_code_ignored(self, tmp_path: Path) -> None:
        """T-0085 round 2: a `frob:claims` marker inside inline `backticks`
        on a prose line is a quotation, not a live claim."""
        import frob.gates as gates_mod

        _write(
            tmp_path,
            "README.md",
            "Write `<!-- frob:claims owasp-top-10 -->` in any doc page.\n",
        )
        assert gates_mod._claims_markers(tmp_path) == []

    def test_doc003_real_marker_with_fenced_example_extracts_once(
        self, tmp_path: Path
    ) -> None:
        """T-0085 round 2: a genuine top-level marker on a page that ALSO
        shows a fenced example of the directive extracts exactly the real
        one -- fence-awareness must not eat legitimate markers either."""
        import frob.gates as gates_mod

        _write(
            tmp_path,
            "README.md",
            "<!-- frob:claims owasp-top-10 -->\n"
            "\n"
            "Example of the directive:\n"
            "\n"
            "```markdown\n"
            "<!-- frob:claims owasp-top-10 -->\n"
            "```\n",
        )
        markers = gates_mod._claims_markers(tmp_path)
        assert markers == [("README.md", 1, "owasp-top-10")]

    def test_default_design_dir_mirror_stays_in_sync(self) -> None:
        """T-0135 review follow-up: the deliberate mirror literal must not drift.

        `frob.gates._DEFAULT_DESIGN_DIR` is a bare string duplicate of
        `frob.strata._design_load.DEFAULT_DESIGN_DIR` -- duplicated (not
        imported) so `_design_dir` never touches `frob.strata` for a repo
        with no design dir. Both imports happen INSIDE this test function
        (never at module level) so this file itself never pays the
        `frob.strata` import cost just by being collected; only this one
        test -- which exists precisely to prove the two literals agree --
        does.
        """
        import frob.gates as gates_mod
        from frob.strata import DEFAULT_DESIGN_DIR

        assert gates_mod._DEFAULT_DESIGN_DIR == DEFAULT_DESIGN_DIR

    def test_no_design_dir_never_imports_frob_strata(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0135: a repo with no design/ dir must never import frob.strata.

        frob.strata transitively imports frob/strata/_facts.py, which needs
        the strata_core native extension (T-0134 degrades that to a typed
        Err, but the point of this ticket is a repo that never opted into
        design/ at all should not even reach that machinery). Simulate the
        standalone-install worst case by making `frob.strata` itself
        unimportable, then confirm sys_gate on a design-less repo still
        returns cleanly instead of propagating the ImportError.
        """
        real_import = builtins.__import__

        def _blow_up_on_frob_strata(name, *args, **kwargs):
            if name == "frob.strata" or name.startswith("frob.strata."):
                raise ImportError("simulated: strata_core unavailable")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _blow_up_on_frob_strata)
        _write(tmp_path, "src/a.py", "def f(): pass\n")
        snapshot = _snapshot(tmp_path)
        assert sys_gate(tmp_path, snapshot) == ()

    def test_design_dir_degrades_with_typed_error_on_native_extension_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0135: a repo WITH design/ must degrade (T-0134), never crash.

        Monkeypatches frob.strata._parse's module-level `strata_core`
        binding to None -- the state a bare `uv tool install frob` (no
        natives) leaves it in -- and confirms sys_gate on a repo that DOES
        have a design/ dir reports the parse failure as a typed SYS004
        violation instead of raising an unhandled exception.
        """
        import frob.strata._parse as parse_mod

        monkeypatch.setattr(parse_mod, "strata_core", None)
        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        _write(tmp_path, "src/a.py", "def f(): pass\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys004 = _by_rule(violations, "SYS004")
        assert len(sys004) == 1
        assert sys004[0].file == "design/m.strata"


class TestSelfAuditGate:
    """T-0756 SELFAUDIT001: sys_gate's production entrypoint folds frob's
    own self-conformance (SYS100-102)/resource-contention (SYS2xx)/
    reliability (REL2xx) audit surface into the ordinary gate pipeline
    (docs/modules/gates.md#self-audit-at-land-selfaudit001-t-0756). Each test is written to
    prove the PRODUCTION invocation (`sys_gate`, the function `frob check`
    itself calls) actually fires SELFAUDIT001 -- not a direct call into
    `frob.strata.check_self_conformance`, which `tests/unit/strata/
    test_selfconform.py` already covers at the pure-function level."""

    # frob:tests src/frob/gates/_sys.py::sys_gate kind="unit"
    # invariant spec: [INV-041](invariants/INV-041.md)
    def test_selfaudit001_folds_selfconform_violation(self, tmp_path: Path) -> None:
        """GIVEN a node declaring a `code=` glob over a file that exercises
        a capability (`requests.get`, net) with NO matching `may`
        declaration, WHEN `sys_gate` (the production `frob check` entry
        point) runs THEN it FAILS with an unwaived SELFAUDIT001 ERROR
        naming the underlying SYS100 finding -- proving the fold actually
        fires through production, not just through `check_self_
        conformance` called directly."""
        _write(tmp_path, "design/m.strata", _SELFAUDIT_DESIGN_STRATA_UNDECLARED)
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        selfaudit = _by_rule(violations, "SELFAUDIT001")
        assert len(selfaudit) >= 1
        assert selfaudit[0].severity == Severity.ERROR
        assert "SYS100" in selfaudit[0].message
        assert "widget" in selfaudit[0].message

    # frob:tests src/frob/gates/_sys.py::sys_gate kind="unit"
    def test_selfaudit001_clean_model_no_violations(self, tmp_path: Path) -> None:
        """GIVEN a design model whose declared `may` capabilities are
        exactly what the bound code exercises WHEN `sys_gate` runs THEN it
        PASSES with zero SELFAUDIT001 findings -- the after-fix half of the
        same before/after fixture proof."""
        design = (
            "module m\n"
            'node widget : trusted { code "src/frob/widget/**"; may "net"; }\n'
        )
        _write(tmp_path, "design/m.strata", design)
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        assert _by_rule(violations, "SELFAUDIT001") == []

    # frob:tests src/frob/gates/_sys.py::sys_gate kind="unit"
    # frob:ticket T-2523
    def test_selfaudit001_folds_sys112_ambient_reason_violation(
        self, tmp_path: Path
    ) -> None:
        """T-2523: an ambient (via-less) `may` grant with no `// because:
        "..."` comment must fire SYS112 through the PRODUCTION `sys_gate`
        entry point -- proving `check_ambient_capability_reasons` (T-2503,
        built and unit-tested but never wired anywhere else until this
        ticket) is actually reachable from `frob check`, not just from its
        own test module."""
        design = (
            "module m\n"
            "node widget : trusted {\n"
            '    code "src/frob/widget/**";\n'
            '    may "exec";\n'
            "}\n"
        )
        _write(tmp_path, "design/m.strata", design)
        _write(tmp_path, "src/frob/widget/_io.py", "subprocess.run(['x'])\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        selfaudit = _by_rule(violations, "SELFAUDIT001")
        sys112 = [v for v in selfaudit if "SYS112" in v.message]
        assert len(sys112) == 1
        assert sys112[0].severity == Severity.ERROR
        assert "widget" in sys112[0].message
        assert "exec" in sys112[0].message

    # frob:tests src/frob/gates/_sys.py::sys_gate kind="unit"
    # frob:ticket T-2523
    def test_selfaudit001_sys112_silent_with_a_because_reason(
        self, tmp_path: Path
    ) -> None:
        """The after-fix half of the same before/after proof: the
        identical ambient grant, now carrying a `// because: "..."`
        comment, produces zero SYS112 findings through production
        `sys_gate`."""
        design = (
            "module m\n"
            "node widget : trusted {\n"
            '    code "src/frob/widget/**";\n'
            '    may "exec";  // because: "widget shells out to its own helper tools"\n'
            "}\n"
        )
        _write(tmp_path, "design/m.strata", design)
        _write(tmp_path, "src/frob/widget/_io.py", "subprocess.run(['x'])\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        selfaudit = _by_rule(violations, "SELFAUDIT001")
        assert [v for v in selfaudit if "SYS112" in v.message] == []

    # frob:tests src/frob/gates/_sys.py::sys_gate kind="unit"
    def test_selfaudit001_suppressed_on_design_load_error(self, tmp_path: Path) -> None:
        """A `.strata` file that fails to parse suppresses SELFAUDIT001
        entirely (matches DOC003/SYS001's suppression posture) -- a broken
        model cannot be honestly self-audited."""
        _write(tmp_path, "design/m.strata", "module m\nnode !!! broken\n")
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        assert _by_rule(violations, "SELFAUDIT001") == []
        assert _by_rule(violations, "SYS004") != []

    # frob:tests src/frob/gates/_sys.py::sys_gate kind="unit"
    def test_selfaudit001_folds_mode_conformance_violation(
        self, tmp_path: Path
    ) -> None:
        """T-1061: GIVEN a node declaring `access "RESOURCE" mode read`
        whose bound code performs a write-capable operation WHEN
        `sys_gate` (the production `frob check` entry point) runs THEN it
        FAILS with an unwaived SELFAUDIT001 ERROR naming the underlying
        SYS205 finding -- proving `check_mode_conformance` is actually
        wired into `frob check`, not just reachable via `frob sys audit`
        directly."""
        design = (
            "module m\n"
            'node widget : trusted { code "src/frob/widget/**"; '
            'access "cfg" mode read; }\n'
        )
        _write(tmp_path, "design/m.strata", design)
        _write(tmp_path, "src/frob/widget/_io.py", 'open("cfg.json", "w").write("x")\n')
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        selfaudit = _by_rule(violations, "SELFAUDIT001")
        matches = [v for v in selfaudit if "SYS205" in v.message]
        assert len(matches) >= 1
        assert matches[0].severity == Severity.ERROR
        assert "widget" in matches[0].message

    # frob:ticket T-1761
    # frob:tests src/frob/gates/_sys_selfaudit.py::_selfaudit_violations kind="unit"
    def test_selfaudit001_folds_stale_via_symbol_violation(
        self, tmp_path: Path
    ) -> None:
        """T-1761: GIVEN a node whose symbol-form `via` entry names a
        symbol that no longer exists WHEN `sys_gate` (the production
        `frob check` entry point) runs THEN it FAILS with an unwaived
        SELFAUDIT001 ERROR naming the underlying SYS109 finding, proving
        `check_stale_via_symbols` (built and unit-tested by T-1627) is
        actually wired into `frob check`, not just reachable in its own
        test module."""
        design = (
            "module m\n"
            'node app : trusted { code "app/site.py"; '
            'may "exec" via "app/site.py::gone"; }\n'
        )
        _write(tmp_path, "design/m.strata", design)
        _write(tmp_path, "app/site.py", "def run(cmd):\n    pass\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        selfaudit = _by_rule(violations, "SELFAUDIT001")
        matches = [v for v in selfaudit if "SYS109" in v.message]
        assert len(matches) >= 1
        assert matches[0].severity == Severity.ERROR
        assert "app" in matches[0].message
        assert "gone" in matches[0].message

    # frob:ticket T-1977
    # frob:tests src/frob/gates/_sys_selfaudit.py::_selfaudit_violations kind="unit"
    def test_selfaudit001_folds_capability_ratchet_violation(
        self, tmp_path: Path
    ) -> None:
        """T-1977: GIVEN a node's scoped via-list that has grown past the
        committed ratchet lock's `accepted_count` WHEN `sys_gate` (the
        production `frob check` entry point) runs THEN it FAILS with an
        unwaived SELFAUDIT001 ERROR naming the underlying SYS111 finding
        -- proving `capability_ratchet_violations` (built and unit-tested
        by T-1628) is actually wired into `frob check`, not just
        reachable in its own test module (the exact gap T-1977 closes,
        same shape T-1761 closed for SYS109)."""

        from frob.strata._effects import CAPABILITY_RATCHET_LOCK_REL

        design = (
            "module m\n"
            'node app : trusted { code "app/**"; '
            'may "fs.write" via "app/a.py", "app/b.py", "app/c.py"; }\n'
        )
        _write(tmp_path, "design/m.strata", design)
        _write(tmp_path, "app/a.py", "def f():\n    pass\n")
        _write(tmp_path, "app/b.py", "def f():\n    pass\n")
        _write(tmp_path, "app/c.py", "def f():\n    pass\n")
        _write(
            tmp_path,
            CAPABILITY_RATCHET_LOCK_REL,
            json.dumps(
                {
                    "entries": {
                        "app::fs.write": {
                            "accepted_count": 2,
                            "reason": "T-0001 baseline",
                        }
                    }
                }
            ),
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        selfaudit = _by_rule(violations, "SELFAUDIT001")
        matches = [v for v in selfaudit if "SYS111" in v.message]
        assert len(matches) >= 1
        assert matches[0].severity == Severity.ERROR
        assert "app" in matches[0].message
        assert "fs.write" in matches[0].message

    # frob:ticket T-1977
    # frob:tests src/frob/gates/_sys_selfaudit.py::_selfaudit_violations kind="unit"
    def test_selfaudit001_does_not_fire_below_the_ratchet_ceiling(
        self, tmp_path: Path
    ) -> None:
        """T-1977 re-verification: a via-list at or below the committed
        ceiling must stay silent through the PRODUCTION gate path too,
        not just in capability_ratchet_violations' own unit tests --
        proves the wiring did not accidentally widen the check's own
        silence conditions."""

        from frob.strata._effects import CAPABILITY_RATCHET_LOCK_REL

        design = (
            "module m\n"
            'node app : trusted { code "app/**"; '
            'may "fs.write" via "app/a.py", "app/b.py"; }\n'
        )
        _write(tmp_path, "design/m.strata", design)
        _write(tmp_path, "app/a.py", "def f():\n    pass\n")
        _write(tmp_path, "app/b.py", "def f():\n    pass\n")
        _write(
            tmp_path,
            CAPABILITY_RATCHET_LOCK_REL,
            json.dumps(
                {
                    "entries": {
                        "app::fs.write": {
                            "accepted_count": 2,
                            "reason": "T-0001 baseline",
                        }
                    }
                }
            ),
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        selfaudit = _by_rule(violations, "SELFAUDIT001")
        assert [v for v in selfaudit if "SYS111" in v.message] == []

    # frob:ticket T-1977
    # frob:tests src/frob/gates/_sys_selfaudit.py::_selfaudit_violations kind="unit"
    def test_selfaudit001_deleting_ratchet_lock_entry_still_fires(
        self, tmp_path: Path
    ) -> None:
        """T-1977 re-verification (bypass path 1, through the PRODUCTION
        gate): deleting a lock entry must not read as "unchecked" -- a
        missing entry is `accepted_count=0`, the strictest ceiling, so a
        nonzero observed via-list count fires immediately even with an
        EMPTY lock file, exactly as it does when calling
        `capability_ratchet_violations` directly."""

        from frob.strata._effects import CAPABILITY_RATCHET_LOCK_REL

        design = (
            "module m\n"
            'node app : trusted { code "app/**"; '
            'may "fs.write" via "app/a.py"; }\n'
        )
        _write(tmp_path, "design/m.strata", design)
        _write(tmp_path, "app/a.py", "def f():\n    pass\n")
        _write(tmp_path, CAPABILITY_RATCHET_LOCK_REL, json.dumps({"entries": {}}))
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        selfaudit = _by_rule(violations, "SELFAUDIT001")
        matches = [v for v in selfaudit if "SYS111" in v.message]
        assert len(matches) >= 1

    # frob:ticket T-1977
    # frob:tests src/frob/gates/_sys_selfaudit.py::_selfaudit_violations kind="unit"
    def test_selfaudit001_shrink_then_regrow_within_ceiling_stays_silent(
        self, tmp_path: Path
    ) -> None:
        """T-1977 re-verification (bypass path 2, through the PRODUCTION
        gate): re-approaching a previously-justified high-water mark
        (never exceeding it) after an intervening shrink must stay
        silent -- that ceiling was already earned once, so re-growing
        back up to it is ordinary movement, not laundered growth."""

        from frob.strata._effects import CAPABILITY_RATCHET_LOCK_REL

        design = (
            "module m\n"
            'node app : trusted { code "app/**"; '
            'may "fs.write" via "app/a.py", "app/b.py", "app/c.py"; }\n'
        )
        _write(tmp_path, "design/m.strata", design)
        _write(tmp_path, "app/a.py", "def f():\n    pass\n")
        _write(tmp_path, "app/b.py", "def f():\n    pass\n")
        _write(tmp_path, "app/c.py", "def f():\n    pass\n")
        # The lock's own ceiling was already justified at 3 (a prior,
        # separately-committed widening) -- re-growing back up to it,
        # even after an intervening shrink no longer reflected here,
        # must not re-trigger.
        _write(
            tmp_path,
            CAPABILITY_RATCHET_LOCK_REL,
            json.dumps(
                {
                    "entries": {
                        "app::fs.write": {
                            "accepted_count": 3,
                            "reason": "T-0002 justified widening to 3",
                        }
                    }
                }
            ),
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        selfaudit = _by_rule(violations, "SELFAUDIT001")
        assert [v for v in selfaudit if "SYS111" in v.message] == []

    # frob:tests src/frob/gates/_sys_selfaudit.py::_compliance_selfaudit_violations \
    # kind="unit"
    def test_selfaudit001_folds_compliance_violation(self, tmp_path: Path) -> None:
        """T-1314: GIVEN a design model with a Pii-clearance node carrying
        `exposure:public-web` and no `privacy-policy` attr (PRIVACY-NOTICE,
        `check_regulation_discharge`'s own litmus case) WHEN `_compliance_
        selfaudit_violations` (the function `sys_gate` calls) runs THEN it
        returns an unwaived SELFAUDIT001 WARN naming the underlying
        PRIVACY-NOTICE finding -- proving `evaluate_compliance` is now
        reachable through `frob check`'s own gate pipeline, not only
        through the separate `frob sys audit` CLI verb. Built directly
        against a constructed `DesignIds`/`KernelModel` (not a parsed
        `.strata` file) because the compliance vocabulary
        (`exposure:public-web`/`privacy-policy`/`subject:*`/
        `jurisdiction:*`) has no `.strata` grammar surface today -- only
        Python-constructed `Node.attrs` can express it (a disclosed,
        out-of-scope-for-this-ticket grammar gap, filed separately)."""
        from frob.gates._sys import _compliance_selfaudit_violations
        from frob.strata import DesignIds, KernelModel, Node

        store = Node(
            id="Store", trust="trusted", clearance="Pii", attrs=("exposure:public-web",)
        )
        model = KernelModel(nodes=(store,), flows=())
        design_ids = DesignIds(models=(model,))
        violations = _compliance_selfaudit_violations(tmp_path, design_ids, "design")
        selfaudit = _by_rule(violations, "SELFAUDIT001")
        matches = [v for v in selfaudit if "PRIVACY-NOTICE" in v.message]
        assert len(matches) >= 1
        assert matches[0].severity == Severity.WARN

    # frob:tests src/frob/gates/_sys_selfaudit.py::_compliance_selfaudit_violations \
    # kind="unit"
    def test_selfaudit001_compliance_clean_model_no_violations(
        self, tmp_path: Path
    ) -> None:
        """GIVEN a design model with no compliance-vocabulary attrs at all
        WHEN `_compliance_selfaudit_violations` runs THEN it returns zero
        SELFAUDIT001 findings -- the after-fix half of the same before/
        after fixture proof as `test_selfaudit001_folds_compliance_
        violation`."""
        from frob.gates._sys import _compliance_selfaudit_violations
        from frob.strata import DesignIds, KernelModel, Node

        store = Node(id="Store", trust="trusted", clearance="Pii")
        model = KernelModel(nodes=(store,), flows=())
        design_ids = DesignIds(models=(model,))
        violations = _compliance_selfaudit_violations(tmp_path, design_ids, "design")
        assert _by_rule(violations, "SELFAUDIT001") == []

    # frob:tests src/frob/gates/_sys_selfaudit.py::_compliance_selfaudit_violations \
    # kind="unit"
    def test_selfaudit001_compliance_suppressed_on_design_load_error(
        self, tmp_path: Path
    ) -> None:
        """A `DesignIds` carrying a load error suppresses the compliance
        fold entirely (matches every other `_selfaudit_violations` sub-
        family's suppression posture) -- a broken model cannot be honestly
        compliance-audited."""
        from frob.gates._sys import _compliance_selfaudit_violations
        from frob.strata import DesignIds, KernelModel, Node
        from frob.strata._design_load import DesignLoadError
        from frob.strata._errors import StrataError

        store = Node(
            id="Store", trust="trusted", clearance="Pii", attrs=("exposure:public-web",)
        )
        model = KernelModel(nodes=(store,), flows=())
        design_ids = DesignIds(
            models=(model,),
            errors=(
                DesignLoadError(
                    path="design/broken.strata", error=StrataError.ParseFailed
                ),
            ),
        )
        violations = _compliance_selfaudit_violations(tmp_path, design_ids, "design")
        assert violations == []


# frob:ticket T-3324
class TestSelfauditFindingsTouching:
    """`frob.gates._sys.selfaudit_findings_touching` (T-3324): the diff-
    scoped land-time enforcement seam -- `frob.tickets._land_squash`'s
    own `_refuse_if_selfaudit_findings_in_touched_files` calls this to
    decide whether a land should be refused, filtered to findings whose
    message names one of the land's own touched files."""

    # frob:tests src/frob/gates/_sys.py::selfaudit_findings_touching kind="unit"
    def test_no_design_dir_returns_empty(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", "def f(): pass\n")
        assert selfaudit_findings_touching(tmp_path, frozenset({"src/a.py"})) == ()

    # frob:tests src/frob/gates/_sys.py::selfaudit_findings_touching kind="unit"
    def test_substring_filter_is_exact_regardless_of_native_availability(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # Exercises the actual filtering logic directly against a mocked
        # `_selfaudit_violations` (never touching real `.strata` parsing,
        # unlike the other tests in this class) -- proves the filter
        # itself is correct independent of whether `strata_core` natives
        # are built in the current environment.
        from frob.gates._models import Severity, Violation

        _write(tmp_path, "design", "")
        (tmp_path / "design").unlink()
        (tmp_path / "design").mkdir()

        touching = Violation(
            rule="SELFAUDIT001",
            severity=Severity.ERROR,
            file="design",
            line=1,
            message="SELFAUDIT001: ... observed at src/a.py:3 but not declared",
        )
        not_touching = Violation(
            rule="SELFAUDIT001",
            severity=Severity.ERROR,
            file="design",
            line=1,
            message="SELFAUDIT001: ... observed at src/b.py:9 but not declared",
        )
        monkeypatch.setattr(
            "frob.gates._sys._selfaudit_violations",
            lambda root, design_ids, design_dir: [touching, not_touching],
        )
        monkeypatch.setattr(
            "frob.strata.load_design_ids", lambda root, design_dir: object()
        )

        findings = selfaudit_findings_touching(tmp_path, frozenset({"src/a.py"}))
        assert findings == (touching,)

    # frob:tests src/frob/gates/_sys.py::selfaudit_findings_touching kind="unit"
    def test_finding_in_touched_file_is_returned(self, tmp_path: Path) -> None:
        _write(tmp_path, "design/m.strata", _SELFAUDIT_DESIGN_STRATA_UNDECLARED)
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        findings = selfaudit_findings_touching(
            tmp_path, frozenset({"src/frob/widget/_io.py"})
        )
        assert len(findings) >= 1
        assert all("SYS100" in v.message for v in findings)

    # frob:tests src/frob/gates/_sys.py::selfaudit_findings_touching kind="unit"
    def test_finding_in_untouched_file_is_filtered_out(self, tmp_path: Path) -> None:
        # Same undeclared-capability model as the must-fire test above,
        # but the "touched files" set names an UNRELATED file -- this
        # land did not cause the drift and must not be blamed for it.
        _write(tmp_path, "design/m.strata", _SELFAUDIT_DESIGN_STRATA_UNDECLARED)
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        findings = selfaudit_findings_touching(
            tmp_path, frozenset({"src/frob/unrelated/_other.py"})
        )
        assert findings == ()

    # frob:tests src/frob/gates/_sys.py::selfaudit_findings_touching kind="unit"
    def test_clean_model_returns_empty(self, tmp_path: Path) -> None:
        design = (
            "module m\n"
            'node widget : trusted { code "src/frob/widget/**"; may "net"; }\n'
        )
        _write(tmp_path, "design/m.strata", design)
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        findings = selfaudit_findings_touching(
            tmp_path, frozenset({"src/frob/widget/_io.py"})
        )
        assert findings == ()


class TestSys111FindingsTouching:
    """`frob.gates._sys.sys111_findings_touching` (T-3575): SYS111
    (capability-ratchet growth) findings, attributed to the `.strata`
    file that DECLARES the tripped node rather than by message-substring
    match -- a SYS111 message has no file path in it at all (see the
    function's own docstring for the root cause)."""

    # frob:tests src/frob/gates/_sys.py::sys111_findings_touching kind="unit"
    def test_no_design_dir_returns_empty(self, tmp_path: Path) -> None:
        from frob.gates._sys import sys111_findings_touching

        _write(tmp_path, "src/a.py", "def f(): pass\n")
        assert sys111_findings_touching(tmp_path, frozenset({"src/a.py"})) == ()

    def _mock_ratchet_trip(self, monkeypatch, tmp_path: Path):
        """Common fixture for the two mock-boundary tests below: a fake
        design dir (so the early-exit is skipped), one fake SYS111
        violation on node `widget`/atom `exec`, and a fake `.strata` file
        declaring that node -- every strata_core-native call
        (`load_design_ids`/`merge_models`/`capability_ratchet_violations`/
        `parse_module`) is mocked so this exercises the attribution logic
        alone, independent of whether strata_core natives are built in
        the current environment (mirrors `TestSelfauditFindingsTouching.
        test_substring_filter_is_exact_regardless_of_native_availability`'s
        own convention)."""
        from typani import Ok

        import frob.strata as strata_mod
        from frob.strata import NodeDecl
        from frob.strata._ast import Module as RawModule
        from frob.strata._effects import CapabilityRatchetViolation

        (tmp_path / "design").mkdir()
        strata_file = tmp_path / "design" / "m.strata"
        strata_file.write_text(
            'module m\nnode widget : trusted { code "src/frob/widget/**"; '
            'may "exec" via "src/frob/widget/_run.py"; }\n'
        )

        trip = CapabilityRatchetViolation(
            node="widget",
            atom="exec",
            observed_count=5,
            accepted_count=3,
            detail="exec via-list on widget grew to 5 site(s), above the "
            "committed ratchet ceiling of 3",
        )
        raw_module = RawModule(
            name="m",
            nodes=(NodeDecl(id="widget", trust="trusted"),),
        )

        monkeypatch.setattr(
            strata_mod, "load_design_ids", lambda root, design_dir: object()
        )
        monkeypatch.setattr(strata_mod, "merge_models", lambda models: object())
        monkeypatch.setattr(
            strata_mod, "capability_ratchet_violations", lambda model, root: (trip,)
        )
        monkeypatch.setattr(strata_mod, "parse_module", lambda text: Ok(raw_module))
        monkeypatch.setattr(
            strata_mod,
            "load_design_ids",
            lambda root, design_dir: type(
                "DesignIds", (), {"errors": (), "models": (object(),)}
            )(),
        )
        return strata_file

    # frob:tests src/frob/gates/_sys.py::sys111_findings_touching kind="unit"
    def test_ratchet_trip_in_declaring_file_is_returned(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from frob.gates._sys import sys111_findings_touching

        self._mock_ratchet_trip(monkeypatch, tmp_path)
        findings = sys111_findings_touching(tmp_path, frozenset({"design/m.strata"}))
        assert len(findings) == 1
        assert "SYS111" in findings[0].message
        assert "widget" in findings[0].message

    # frob:tests src/frob/gates/_sys.py::sys111_findings_touching kind="unit"
    def test_ratchet_trip_in_untouched_file_is_filtered_out(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from frob.gates._sys import sys111_findings_touching

        self._mock_ratchet_trip(monkeypatch, tmp_path)
        findings = sys111_findings_touching(
            tmp_path, frozenset({"design/unrelated.strata"})
        )
        assert findings == ()


class TestDocptrFindingsTouching:
    """`frob.gates._sys.docptr_findings_touching` (T-3575): DOC004/DOC006
    (dangling doc anchor / unresolved file-path pointer) findings,
    attributed to `files` via EITHER the finding's own doc file or a
    path/anchor named in its message -- the gap T-3324's original land-
    time check left open entirely (a different gate module, never
    evaluated at land time at all)."""

    # frob:tests src/frob/gates/_sys.py::docptr_findings_touching kind="unit"
    def test_finding_in_touched_doc_is_returned(self, tmp_path: Path) -> None:
        from frob.gates._sys import docptr_findings_touching

        _git_init(tmp_path)
        _write(tmp_path, "docs/broken.md", "See `src/frob/gone_forever.py` here.\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        findings = docptr_findings_touching(tmp_path, frozenset({"docs/broken.md"}))
        assert any(v.file == "docs/broken.md" for v in findings)

    # frob:tests src/frob/gates/_sys.py::docptr_findings_touching kind="unit"
    def test_finding_naming_a_touched_target_is_returned(self, tmp_path: Path) -> None:
        from frob.gates._sys import docptr_findings_touching

        _git_init(tmp_path)
        _write(
            tmp_path,
            "docs/pointer.md",
            "See `src/frob/deleted_module.py` for details.\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        findings = docptr_findings_touching(
            tmp_path, frozenset({"src/frob/deleted_module.py"})
        )
        assert any("src/frob/deleted_module.py" in v.message for v in findings)

    # frob:tests src/frob/gates/_sys.py::docptr_findings_touching kind="unit"
    def test_finding_in_untouched_files_is_filtered_out(self, tmp_path: Path) -> None:
        from frob.gates._sys import docptr_findings_touching

        _git_init(tmp_path)
        _write(tmp_path, "docs/broken.md", "See `src/frob/gone_forever.py` here.\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        findings = docptr_findings_touching(tmp_path, frozenset({"docs/unrelated.md"}))
        assert findings == ()


class TestArchGateThresholds:
    """T-0373: arch_gate reads its long-function threshold from frob.toml's
    [arch] table (via frob.app.config.load_arch_config) instead of always
    using frob.arch.analyze_project's own conservative 30-line default."""

    def test_arch_gate_uses_calibrated_default_not_library_default(
        self, tmp_path: Path
    ) -> None:
        """No frob.toml at all: `frob.arch.analyze_project`'s own bare
        30-line default still flags the ~39-line complex function, but
        `arch_gate` -- which threads `load_arch_config`'s calibrated
        60-line default through -- does not. Proof the gate no longer
        silently uses `analyze_project`'s conservative defaults."""
        from frob.arch import analyze_project
        from frob.gates._arch import arch_gate

        _write(tmp_path, "src/mod.py", _complex_function_source("do_work"))

        raw_result = analyze_project(tmp_path / "src")
        assert "long-function" in {s.category for s in raw_result.suggestions}

        violations = arch_gate(tmp_path)
        assert not _by_rule(violations, "ARCH001")

    def test_arch001_respects_explicit_frob_toml_override(self, tmp_path: Path) -> None:
        """A frob.toml [arch] max_function_lines=20 override (well below
        both the library's 30-line default and the calibrated 60-line
        default) still fires ARCH001 -- proof arch_gate actually reads
        frob.toml, not just a hardcoded calibrated constant."""
        from frob.gates._arch import arch_gate

        _write(tmp_path, "src/mod.py", _complex_function_source("do_work"))
        _write(tmp_path, "frob.toml", "[arch]\nmax_function_lines = 20\n")
        violations = arch_gate(tmp_path)
        assert _by_rule(violations, "ARCH001")


class TestGateOrderSetEquality:
    """T-0438/T-0839: `_CANONICAL_GATE_ORDER` (T-0415's deterministic merge
    order) and `_ALL_GATES` (the set of every selectable gate name) must
    name the exact same gates. If a new gate is added to one but not the
    other, a gate could silently drop from `frob check` output (missing
    from the canonical order means it never gets merged back in) or
    `run_gates` could reject a gate name that was never made orderable --
    either way a quiet accounting bug, not a loud one, without this
    set-equality pin. T-0839 splits the single set-equality assertion into
    both drift directions individually so a failure names exactly which
    side drifted, and adds `_merge_canonical_order`'s own loud-failure
    behavior alongside it."""

    def test_canonical_gate_order_matches_all_gates(self) -> None:
        # frob:tests src/frob/gates/__init__.py::_merge_canonical_order
        # (the consumer of _CANONICAL_GATE_ORDER whose correctness this
        # set-equality invariant protects; the two constants are module-level
        # data the graph does not track as symbols, so bind to the function)
        # frob:waive COV006 reason="T-0525: module-level constant set-equality, never \
        # a call to _merge_canonical_order -- same \
        # sound-but-invisible-to-the-call-graph shape as \
        # TestProcessPoolGates.test_process_job_runs_in_a_separate_process above; \
        # symbol-exact now (T-0525), so this waiver covers only this test's own edge"
        from frob.gates import _ALL_GATES, _CANONICAL_GATE_ORDER

        assert set(_CANONICAL_GATE_ORDER) == _ALL_GATES, (
            "_CANONICAL_GATE_ORDER and _ALL_GATES have drifted apart -- "
            "every gate in _ALL_GATES must appear exactly once in "
            "_CANONICAL_GATE_ORDER so merge order stays deterministic and "
            "no gate silently drops from frob check output"
        )
        assert len(_CANONICAL_GATE_ORDER) == len(set(_CANONICAL_GATE_ORDER)), (
            "_CANONICAL_GATE_ORDER contains a duplicate gate name"
        )

    def test_all_gates_is_subset_of_canonical_order(self) -> None:
        # frob:tests src/frob/gates/__init__.py::_merge_canonical_order
        # frob:waive COV006 reason="T-0525: module-level constant set-difference, \
        # never a call to _merge_canonical_order -- same shape as \
        # test_canonical_gate_order_matches_all_gates above, symbol-exact so this \
        # waiver covers only this test's own edge"
        """T-0839 drift direction 1: every gate in `_ALL_GATES` (selectable,
        can produce real violations) must appear in `_CANONICAL_GATE_ORDER`
        -- this is exactly the T-0788 "compliance" incident: a gate added to
        `_ALL_GATES` but never added to the order tuple, whose findings
        `_merge_canonical_order` would silently drop."""
        from frob.gates import _ALL_GATES, _CANONICAL_GATE_ORDER

        missing_from_order = _ALL_GATES - set(_CANONICAL_GATE_ORDER)
        assert not missing_from_order, (
            f"gate(s) {sorted(missing_from_order)} are in _ALL_GATES but "
            "missing from _CANONICAL_GATE_ORDER -- their violations would "
            "be silently dropped from frob check output"
        )

    def test_canonical_order_names_no_nonexistent_gate(self) -> None:
        """T-0839 drift direction 2: every gate named in
        `_CANONICAL_GATE_ORDER` must actually exist in `_ALL_GATES` -- a
        stale/typo'd order entry naming a gate nothing ever registers is a
        harmless no-op today, but a silent one, and the inverse drift of
        the T-0788 incident.
        # frob:tests src/frob/gates/__init__.py::_merge_canonical_order
        """
        from frob.gates import _ALL_GATES, _CANONICAL_GATE_ORDER

        nonexistent = set(_CANONICAL_GATE_ORDER) - _ALL_GATES
        assert not nonexistent, (
            f"gate(s) {sorted(nonexistent)} are named in "
            "_CANONICAL_GATE_ORDER but do not exist in _ALL_GATES -- remove "
            "the stale entry or register the gate"
        )


class TestMergeCanonicalOrder:
    """T-0839: `_merge_canonical_order` must raise loudly on a gate name it
    cannot place, rather than silently dropping that gate's violations --
    the failure mode hit live when T-0788's "compliance" gate was briefly
    absent from `_CANONICAL_GATE_ORDER`."""

    @staticmethod
    def _violation(rule: str) -> Violation:
        return Violation(
            rule=rule,
            severity=Severity.ERROR,
            file="src/example.py",
            line=1,
            message=f"{rule}: synthetic test violation",
        )

    def test_unknown_gate_key_raises_with_name(self) -> None:
        # frob:tests src/frob/gates/__init__.py::_merge_canonical_order
        from frob.gates import GateOrderDriftError, _merge_canonical_order

        raw: dict[str, tuple[Violation, ...]] = {
            "not_a_real_gate": (self._violation("FAKE001"),)
        }
        with pytest.raises(GateOrderDriftError) as exc_info:
            _merge_canonical_order(raw)
        assert "not_a_real_gate" in str(exc_info.value)

    def test_all_current_gates_merge_without_raising(self) -> None:
        """Every name in `_ALL_GATES` must merge cleanly today -- this is
        the regression guard for the T-0788 incident itself: had this test
        existed then, it would have failed the moment "compliance" was
        added to `_ALL_GATES` without a matching order-tuple entry."""
        # frob:tests src/frob/gates/__init__.py::_merge_canonical_order
        from frob.gates import _ALL_GATES, _merge_canonical_order

        raw: dict[str, tuple[Violation, ...]] = {
            name: (self._violation("SYN001"),) for name in _ALL_GATES
        }
        merged = _merge_canonical_order(raw)
        assert len(merged) == len(_ALL_GATES)


# frob:ticket T-0499
# frob:ticket T-0972
class TestKnownGateRuleIds:
    """`known_gate_rule_ids()` is the public accessor strata's
    `caught_by` verification (THREAT006/COMPLIANCE004) needs to resolve
    rule-id-shaped references against; production callsites (T-0499)
    thread it in instead of silently defaulting to empty."""

    def test_returns_known_rule_id(self) -> None:
        """A real, stable gate rule id is present in the returned set."""
        assert "SEC001" in known_gate_rule_ids()

    def test_is_frozenset(self) -> None:
        """Return type is an immutable frozenset, not a mutable copy a
        caller could accidentally mutate shared state through."""
        assert isinstance(known_gate_rule_ids(), frozenset)

    # frob:ticket T-2441
    # frob:tests tests/gates_suite/test_sys.py::TestKnownGateRuleIds.test_bare_port001_registered  # noqa: E501
    def test_bare_port001_registered(self) -> None:
        """T-2441 (BUG002 repro): bare "PORT001" -- the T-2391 fail-loudly
        UNRESOLVED rule id `_port_selfcheck.py` constructs at
        `_unresolved_project_name_violation`, distinct from the
        PORT001-PATH/PORT001-IDENT pair T-2397 already registered -- must
        be a real, registered gate rule id. FAILS at T-2441's own parent
        (only PORT001-PATH/PORT001-IDENT were registered), PASSES once
        this ticket's _KNOWN_GATE_RULES entry lands."""
        assert "PORT001" in known_gate_rule_ids()

    # frob:ticket T-0924
    # T-0924: paid the allowlist down to empty -- every id T-0901 carried
    # here (COMPLIANCE001-004/HOST001/HOST002/HOST-BLAST/KRB001-004/
    # LINT001-005/PII001-004/RELWAIVE002/THREAT001-005) is now registered
    # in `_KNOWN_GATE_RULES` instead, so the drift-lock below actually
    # guards this batch rather than exempting it. PARSE002 (landed on main
    # concurrently with this pass) was folded straight into
    # `_KNOWN_GATE_RULES` instead of parked here, since it is exactly this
    # ticket's own defect class.
    #
    # frob:ticket T-0964
    # frob:ticket T-0966
    # T-0964 extended the drift-lock below to also resolve `rule=
    # CONST_NAME` references (not just inline `rule="..."` literals),
    # which surfaced a real, pre-existing gap: SYS100-102/SYS200-203 were
    # genuinely emitted via module-level constants in _selfconform.py/
    # _contention.py but were not yet added to `_KNOWN_GATE_RULES`. T-0966
    # added all seven entries there.
    #
    # frob:ticket T-1010
    # T-1010 inverted this registry: the scan itself (previously
    # duplicated inline here) is now importable production code
    # (`frob.gates._rule_id_scan`), and `_KNOWN_GATE_RULES` is the
    # generated-and-verified artifact it derives from. The former
    # `_KNOWN_ISSUE_ALLOWLIST` (an ad hoc "not yet registered" parking
    # lot, always empty in practice once the two historical batches above
    # were paid down) is retired in favor of `_rule_id_scan.
    # RETIRED_RULE_IDS`, which excludes ids at the SOURCE of generation
    # instead of at the point of comparison -- one manual knob, not two.
    # This test is now a generator-freshness check, not a hand-rolled scan.

    # frob:ticket T-0901
    # frob:ticket T-0924
    # frob:ticket T-0964
    # frob:ticket T-0972
    # frob:ticket T-1010
    # frob:tests \
    # tests/gates_suite/test_sys.py::TestKnownGateRuleIds.test_every_emitted_rule_liter\
    # al_is_known
    def test_every_emitted_rule_literal_is_known(self) -> None:
        """Generator-freshness drift-lock (T-1010, inverting the T-0964
        scan): every rule id `frob.gates._rule_id_scan.
        generated_gate_rule_ids()` reports live -- every `rule="..."`/
        `rule=CONST_NAME` construction under `_rule_id_scan.SCANNED_BASES`,
        minus `_rule_id_scan.RETIRED_RULE_IDS` -- must be a member of
        `known_gate_rule_ids()`. A gate/rule added without a matching
        `_KNOWN_GATE_RULES` entry fails loud immediately instead of
        silently reproducing the PARSE001/TICK005/REG011/PII011/PII012/
        SYSWAIVE002/THREAT006/PROTO004/DEC000 omission class (T-0903/
        T-0923/T-0901), including the T-0964 variant where the id is only
        ever referenced via a module-level constant rather than an inline
        literal."""
        repo_root = Path(__file__).resolve().parents[2]
        generated = generated_gate_rule_ids(repo_root)
        known = known_gate_rule_ids()
        found = scan_emitted_rule_ids(repo_root)
        unknown = {
            rule_id: found[rule_id] for rule_id in generated if rule_id not in known
        }
        assert not unknown, (
            "rule id(s) constructed in src/frob/gates or src/frob/strata "
            "but missing from _KNOWN_GATE_RULES (paste in the entry "
            "frob.gates._rule_id_scan.generated_gate_rule_ids() now "
            f"reports): {unknown}"
        )

    # frob:ticket T-1010
    # frob:tests \
    # tests/gates_suite/test_sys.py::TestKnownGateRuleIds.test_scan_finds_a_synthetic_r\
    # ule_id
    def test_scan_finds_a_synthetic_rule_id(self, tmp_path: Path) -> None:
        """A fresh gate emitting a rule id via an inline `rule="..."`
        literal is picked up by `scan_emitted_rule_ids` with no hand edit
        to any registry -- the acceptance shape T-1010 exists to
        guarantee."""
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        (gates_dir / "_synthetic.py").write_text(
            'def synthetic_gate():\n    return Violation(rule="ZZZTEST001")\n'
        )

        found = scan_emitted_rule_ids(tmp_path)

        assert "ZZZTEST001" in found
        assert found["ZZZTEST001"] == "src/frob/gates/_synthetic.py:2"

    # frob:ticket T-1010
    # frob:tests \
    # tests/gates_suite/test_sys.py::TestKnownGateRuleIds.test_scan_resolves_const_name\
    # _reference
    def test_scan_resolves_const_name_reference(self, tmp_path: Path) -> None:
        """A `rule=CONST_NAME` reference resolved against a module-level
        `CONST_NAME = "RULE123"` assignment -- the T-0964 class this
        scanner must keep covering, not just inline literals."""
        strata_dir = tmp_path / "src" / "frob" / "strata"
        strata_dir.mkdir(parents=True)
        (strata_dir / "_synthetic.py").write_text(
            'ZZZ_CONST = "ZZZTEST002"\n\n\ndef synthetic_gate():\n'
            "    return Violation(rule=ZZZ_CONST)\n"
        )

        found = scan_emitted_rule_ids(tmp_path)

        assert found.get("ZZZTEST002") == "src/frob/strata/_synthetic.py:5"

    # frob:ticket T-1010
    # frob:tests \
    # tests/gates_suite/test_sys.py::TestKnownGateRuleIds.test_retired_id_stays_excluded
    def test_retired_id_stays_excluded(self, tmp_path: Path) -> None:
        """An id on the retired list stays out of
        `generated_gate_rule_ids()`'s output even though the scan itself
        would otherwise find it -- the one manual exclusion knob T-1010
        leaves in place."""
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        (gates_dir / "_synthetic.py").write_text(
            'def synthetic_gate():\n    return Violation(rule="ZZZTEST003")\n'
        )

        found = scan_emitted_rule_ids(tmp_path)
        assert "ZZZTEST003" in found

        generated = generated_gate_rule_ids(tmp_path, retired=frozenset({"ZZZTEST003"}))

        assert "ZZZTEST003" not in generated


# frob:ticket T-1264
class TestRuleFixability:
    """T-1264: `generated_fixability()` is the AUTHORITY for which tier
    (auto/verified/assisted/manual) each known gate rule id belongs to,
    derived from the actual `TIER_A_HANDLERS`/`TIER_B_HANDLERS`/
    `TIER_C_EMITTERS` dispatch tables -- `_KNOWN_RULE_FIXABILITY` is the
    checked-in GENERATED artifact kept in sync with it, same
    generated-verified shape `TestKnownGateRuleIds` already exercises for
    rule-id scanning itself."""

    # frob:ticket T-1264
    def test_every_known_rule_id_maps_to_exactly_one_tier(self) -> None:
        """GIVEN every known gate rule id THEN `generated_fixability()`
        maps it to exactly one of auto/verified/assisted/manual, with
        `manual` the correct default for a rule with no handler in any
        table."""
        mapping = generated_fixability(known_gate_rule_ids())
        assert set(mapping) == set(known_gate_rule_ids())
        assert all(
            tier in {"auto", "verified", "assisted", "manual"}
            for tier in mapping.values()
        )
        # A rule genuinely absent from every Tier A/B/C table is manual --
        # not silently omitted from the mapping.
        assert mapping["SEC001"] == "manual"

    # frob:ticket T-1264
    def test_conflicting_registration_raises_fixabilityconflict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """GIVEN a rule id registered in more than one of
        TIER_A_HANDLERS/TIER_B_HANDLERS/TIER_C_EMITTERS WHEN
        `generated_fixability()` runs THEN it raises `FixabilityConflict`
        rather than silently picking one."""
        import frob.gates._fix_engine_tier_b as tier_b_module

        monkeypatch.setattr(
            tier_b_module,
            "TIER_B_HANDLERS",
            {"DOC007": lambda *a, **k: []},
        )
        with pytest.raises(FixabilityConflict):
            generated_fixability(frozenset({"DOC007"}))

    # frob:ticket T-1264
    def test_checked_in_literal_matches_a_fresh_scan(self) -> None:
        """GIVEN the checked-in `_KNOWN_RULE_FIXABILITY` literal WHEN it
        drifts from a fresh `generated_fixability()` scan (a handler added
        without updating the literal) THEN this test fails loud -- the
        same drift-lock shape `TestKnownGateRuleIds`'s own scan-vs-literal
        test already applies to rule ids, applied here to tiers. Only the
        non-"manual" entries are checked-in (manual is the honest default
        for everything else), so the comparison expands the fresh scan
        down to non-manual entries before comparing."""
        fresh = generated_fixability(known_gate_rule_ids())
        fresh_non_manual = {k: v for k, v in fresh.items() if v != "manual"}
        assert fresh_non_manual == _KNOWN_RULE_FIXABILITY

    # frob:ticket T-1264
    def test_sync_gate_rule_fixability_backfills_missing_field(
        self, tmp_path: Path
    ) -> None:
        """GIVEN check-coverage.yaml's CHK-GATE-<rule> entries THEN each
        carries a fixability: field kept in sync the same idempotent way
        gate_rule_entries already is: a fresh entry with no field gets one
        backfilled from `generated_fixability`, and a second run is a
        no-op (idempotent, matching `sync_gate_rule_entries`'s own
        contract)."""
        from frob.registry._staleness import sync_gate_rule_fixability

        registry = tmp_path / "check-coverage.yaml"
        registry.write_text(
            "schema_version: 1\n"
            "gate_rule_entries:\n"
            '  - id: "CHK-GATE-DOC007"\n'
            '    name: "DOC007 is a live, enforced gate rule"\n'
            '    disposition: "handled_by:DOC007"\n'
            "    cross_refs: []\n"
            "gate_rule_total: 1\n"
        )
        result = sync_gate_rule_fixability(registry, frozenset({"DOC007"}))
        assert result.is_ok
        assert result.danger_ok == ("DOC007",)
        written = registry.read_text()
        assert 'fixability: "auto"' in written
        import yaml

        parsed = yaml.safe_load(written)  # must stay valid YAML after backfill
        entry = parsed["gate_rule_entries"][0]
        assert entry["fixability"] == "auto"
        assert entry["disposition"] == "handled_by:DOC007"

        second = sync_gate_rule_fixability(registry, frozenset({"DOC007"}))
        assert second.is_ok
        assert second.danger_ok == ()


# frob:ticket T-0459
# frob:ticket T-2740
class TestRenderLintGate:
    """RENDER001: bare stdout write outside frob.render
    (docs/modules/render.md#renderer)."""

    def _init_repo(self, tmp_path: Path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)

    def _commit(self, tmp_path: Path) -> None:
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-qm", "c"], cwd=tmp_path, check=True)

    # frob:tests tests/gates_suite/test_sys.py::TestRenderLintGate.test_bare_print_fires
    def test_bare_print_fires(self, tmp_path: Path) -> None:
        """A bare `print(...)` in a runner-shaped file fires RENDER001."""
        from frob.gates._render_lint import render_lint_gate

        self._init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob" / "app"
        pkg.mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (pkg / "__init__.py").write_text("")
        (pkg / "offender_runner.py").write_text("def run():\n    print('hello')\n")
        self._commit(tmp_path)

        violations = render_lint_gate(tmp_path)

        hits = _by_rule(violations, "RENDER001")
        offender_hits = [v for v in hits if v.file == "src/frob/app/offender_runner.py"]
        assert len(offender_hits) == 1
        assert offender_hits[0].line == 2

    # frob:tests \
    # tests/gates_suite/test_sys.py::TestRenderLintGate.test_render_package_exempt
    def test_render_package_exempt(self, tmp_path: Path) -> None:
        """`src/frob/render/` itself is the one sanctioned home for these
        calls (`Renderer._emit`'s own `print`) and is never scanned."""
        from frob.gates._render_lint import render_lint_gate

        self._init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob" / "render"
        pkg.mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (pkg / "__init__.py").write_text("")
        (pkg / "_renderer.py").write_text(
            "def _emit(line, stream):\n    print(line, file=stream)\n"
        )
        self._commit(tmp_path)

        violations = render_lint_gate(tmp_path)

        assert _by_rule(violations, "RENDER001") == []

    # frob:tests \
    # tests/gates_suite/test_sys.py::TestRenderLintGate.test_stderr_directed_print_is_s\
    # ilent
    def test_stderr_directed_print_is_silent(self, tmp_path: Path) -> None:
        """A `print(..., file=sys.stderr)` call is never flagged --
        INV-RENDER-SOLE-STDOUT governs stdout only."""
        from frob.gates._render_lint import render_lint_gate

        self._init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob" / "app"
        pkg.mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (pkg / "__init__.py").write_text("")
        (pkg / "offender_runner.py").write_text(
            "import sys\n\n\ndef run():\n    print('oops', file=sys.stderr)\n"
        )
        self._commit(tmp_path)

        violations = render_lint_gate(tmp_path)

        assert _by_rule(violations, "RENDER001") == []

    # frob:tests \
    # tests/gates_suite/test_sys.py::TestRenderLintGate.test_unparseable_file_fires_par\
    # se001
    # frob:ticket T-0897
    def test_unparseable_file_fires_parse001(self, tmp_path: Path) -> None:
        """A file with a Python syntax error fires PARSE001 instead of
        being silently dropped from the scan with zero Violation (T-0897)."""
        from frob.gates._render_lint import render_lint_gate

        self._init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob" / "app"
        pkg.mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (pkg / "__init__.py").write_text("")
        (pkg / "broken_runner.py").write_text("def run(:\n    pass\n")
        self._commit(tmp_path)

        violations = render_lint_gate(tmp_path)

        hits = _by_rule(violations, "PARSE001")
        offender_hits = [v for v in hits if v.file == "src/frob/app/broken_runner.py"]
        assert len(offender_hits) == 1
        assert offender_hits[0].severity == Severity.ERROR

    # frob:tests \
    # tests/gates_suite/test_sys.py::TestRenderLintGate.test_claude_hooks_dir_exempt
    # frob:ticket T-2719
    def test_claude_hooks_dir_exempt(self, tmp_path: Path) -> None:
        """A bare `print(...)` under `.claude/hooks/` does NOT fire
        RENDER001 (T-2719): hook scripts run standalone with no `frob.*`
        import, so `frob.render.Renderer` is structurally unreachable --
        this is the false-positive shape T-1614's waive audit found 11
        individually-honest per-line waivers papering over. Also proves
        the path is genuinely SCANNED (not merely absent from the tree,
        which would prove nothing) by nesting one level deep."""
        from frob.gates._render_lint import render_lint_gate

        self._init_repo(tmp_path)
        (tmp_path / "src" / "frob").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        hooks = tmp_path / ".claude" / "hooks" / "sub"
        hooks.mkdir(parents=True)
        (hooks / "offender-hook.py").write_text("print('standalone hook output')\n")
        self._commit(tmp_path)

        violations = render_lint_gate(tmp_path)

        assert _by_rule(violations, "RENDER001") == []

    # frob:tests \
    # tests/gates_suite/test_sys.py::TestRenderLintGate.test_fleet_status_file_exempt
    # frob:ticket T-2719
    def test_fleet_status_file_exempt(self, tmp_path: Path) -> None:
        """A bare `print(...)` in `scripts/fleet_status.py` does NOT fire
        RENDER001 (T-2719) -- same standalone, no-frob-import constraint
        as `.claude/hooks/`, named as one file rather than a `scripts/`
        prefix (see `test_exemption_is_file_scoped_not_dir_scoped` below)."""
        from frob.gates._render_lint import render_lint_gate

        self._init_repo(tmp_path)
        (tmp_path / "src" / "frob").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        scripts = tmp_path / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "fleet_status.py").write_text("print('fleet status output')\n")
        self._commit(tmp_path)

        violations = render_lint_gate(tmp_path)

        assert _by_rule(violations, "RENDER001") == []

    # frob:tests \
    # tests/gates_suite/test_sys.py::TestRenderLintGate.test_exemption_is_file_scoped_n\
    # ot_dir_scoped
    # frob:ticket T-2719
    def test_exemption_is_file_scoped_not_dir_scoped(self) -> None:
        """Control on the exemption predicate itself: `scripts/
        fleet_status.py` is exempt as a single NAMED file, not a blanket
        `scripts/` directory prefix -- a sibling script under `scripts/`
        (e.g. `bump_version.py`, which genuinely imports `frob.*` and
        stays fully subject to RENDER001) must NOT read as exempt. Checked
        directly against `_EXEMPT_PREFIXES` rather than through a full
        `render_lint_gate` scan, because `scripts/` is deliberately NOT
        one of the extra scan pathspecs -- `bump_version.py` was never
        scanned before this ticket and stays unscanned after it (only the
        one named `fleet_status.py` file was added to the scan), so a
        gate-level 'still fires' fixture for it would prove nothing new;
        the risk this control actually guards against is the exemption
        STRING becoming an accidental directory prefix, e.g. a future
        edit shortening `"scripts/fleet_status.py"` to `"scripts/"`."""
        from frob.gates._render_lint import _EXEMPT_PREFIXES

        assert "scripts/fleet_status.py".startswith(_EXEMPT_PREFIXES)
        assert ".claude/hooks/offender.py".startswith(_EXEMPT_PREFIXES)
        assert not "scripts/bump_version.py".startswith(_EXEMPT_PREFIXES)
        assert not "scripts/other_tool.py".startswith(_EXEMPT_PREFIXES)

    # frob:tests \
    # tests/gates_suite/test_sys.py::TestRenderLintGate.test_scan_now_covers_hooks_and_\
    # fleet_status
    # frob:ticket T-2719
    def test_scan_now_covers_hooks_and_fleet_status(self, tmp_path: Path) -> None:
        """BUG002 repro (T-2719): before this fix, `.claude/hooks/**` and
        `scripts/fleet_status.py` were NOT scanned by RENDER001 at all --
        `_tracked_python_files` queried a single hardcoded `src/frob`
        `git ls-files` pathspec -- so T-1614's 11 `frob:waive RENDER001`
        directives in those files were suppressing nothing (verified live
        against this repo: those directives sit on lines the pre-fix gate
        never even enumerated). This asserts the scan-level fact directly:
        a `.claude/hooks/` file and `scripts/fleet_status.py` are now
        enumerated by the gate's own tracked-file helper -- structurally
        impossible before this ticket, since the old helper only ever
        queried `src/frob`."""
        from frob.gates._render_lint import _tracked_python_files

        self._init_repo(tmp_path)
        (tmp_path / "src" / "frob").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        hooks = tmp_path / ".claude" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "some-hook.py").write_text("print('x')\n")
        scripts = tmp_path / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "fleet_status.py").write_text("print('y')\n")
        self._commit(tmp_path)

        files = _tracked_python_files(tmp_path)

        assert ".claude/hooks/some-hook.py" in files
        assert "scripts/fleet_status.py" in files

    # frob:ticket T-2740
    def test_render001_scans_true_for_a_real_scanned_file(self, tmp_path: Path) -> None:
        """`render001_scans` (T-2740): a plain `src/frob/**.py` file is
        genuinely in RENDER001's scan set."""
        from frob.gates._render_lint import render001_scans

        self._init_repo(tmp_path)
        (tmp_path / "src" / "frob").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "mod.py").write_text("print('x')\n")
        self._commit(tmp_path)

        assert render001_scans(tmp_path, "src/frob/mod.py") is True

    # frob:ticket T-2740
    def test_render001_scans_false_for_an_exempt_path(self, tmp_path: Path) -> None:
        """`render001_scans` (T-2740): `.claude/hooks/` is exempt by
        `_EXEMPT_PREFIXES` -- the exact structural signal T-2733's own
        waiver removal relied on."""
        from frob.gates._render_lint import render001_scans

        self._init_repo(tmp_path)
        hooks = tmp_path / ".claude" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "some-hook.py").write_text("print('x')\n")
        self._commit(tmp_path)

        assert render001_scans(tmp_path, ".claude/hooks/some-hook.py") is False

    # frob:ticket T-2740
    def test_render001_scans_false_for_a_path_outside_any_pathspec(
        self, tmp_path: Path
    ) -> None:
        """`render001_scans` (T-2740): a file outside every scanned
        pathspec (not `src/frob`, not `.claude/hooks`, not the single
        `scripts/fleet_status.py` file) is structurally unreachable by
        RENDER001 -- the shape T-2719 found 11 waivers sitting on."""
        from frob.gates._render_lint import render001_scans

        self._init_repo(tmp_path)
        other = tmp_path / "somewhere" / "else"
        other.mkdir(parents=True)
        (other / "mod.py").write_text("print('x')\n")
        self._commit(tmp_path)

        assert render001_scans(tmp_path, "somewhere/else/mod.py") is False
