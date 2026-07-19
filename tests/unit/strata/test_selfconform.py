"""Unit tests for T-0150 self-conformance: SYS100/SYS101/SYS102 reconciled
against `design/frob.strata`'s `code`/`may` declarations
(docs/strata/selfconform.md).

POST-REVIEW REWORK: the reviewed mechanism is `Node.attrs`'s `code=<glob>`
convention (`bind_code`, T-0078) + `Node.may` (T-0079/T-0113), the SAME
kernel-level fields `test_code_binding.py`/`test_effects.py` already
exercise -- no `frob.toml` table, matching `_selfconform.py`'s rework.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.strata import (
    SYS_STALE_DESIGN,
    SYS_UNDECLARED_INTERFACE,
    SYS_UNMODELED_CODE,
    KernelModel,
    Node,
    Waiver,
    check_self_conformance,
)
from frob.strata._code_binding import CodeBinding
from frob.strata._effects import _KIND_MAP
from frob.strata._selfconform import (
    _EXTENDED_KINDS,
    _observed_extended_kinds_by_node,
    _sorted_capability_files,
)
from frob.strata._waive import STALE_WAIVER_RULE
from frob.vet._capability import _PATTERNS, SCANNED_LANGUAGES, language_for
from frob.vet._capability_registry import LANGUAGES


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestUndeclaredInterfaceCore:
    """SYS100 for net/fs-write/exec -- delegated verbatim to THREAT004's
    `check_capability_conformance` (docs/strata/selfconform.md#the-three-rules)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_core_undeclared_interface_fires(self, tmp_path: Path):
        _write(
            tmp_path, "src/frob/widget/_io.py", "import requests\nrequests.get('x')\n"
        )
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [
            v for v in result.danger_ok.violations if v.rule == SYS_UNDECLARED_INTERFACE
        ]
        assert any(v.node == "widget" and "net" in v.detail for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_core_undeclared_interface_discharges_once_declared(self, tmp_path: Path):
        _write(
            tmp_path, "src/frob/widget/_io.py", "import requests\nrequests.get('x')\n"
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE for v in result.danger_ok.violations
        )


class TestUndeclaredInterfaceExtended:
    """SYS100 for eval/env/ffi/install-hook -- the slice THREAT004
    structurally cannot see (docs/strata/selfconform.md#the-three-rules)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_extended_undeclared_interface_fires(self, tmp_path: Path):
        _write(tmp_path, "src/frob/widget/_io.py", "x = compile('1', '<s>', 'eval')\n")
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [
            v for v in result.danger_ok.violations if v.rule == SYS_UNDECLARED_INTERFACE
        ]
        assert any(v.node == "widget" and "eval" in v.detail for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_extended_undeclared_interface_discharges_once_declared(
        self, tmp_path: Path
    ):
        _write(tmp_path, "src/frob/widget/_io.py", "x = compile('1', '<s>', 'eval')\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("eval",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE for v in result.danger_ok.violations
        )


class TestStaleDesign:
    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_stale_design_fires(self, tmp_path: Path):
        """A `may` capability declared for a node never observed in its
        `code=`-bound files is SYS101."""
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_STALE_DESIGN]
        assert any(v.node == "widget" and "net" in v.detail for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_stale_design_discharges_once_observed(self, tmp_path: Path):
        _write(
            tmp_path, "src/frob/widget/_io.py", "import requests\nrequests.get('x')\n"
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(v.rule == SYS_STALE_DESIGN for v in result.danger_ok.violations)


class TestUnmodeledCode:
    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_unmodeled_code_fires(self, tmp_path: Path):
        """A `src/frob/` directory claimed by no node's `code=` glob at
        all is SYS102, even with zero observable capabilities."""
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        _write(tmp_path, "src/frob/orphan/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_UNMODELED_CODE]
        assert any(v.node == "orphan" for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_unmodeled_code_discharges_once_mapped(self, tmp_path: Path):
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        _write(tmp_path, "src/frob/orphan/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
                Node(id="other", trust="trusted", attrs=("code=src/frob/orphan/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNMODELED_CODE for v in result.danger_ok.violations
        )


class TestNonPythonLanguageWiring:
    """T-0169: the logand.app pilot found `frob sys audit` never scanned
    TS/JS at all -- `bind_code` walks only `.py` (T-0078, correctly, since
    it also backs Python-import conformance), and self-conformance used to
    hand that same `.py`-only binding straight to the capability scan, so
    a TS/JS (or Rust/C-C++) file was invisible to SYS100/SYS101 no matter
    what it did. `_capability_binding` closes that gap; these tests prove
    it end to end through the real `check_self_conformance` entrypoint,
    not just at the binding-helper level."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_typescript_undeclared_capability_fires(self, tmp_path: Path):
        """A `.ts` file with an obvious browser capability (fetch +
        localStorage) bound by a node's `code=` glob is SYS100 -- the exact
        repro that was silently missed before T-0169 (bind_code never even
        saw the file, so `check_self_conformance` returned zero
        violations for an ambient node)."""
        _write(
            tmp_path,
            "src/frob/widget/app.ts",
            "fetch('https://evil.example/x');\nlocalStorage.setItem('a', 'b');\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = {
            v.detail
            for v in result.danger_ok.violations
            if v.rule == SYS_UNDECLARED_INTERFACE and v.node == "widget"
        }
        assert any("fetch_url" in detail for detail in hit)
        assert any("client_storage" in detail for detail in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_typescript_undeclared_capability_discharges_once_declared(
        self, tmp_path: Path
    ):
        """The same TS fixture with `may=("fetch_url", "client_storage")`
        declared produces no SYS100 for those kinds -- proves the TS scan
        result actually reaches the declared/observed join, not just the
        raw scanner."""
        _write(
            tmp_path,
            "src/frob/widget/app.ts",
            "fetch('https://evil.example/x');\nlocalStorage.setItem('a', 'b');\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fetch_url", "client_storage"),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE and v.node == "widget"
            for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_typescript_stale_design_fires(self, tmp_path: Path):
        """`may=("fetch_url",)` declared on a node whose `code=`-bound `.ts`
        file never calls `fetch`/etc. is SYS101 for a non-Python language,
        the same drift check Python already had."""
        _write(tmp_path, "src/frob/widget/app.ts", "console.log('noop');\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fetch_url",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_STALE_DESIGN]
        assert any(v.node == "widget" and "fetch_url" in v.detail for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::_sorted_capability_files kind="unit"
    def test_sorted_capability_files_includes_typescript(self, tmp_path: Path):
        """Direct proof `_sorted_capability_files` (the file walk feeding
        `_capability_binding`) actually yields a `.ts` path, not just that
        the end-to-end violation happens to appear for some other reason."""
        _write(tmp_path, "src/frob/widget/app.ts", "fetch('x');\n")
        found = _sorted_capability_files(tmp_path)
        assert any(p.suffix == ".ts" for p in found)

    # frob:tests src/frob/strata/_selfconform.py::_sorted_capability_files kind="unit"
    def test_sorted_capability_files_honors_graph_exclude(self, tmp_path: Path):
        """T-0274: a [graph].exclude dir (e.g. bundled frontend build
        output) must be pruned the same way bind_code's walk is, not just
        the built-in skip-dir set -- graphite FROBLEMS.md 2026-07-18 #1."""
        _write(tmp_path, "server/static/bundle.js", "fetch('x');\n")
        _write(tmp_path, "server/routes.ts", "fetch('x');\n")
        (tmp_path / "frob.toml").write_text(
            '[graph]\nexclude = ["server/static/**"]\n', encoding="utf-8"
        )
        found = _sorted_capability_files(tmp_path)
        rels = {p.relative_to(tmp_path).as_posix() for p in found}
        assert "server/routes.ts" in rels
        assert "server/static/bundle.js" not in rels


class TestCoreUndeclaredInterfaceNonPython:
    """REVIEWER-CAUGHT REJECT ROUND (T-0169): the extended-kinds/SYS101
    fix above still left `_core_undeclared_violations` (net/fs-write/exec,
    delegated to THREAT004's `check_capability_conformance`) on the raw
    Python-only `bind_code` binding -- so a `.ts` `axios.get(...)` or a
    `.rs` `Command::new(...).spawn()` under a `code=` glob produced ZERO
    SYS100 and a SPURIOUS SYS102 instead, exactly reproducing the original
    bug for the raw net/exec/fs-write kinds the pilot most needs caught.
    `check_capability_conformance` is language-generic (`_effects.py::
    _line_effects` uses `language_for`/`_PATTERNS`, no Python-specific
    parsing) so this was purely a wiring omission, not a real scope
    boundary -- `check_self_conformance` now hands `_core_undeclared_
    violations` and `_unmodeled_violations` the SAME `_capability_binding`
    superset as SYS100-extended/SYS101."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_typescript_core_net_undeclared_fires(self, tmp_path: Path):
        """A `.ts` file calling `axios.get(...)` (raw `net`, THREAT004's
        core delegated kind) with no `may` declaration is SYS100, and NOT
        also a spurious SYS102 for the same directory."""
        _write(
            tmp_path,
            "src/frob/widget/app.ts",
            "import axios from 'axios';\naxios.get('https://evil.example/x');\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        violations = result.danger_ok.violations
        assert any(
            v.rule == SYS_UNDECLARED_INTERFACE
            and v.node == "widget"
            and "net" in v.detail
            for v in violations
        )
        assert not any(v.rule == SYS_UNMODELED_CODE for v in violations)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_typescript_core_net_discharges_once_declared(self, tmp_path: Path):
        """The same `axios.get(...)` fixture with `may=("net",)` declared
        produces no SYS100 for `net` -- proves the TS core-kind scan
        actually reaches the declared/observed join, not just the raw
        scanner."""
        _write(
            tmp_path,
            "src/frob/widget/app.ts",
            "import axios from 'axios';\naxios.get('https://evil.example/x');\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE and v.node == "widget"
            for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_rust_core_exec_undeclared_fires(self, tmp_path: Path):
        """A `.rs` file calling `Command::new(...).spawn()` (raw `exec`)
        with no `may` declaration is SYS100, and NOT also a spurious
        SYS102 for the same directory."""
        _write(
            tmp_path,
            "src/frob/widget/main.rs",
            'use std::process::Command;\nfn f() { Command::new("ls").spawn(); }\n',
        )
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        violations = result.danger_ok.violations
        assert any(
            v.rule == SYS_UNDECLARED_INTERFACE
            and v.node == "widget"
            and "exec" in v.detail
            for v in violations
        )
        assert not any(v.rule == SYS_UNMODELED_CODE for v in violations)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_rust_core_exec_discharges_once_declared(self, tmp_path: Path):
        """The same `Command::new(...).spawn()` fixture with
        `may=("exec",)` declared produces no SYS100 for `exec`."""
        _write(
            tmp_path,
            "src/frob/widget/main.rs",
            'use std::process::Command;\nfn f() { Command::new("ls").spawn(); }\n',
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("exec",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE and v.node == "widget"
            for v in result.danger_ok.violations
        )


class TestLanguageCoverageDriftLock:
    # frob:tests src/frob/strata/_selfconform.py::_sorted_capability_files kind="unit"
    def test_scanned_languages_equals_registry_languages(self):
        """T-0169 drift lock: the set of languages self-conformance (and
        `vet`) actually reach via `language_for`/`_EXT_LANGUAGE` must equal
        the set `_capability_registry.LANGUAGES` claims support (T-0158's
        coverage matrix). If a new language column is ever added to the
        registry without a matching `_EXT_LANGUAGE` extension entry (or
        vice versa), this fails immediately instead of that language
        silently going unscanned the way TS/JS did before this ticket."""
        assert SCANNED_LANGUAGES == frozenset(LANGUAGES)

    def test_language_for_is_consistent_with_scanned_languages(self):
        """Every language `language_for` can ever return is a member of
        `SCANNED_LANGUAGES` -- keeps the constant honest against the
        function it is meant to characterize, not just hand-copied."""
        samples = {
            "a.py": "python",
            "a.ts": "typescript",
            "a.tsx": "typescript",
            "a.js": "typescript",
            "a.rs": "rust",
            "a.c": "c-cpp",
            "a.cpp": "c-cpp",
        }
        for name, expected in samples.items():
            resolved = language_for(Path(name))
            assert resolved == expected
            assert resolved in SCANNED_LANGUAGES


class TestExtendedKindsDriftLock:
    # frob:tests src/frob/strata/_selfconform.py::_observed_extended_kinds_by_node kind="unit"
    def test_extended_kinds_is_disjoint_from_kind_map(self):
        """`_EXTENDED_KINDS` (SYS100's new-code slice) and `_KIND_MAP`'s keys
        (THREAT004's delegated slice) must never overlap -- a shared kind
        would double-count SYS100 for it. Also must union to EVERY kind
        `vet._capability._PATTERNS` defines (docs/strata/selfconform.md
        #kind-space-drift-lock): if `_KIND_MAP` or `_PATTERNS` ever grows a
        kind neither set accounts for, this test fails first, loudly."""
        assert _EXTENDED_KINDS.isdisjoint(_KIND_MAP.keys())
        all_pattern_kinds = frozenset(
            kind for table in _PATTERNS.values() for kind in table
        )
        assert _EXTENDED_KINDS | frozenset(_KIND_MAP.keys()) == all_pattern_kinds

    def test_observed_extended_kinds_by_node_only_ever_yields_extended_kinds(
        self, tmp_path: Path
    ):
        """`_observed_extended_kinds_by_node` intersects its raw scan against
        `_EXTENDED_KINDS` (the `& _EXTENDED_KINDS` in its body) -- exercise it
        against a real file containing an `eval(` needle (a `_KIND_MAP`-
        disjoint kind per the test above) and confirm the observed set is
        both non-empty and a subset of `_EXTENDED_KINDS`, never leaking a
        `_KIND_MAP` kind through. Ties the drift-lock constants to the
        function that actually consumes them, not just to each other."""
        src = tmp_path / "danger.py"
        src.write_text("def f(x):\n    return eval(x)\n")
        binding = CodeBinding(owner={"danger.py": "node.danger"})

        observed = _observed_extended_kinds_by_node(binding, tmp_path)

        assert observed == {"node.danger": frozenset({"eval"})}
        assert observed["node.danger"] <= _EXTENDED_KINDS
        assert observed["node.danger"].isdisjoint(_KIND_MAP.keys())


class TestWaiverChannel:
    """T-0174: a `Node.waives` entry suppresses its matching SYS finding
    (kept in `report.waived`, never dropped) and a waiver matching nothing
    is reported as a new SYSWAIVE002 violation (drift-lock)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    # frob:waive PERF001 reason="an any()-generator plus a two-clause list comprehension over one tiny fixture result, not a hot loop"
    def test_matching_waiver_moves_violation_to_waived(self, tmp_path: Path):
        """SYS100 is multi-instance-per-node (T-0174 REJECT round), so the
        waiver must name the exact capability kind (`net`, matching
        `requests.get`'s observed effect) as a `SYS100:net` sub-target --
        a bare `SYS100` waiver would be an elaborate-adjacent-invalid
        value this test does not construct."""
        _write(
            tmp_path, "src/frob/widget/_io.py", "import requests\nrequests.get('x')\n"
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    waives=(
                        Waiver(
                            rule=f"{SYS_UNDECLARED_INTERFACE}:net",
                            reason="pilot fixture, tracked in T-0174",
                        ),
                    ),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE for v in result.danger_ok.violations
        )
        waived = [
            v
            for v in result.danger_ok.waived
            if v.rule == SYS_UNDECLARED_INTERFACE and v.node == "widget"
        ]
        assert len(waived) == 1
        assert "WAIVED" in waived[0].detail
        assert "pilot fixture, tracked in T-0174" in waived[0].detail
        assert "SYS100:net" in waived[0].detail

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_stale(self, tmp_path: Path):
        """`widget` declares no capability at all, so SYS100:net never
        fires -- the waiver on it matches zero findings and must be
        reported as a new SYSWAIVE002 violation, not silently accepted."""
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    waives=(
                        Waiver(
                            rule=f"{SYS_UNDECLARED_INTERFACE}:net",
                            reason="never fires -- stale waiver litmus",
                        ),
                    ),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        stale = [v for v in result.danger_ok.violations if v.rule == STALE_WAIVER_RULE]
        assert len(stale) == 1
        assert stale[0].node == "widget"

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_sub_target_waiver_does_not_suppress_a_different_kind(self, tmp_path: Path):
        """T-0174 REJECT round, the critical fixture at the
        `check_self_conformance` layer: `widget` observes BOTH `net`
        (`requests.get`) and `exec` (`subprocess.run`) undeclared -- two
        SYS100 findings on the same node. Waiving only `SYS100:net` must
        NOT suppress the `SYS100:exec` finding."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nimport subprocess\n"
            "requests.get('x')\nsubprocess.run(['ls'])\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    waives=(
                        Waiver(
                            rule=f"{SYS_UNDECLARED_INTERFACE}:net",
                            reason="net leg tracked separately, litmus fixture",
                        ),
                    ),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        remaining = [
            v for v in result.danger_ok.violations if v.rule == SYS_UNDECLARED_INTERFACE
        ]
        assert len(remaining) == 1
        assert remaining[0].capability == "exec"
        waived = [
            v for v in result.danger_ok.waived if v.rule == SYS_UNDECLARED_INTERFACE
        ]
        assert len(waived) == 1
        assert waived[0].capability == "net"


class TestRealGateGreen:
    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="integration"
    def test_repo_design_and_declarations_are_self_conformant(self):
        """`design/frob.strata`'s real `code`/`may` declarations, run
        against the REAL `src/frob/` tree, produce zero SYS100/SYS101/
        SYS102 violations -- the T-0150 gate-green assertion. Skips (does
        not xfail) when the native strata_core extension isn't installed,
        matching every other `.strata`-parsing test's guard in this suite."""
        pytest.importorskip("strata_core")
        from frob.strata._design_load import load_design_ids
        from frob.strata._sysdoc import merge_models

        root = Path(__file__).resolve().parents[3]
        ids = load_design_ids(root, "design")
        assert not ids.errors, f"design load failed: {ids.errors}"
        model = merge_models(ids.models)

        result = check_self_conformance(model, root)
        assert result.is_ok, result.err
        violations = result.danger_ok.violations
        assert violations == (), [(v.rule, v.node, v.detail) for v in violations]
