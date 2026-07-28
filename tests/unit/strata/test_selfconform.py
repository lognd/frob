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
    SYS_COVERAGE_TOTALITY,
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
from frob.strata._errors import StrataError
from frob.strata._selfconform import (
    _EXTENDED_KINDS,
    _dedupe_sys100_extended_against_core,
    _observed_all_kinds_by_node,
    _observed_extended_kinds_by_node,
    _sorted_capability_files,
)
from frob.strata._selfconform import SelfConformViolation as _SCV
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
    """SYS100 for eval/ffi/install-hook -- the slice THREAT004
    structurally cannot see (docs/strata/selfconform.md#the-three-rules).
    T-1075: `env` moved OUT of this extended slice into THREAT004's own
    core delegated join (`env-read`/`env-write` -> `env.read`/`env.write`
    via `_effects.py::_KIND_MAP`), same as `fs-read`'s own T-0717
    promotion."""

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


class TestUndeclaredInterfaceCrossPassDedup:
    """T-0266: `_core_undeclared_violations` and `_extended_kind_violations`
    are independent SYS100 producers joined against the same `(node,
    capability)` space -- a capability observed by BOTH passes must
    surface as ONE finding, not two."""

    def test_dedupe_helper_drops_extended_when_core_already_reports_same_site(self):
        """Unit-level: the merge helper itself, isolated from any real
        scan -- two `SelfConformViolation`s sharing `(node, capability)`,
        one from each pass, collapse to zero surviving extended entries
        (core is kept whole by the caller, `_collect_sys_violations`)."""
        core = [
            _SCV(
                rule=SYS_UNDECLARED_INTERFACE,
                node="widget",
                detail="capability 'net' observed at src/frob/widget/_io.py:2 "
                "but not declared",
                capability="net",
            )
        ]
        extended = [
            _SCV(
                rule=SYS_UNDECLARED_INTERFACE,
                node="widget",
                detail="capability 'net' observed but not declared",
                capability="net",
            )
        ]
        assert _dedupe_sys100_extended_against_core(core, extended) == []

    def test_dedupe_helper_keeps_distinct_node_or_capability_sites(self):
        """A distinct `(node, capability)` pair on the extended side is
        never dropped -- only an exact `(node, capability)` match against
        core is filtered."""
        core = [
            _SCV(
                rule=SYS_UNDECLARED_INTERFACE,
                node="widget",
                detail="capability 'net' observed but not declared",
                capability="net",
            )
        ]
        extended = [
            _SCV(
                rule=SYS_UNDECLARED_INTERFACE,
                node="widget",
                detail="capability 'eval' observed but not declared",
                capability="eval",
            ),
            _SCV(
                rule=SYS_UNDECLARED_INTERFACE,
                node="other",
                detail="capability 'net' observed but not declared",
                capability="net",
            ),
        ]
        assert _dedupe_sys100_extended_against_core(core, extended) == extended

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_same_site_observed_by_both_passes_yields_one_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """End-to-end via `check_self_conformance`: widen `_EXTENDED_KINDS`
        to also cover `exec` (simulating the kind-vocabulary drift the
        helper's docstring warns about -- `_KIND_MAP`/`_EXTENDED_KINDS`
        are not today statically enforced disjoint) so ONE real
        `subprocess.run` site is genuinely observed by BOTH
        `_core_undeclared_violations` (THREAT004 delegate) and
        `_extended_kind_violations` for the SAME `(node, capability)`.
        `exec` (unlike T-0771's `net-connect`/`net-listen`, which
        `_KIND_MAP` renormalizes to the dotted `net.connect`/`net.listen`
        spelling) is the one `_KIND_MAP` entry that maps to itself, so it
        is still the kind whose raw and THREAT004-normalized spellings are
        identical -- the exact collision this test needs to reproduce.
        Asserts exactly one SYS100 finding survives, not two."""
        import frob.strata._selfconform as selfconform_mod

        monkeypatch.setattr(
            selfconform_mod, "_EXTENDED_KINDS", frozenset({"exec", *_EXTENDED_KINDS})
        )
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import subprocess\nsubprocess.run(['ls'])\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hits = [
            v
            for v in result.danger_ok.violations
            if v.rule == SYS_UNDECLARED_INTERFACE
            and v.node == "widget"
            and v.capability == "exec"
        ]
        assert len(hits) == 1


class TestUndeclaredInterfaceFsReadAlias:
    """T-0304 follow-up: the `fs`/`fs-read` backward-compat alias only
    covered SYS101 (stale design); SYS100 (undeclared interface) still
    fired for a broader `may "fs"` declaration against a read-only
    observation, since `fs-read` is only ever matched against `_EXTENDED_
    KINDS & declared` and a bare `fs` declaration is not itself an
    extended kind. This class exercises the SYS100 direction directly
    (docs/strata/selfconform.md#fs-read-fs-write)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_broad_fs_declaration_discharges_read_only_observation(
        self, tmp_path: Path
    ):
        """A node that declares the legacy, broader `may "fs"` must not
        fire SYS100 for a real read-only observation: `fs` is a superset
        of `fs-read` and already covers it (live repro: lithos's
        rust_core/regolith_py/stdlib_records/tooling/demos/vscode_ext all
        declare `may "fs"` and all six fired SYS100 for `fs-read` before
        this fix)."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').read_text()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE and v.capability == "fs-read"
            for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_narrow_fs_read_declaration_does_not_cover_fs_read(self, tmp_path: Path):
        """A node that already declares `may "fs-read"` directly is
        unaffected by the alias (it never needed it): a read-only
        observation is discharged with no SYS100 finding, same as
        before this fix."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').read_text()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs-read",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE and v.capability == "fs-read"
            for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_fs_read_only_declaration_still_fires_on_fs_write_observation(
        self, tmp_path: Path
    ):
        """Asymmetry check (the point of the split, module docstring):
        a node declaring ONLY the narrower `may "fs-read"` must still
        fire (via THREAT004's core delegate) when a real fs-write-class
        effect is observed -- narrower declarations never cover broader
        observations, only the reverse."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').write_text('y')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs-read",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [
            v for v in result.danger_ok.violations if v.rule == SYS_UNDECLARED_INTERFACE
        ]
        # T-0717: a fs-write-class observation now reports the precise
        # "fs.write" spelling, not the old ambiguous bare "fs".
        assert any(v.node == "widget" and v.capability == "fs.write" for v in hit)


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

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_legacy_fs_declaration_discharges_on_read_only_observation(
        self, tmp_path: Path
    ):
        """T-0018 (graphite adoption): graphite's `node core` declares
        `may "fs"` for genuinely-real read-only filesystem access
        (`Path.read_text()`/`json.loads()`, no writes anywhere) and SYS101
        fired "declared but never observed" because the scanner only ever
        emitted the write-derived `fs` kind. A pre-existing bare `may "fs"`
        declaration must be backward-compatibly satisfied by a read-only
        observation now that `fs-read` is a distinct, real kind."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').read_text()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(v.rule == SYS_STALE_DESIGN for v in result.danger_ok.violations)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_fs_read_declaration_discharges_on_read_only_observation(
        self, tmp_path: Path
    ):
        """A node that declares the new, more honest `may "fs-read"` (rather
        than the legacy bare `fs`) is satisfied directly by a read-only
        observation too."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').read_text()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs-read",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(v.rule == SYS_STALE_DESIGN for v in result.danger_ok.violations)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_fs_read_declaration_stays_stale_when_only_writes_observed(
        self, tmp_path: Path
    ):
        """The alias is one-directional: `fs-read` declared but only a
        write observed must still be stale (a real distinction, not a
        blanket merge of the two kinds)."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').write_text('y')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs-read",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_STALE_DESIGN]
        assert any(v.node == "widget" and "fs-read" in v.detail for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    # invariant spec: [INV-026](invariants/INV-026.md)
    def test_stale_design_skips_node_fully_within_graph_exclude(self, tmp_path: Path):
        """T-0310: a node whose ENTIRE `code=` glob resolves only to
        `[graph].exclude`'d paths (aprog-public's activities/slidegen/
        content shape) has no file capability observation could ever see --
        SYS101 'declared but never observed' is a category error for it,
        not real design drift, and must NOT fire no matter what `may` it
        declares."""
        _write(tmp_path, "src/frob/widget/excluded/_io.py", "x = 1\n")
        (tmp_path / "frob.toml").write_text(
            '[graph]\nexclude = ["src/frob/widget/excluded/**"]\n', encoding="utf-8"
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/excluded/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(v.rule == SYS_STALE_DESIGN for v in result.danger_ok.violations)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_stale_design_still_fires_when_node_has_non_excluded_file(
        self, tmp_path: Path
    ):
        """The T-0310 skip must NOT weaken SYS101 for a node that has at
        least one observable (non-excluded) file: a genuinely-undeclared-
        vs-observed mismatch on that file must still fire, exactly as
        before -- only the fully-excluded case is skipped."""
        _write(tmp_path, "src/frob/widget/excluded/_io.py", "x = 1\n")
        _write(tmp_path, "src/frob/widget/_main.py", "x = 1\n")
        (tmp_path / "frob.toml").write_text(
            '[graph]\nexclude = ["src/frob/widget/excluded/**"]\n', encoding="utf-8"
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
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_STALE_DESIGN]
        assert any(v.node == "widget" and "net" in v.detail for v in hit)


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


class TestUnmodeledCodeForeignFileGranularity:
    """G4 (docs/audits/strata.md): a FOREIGN file in an already-modeled
    directory (or a loose file directly under `src/frob/`) used to escape
    SYS102 entirely, since the OLD grain marked a whole directory 'owned'
    the moment ANY file in it was non-FOREIGN, and `_top_level_dirs` never
    even iterated files (only directories). Confirmed as a live gap before
    this ticket's fix (a `frob.strata._selfconform.check_self_conformance`
    call against such a fixture returned zero violations)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_foreign_file_in_otherwise_owned_directory_fires(self, tmp_path: Path):
        """A directory with ONE globbed file and one un-globbed sibling
        must fire SYS102 for the un-globbed file specifically -- the
        directory being "otherwise modeled" must not hide it."""
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        _write(tmp_path, "src/frob/widget/backdoor.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/_io.py",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_UNMODELED_CODE]
        assert any(v.node == "src/frob/widget/backdoor.py" for v in hit)
        # The directory as a whole must NOT also fire (it IS partially
        # modeled) -- only the specific unbound file.
        assert not any(v.node == "widget" for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_loose_top_level_file_fires(self, tmp_path: Path):
        """A `.py` file placed directly under `src/frob/` (no
        subdirectory at all) with no node's `code=` glob binding it must
        fire SYS102 -- `_top_level_dirs` only ever walked directories, so
        this file was invisible to every SYS10x rule before the fix."""
        _write(tmp_path, "src/frob/loose_module.py", "x = 1\n")
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_UNMODELED_CODE]
        assert any(v.node == "src/frob/loose_module.py" for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_loose_top_level_file_discharges_once_globbed(self, tmp_path: Path):
        """The same loose file, once a node's `code=` glob actually binds
        it, produces no SYS102."""
        _write(tmp_path, "src/frob/loose_module.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="loose",
                    trust="trusted",
                    attrs=("code=src/frob/loose_module.py",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNMODELED_CODE for v in result.danger_ok.violations
        )


class TestUnmodeledCodeMissingPackageRoot:
    """T-0211: `_PACKAGE_ROOT` ("src/frob") is frob's own layout -- a repo
    with no `src/frob/` at all (i.e. every non-frob repo) must not have
    SYS102 fire, and must not emit a WARNING-level log about it (sibling-
    repo pilot P2 found this warning firing on every audit run of every
    non-frob repo, reading as "the self-conformance proof is vacuous" even
    though the other checks genuinely ran)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_missing_package_root_produces_no_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ):
        """A repo with no `src/frob/` directory at all gets zero SYS102
        violations and zero WARNING-level selfconform log records --
        frob's package-root assumption must not leak into generic repos."""
        _write(tmp_path, "src/other/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(Node(id="other", trust="trusted", attrs=("code=src/other/**",)),)
        )
        with caplog.at_level("DEBUG", logger="frob"):
            result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNMODELED_CODE for v in result.danger_ok.violations
        )
        warnings = [r for r in caplog.records if r.levelno >= 30]
        assert not any("selfconform" in r.getMessage() for r in warnings), warnings


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
    # frob:waive COV006 reason="T-0536: SCANNED_LANGUAGES (frob.vet._capability) and \
    # LANGUAGES (frob.vet._capability_registry) are both module-level constants \
    # asserted for set equality here -- neither is ever CALLED by this test's body, so \
    # there is no call-graph edge for the graph to find regardless of which symbol \
    # frob:tests names. Retargeting the directive straight at SCANNED_LANGUAGES was \
    # tried and rejected: DRIFT002 then reports the ref as unresolvable (module-level \
    # assignments are not graph nodes), trading one false positive for another. Same \
    # module-constant-drift-lock shape as T-0516's tests/test_gates.py waiver."
    def test_scanned_languages_equals_registry_languages(self):
        """T-0169 drift lock: the set of languages self-conformance (and
        `vet`) actually reach via `language_for`/`_EXT_LANGUAGE` must equal
        the set `_capability_registry.LANGUAGES` claims support (T-0158's
        coverage matrix). If a new language column is ever added to the
        registry without a matching `_EXT_LANGUAGE` extension entry (or
        vice versa), this fails immediately instead of that language
        silently going unscanned the way TS/JS did before this ticket.

        T-0170 adds `kotlin` as a fully registry-backed language (its
        `_DangerousOperation`/`_MatrixExcuse` entries live in
        `_capability_registry.py` like every other language), so the lock
        stays the strict equality it always was -- no carve-out."""
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
            "a.kt": "kotlin",
            "a.kts": "kotlin",
        }
        for name, expected in samples.items():
            resolved = language_for(Path(name))
            assert resolved == expected
            assert resolved in SCANNED_LANGUAGES


class TestExtendedKindsDriftLock:
    # frob:tests src/frob/strata/_selfconform.py::_observed_extended_kinds_by_node \
    # kind="unit"
    # frob:waive COV006 reason="T-0536: _EXTENDED_KINDS/_KIND_MAP/_PATTERNS are \
    # module-level constants this test asserts set operations over -- never CALLED, so \
    # there is no call-graph edge regardless of binding. Retargeting straight at \
    # _EXTENDED_KINDS was tried and rejected: DRIFT002 then reports the ref as \
    # unresolvable (module-level assignments are not graph nodes), trading one false \
    # positive for another. Same module-constant-drift-lock shape as T-0516's \
    # tests/test_gates.py waiver."
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

    # frob:tests tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock.test_observed_all_kinds_by_node_normalizes_through_kind_map  # noqa: E501
    def test_observed_all_kinds_by_node_normalizes_through_kind_map(
        self, tmp_path: Path
    ):
        """`_observed_all_kinds_by_node`'s SYS101 sibling: a real
        `subprocess.run(...)` call scans as the raw `"exec"` kind, which
        `_KIND_MAP` maps to itself (`"exec" -> "exec"`) -- confirms the
        normalized-view wrapper reaches a `_KIND_MAP`-covered kind end to
        end, not just `_observed_extended_kinds_by_node`'s disjoint-kind
        case above."""
        src = tmp_path / "spawn.py"
        src.write_text('import subprocess\ndef f():\n    subprocess.run(["ls"])\n')
        binding = CodeBinding(owner={"spawn.py": "node.spawn"})

        observed = _observed_all_kinds_by_node(binding, tmp_path)

        assert observed == {"node.spawn": frozenset({_KIND_MAP["exec"]})}


class TestWaiverChannel:
    """T-0174: a `Node.waives` entry suppresses its matching SYS finding
    (kept in `report.waived`, never dropped) and a waiver matching nothing
    is reported as a new SYSWAIVE002 violation (drift-lock)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_matching_waiver_moves_violation_to_waived(self, tmp_path: Path):
        """SYS100 is multi-instance-per-node (T-0174 REJECT round), so the
        waiver must name the exact capability kind (`net.connect`, T-0771's
        precise spelling now that `net` is wired -- matching
        `requests.get`'s observed effect) as a `SYS100:net.connect` sub-
        target -- a bare `SYS100` waiver would be an elaborate-adjacent-
        invalid value this test does not construct."""
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
                            rule=f"{SYS_UNDECLARED_INTERFACE}:net.connect",
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
        assert "SYS100:net.connect" in waived[0].detail

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
        `check_self_conformance` layer: `widget` observes BOTH `net.connect`
        (`requests.get`, T-0771's precise spelling) and `exec`
        (`subprocess.run`) undeclared -- two SYS100 findings on the same
        node. Waiving only `SYS100:net.connect` must NOT suppress the
        `SYS100:exec` finding."""
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
                            rule=f"{SYS_UNDECLARED_INTERFACE}:net.connect",
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
        assert waived[0].capability == "net.connect"


class TestRealGateGreen:
    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance \
    # kind="integration"
    def test_repo_design_and_declarations_are_self_conformant(self):
        """`design/frob.strata`'s real `code`/`may` declarations, run
        against the REAL `src/frob/` tree, produce zero SYS100/SYS101/
        SYS102/SYS103 violations -- the T-0150 gate-green assertion, UNCHANGED
        and still strict (T-0667: SYS103/SYS-COV joins it at zero too --
        `_coverage_totality_scan_prefix` restricts SYS103 to `_PACKAGE_ROOT`
        on frob's own tree specifically, docs/modules/strata.md#sys-cov-
        coverage-totality-sys103-t-0667, so it does not fire on `tests/**`/
        `scripts/**`/`frob-core/src/**`/`strata-core/src/**`, which
        `design/frob.strata` does not model). Skips (does not xfail) when
        the native strata_core extension isn't installed, matching every
        other `.strata`-parsing test's guard in this suite."""
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


class TestBindingErrorPropagation:
    """`check_self_conformance` must propagate `bind_code`'s error
    unchanged (deny by default, never a silent partial scan) --
    docstring's `Err` clause."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_ambiguous_code_binding_propagates_as_err(self, tmp_path: Path):
        """Two nodes whose `code=` globs both match the same file make
        `bind_code` return `Err(AmbiguousCodeBinding)`; that must surface
        unchanged from `check_self_conformance`, not be swallowed."""
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="a", trust="trusted", attrs=("code=src/frob/widget/**",)),
                Node(id="b", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.AmbiguousCodeBinding


class TestModeQualifiedFsStaleDesign:
    """T-0717 acceptance clause 1: a node declaring precisely `may
    "fs.read"` and whose bound code only reads discharges SYS101 narrowly
    (only `fs.read` itself can satisfy it)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_fs_read_declaration_discharges_on_read_only_code(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').read_text()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs.read",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(v.rule == SYS_STALE_DESIGN for v in result.danger_ok.violations)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_fs_read_declaration_stays_stale_when_only_writes_observed(
        self, tmp_path: Path
    ):
        """The precise declaration does NOT discharge on the OTHER mode --
        a `fs.read`-only declarer whose code only writes is still stale."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').write_text('y')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs.read",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_STALE_DESIGN]
        assert any(v.node == "widget" and v.capability == "fs.read" for v in hit)


class TestCoverageTotality:
    """SYS103 (SYS-COV, T-0667): a `FOREIGN` file the binding-aware
    scanner observes ANY capability in fires, on any root -- not just
    `src/frob/` (docs/modules/strata.md#sys-cov-coverage-totality-sys103-t-0667)."""

    # frob:tests src/frob/strata/_selfconform.py::_coverage_totality_violations kind="unit"  # noqa: E501
    def test_foreign_file_with_capability_fires_sys103(self, tmp_path: Path):
        """A file with an observed `net` effect and no node's `code=`
        glob binding it fires SYS103, even though SYS100/SYS101 (which
        only reconcile BOUND files) have nothing to say about it."""
        _write(
            tmp_path,
            "src/frob/orphan/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(nodes=())
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [
            v for v in result.danger_ok.violations if v.rule == SYS_COVERAGE_TOTALITY
        ]
        assert any(
            v.node == "src/frob/orphan/_io.py" and "net" in v.detail for v in hit
        )

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_bound_file_discharges_sys103(self, tmp_path: Path):
        """The same capable file, once a node's `code=` glob binds it,
        produces no SYS103 -- 'every module bound to a node' is silent --
        REGARDLESS of whether that node declares `may` for the observed
        kind. SYS103's only question is binding, never conformance
        (module docstring); the node here declares NO `may` at all, so
        SYS100 fires for the SAME site while SYS103 stays silent,
        proving the two rules are answering genuinely different
        questions rather than one masking the other."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import subprocess\nsubprocess.run(['ls'])\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_COVERAGE_TOTALITY for v in result.danger_ok.violations
        )
        assert any(
            v.rule == SYS_UNDECLARED_INTERFACE for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::_coverage_totality_violations kind="unit"  # noqa: E501
    def test_foreign_capability_free_file_does_not_fire_sys103(self, tmp_path: Path):
        """A `FOREIGN` file with zero observed capabilities (plain data)
        does not fire SYS103 -- only capable-but-unbound code is the
        failure mode SYS-COV catches (SYS102 still catches this same file
        under its own, frob-tree-only rule -- unaffected here)."""
        _write(tmp_path, "src/frob/orphan/_io.py", "x = 1\n")
        model = KernelModel(nodes=())
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_COVERAGE_TOTALITY for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::_coverage_totality_violations kind="unit"  # noqa: E501
    def test_fires_outside_src_frob_layout(self, tmp_path: Path):
        """SYS103 is repo-general, unlike SYS102's `_PACKAGE_ROOT`
        hardcoding: a capable, unbound file OUTSIDE `src/frob/` entirely
        still fires."""
        _write(
            tmp_path,
            "app/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(nodes=())
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [
            v for v in result.danger_ok.violations if v.rule == SYS_COVERAGE_TOTALITY
        ]
        assert any(v.node == "app/widget/_io.py" for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::_coverage_totality_violations kind="unit"  # noqa: E501
    def test_sys103_waivable_as_bare_rule(self, tmp_path: Path):
        """A bare `waive "SYS103"` clause suppresses the finding -- SYS103
        is NOT in `MULTI_INSTANCE_WAIVER_FAMILIES`, so it must not require
        a sub-target, unlike SYS100/SYS101 (docs/strata/selfconform.md's
        SYS102 waiver precedent: `apply_waivers` reads `Node.waives`
        keyed by `node.id`, and a SYS102/SYS103 finding's `node` field is
        the unbound file's OWN path, matching SYS102's `waive "SYS102"`
        convention -- a `Node` entry with id == the file path, `code=`-
        free, exists purely to carry the waiver, same shape a `.strata`
        author would declare)."""
        _write(
            tmp_path,
            "src/frob/orphan/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="src/frob/orphan/_io.py",
                    trust="trusted",
                    waives=(Waiver(rule=SYS_COVERAGE_TOTALITY, reason="test waiver"),),
                ),
            ),
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_COVERAGE_TOTALITY for v in result.danger_ok.violations
        )
        assert any(v.rule == SYS_COVERAGE_TOTALITY for v in result.danger_ok.waived)

    # frob:tests src/frob/strata/_selfconform.py::_coverage_totality_violations kind="unit"  # noqa: E501
    def test_repo_unrestricted_scan_is_clean(self, monkeypatch: pytest.MonkeyPatch):
        """T-1079 (SYS103's 264-finding follow-up): `design/frob.strata`
        now models `tests/**`/`scripts/**`/`frob-core/src/**`/
        `strata-core/src/**` (the `testsuite`/`scripts_ops`/
        `strata_core_native`/`frob_core_native` nodes,
        docs/modules/strata.md's "Modeled: `_PACKAGE_ROOT` restriction's
        264-finding follow-up" section) -- this proves it directly by
        bypassing `_coverage_totality_scan_prefix`'s `_PACKAGE_ROOT`
        restriction (monkeypatched to always return `None`, i.e. the
        SAME unrestricted whole-`root` scan T-0667 measured 264 findings
        under before this ticket) and asserting `check_self_conformance`
        against the REAL, merged `design/` model and the REAL repo tree
        still returns zero SYS100/SYS101/SYS102/SYS103 violations. The
        production `SELFAUDIT001` gate still runs the `_PACKAGE_ROOT`-
        restricted scan (`_coverage_totality_scan_prefix` itself is
        unchanged, out of this ticket's scope) -- this test proves the
        MODEL has caught up, independent of whether the live gate has
        been widened to consult it yet (follow-up ticket, Done report)."""
        pytest.importorskip("strata_core")
        from frob.strata import _selfconform as sc
        from frob.strata._design_load import load_design_ids
        from frob.strata._sysdoc import merge_models

        root = Path(__file__).resolve().parents[3]
        ids = load_design_ids(root, "design")
        assert not ids.errors, f"design load failed: {ids.errors}"
        model = merge_models(ids.models)

        monkeypatch.setattr(sc, "_coverage_totality_scan_prefix", lambda r: None)

        result = sc.check_self_conformance(model, root)
        assert result.is_ok, result.err
        violations = result.danger_ok.violations
        assert violations == (), [(v.rule, v.node, v.detail) for v in violations]
