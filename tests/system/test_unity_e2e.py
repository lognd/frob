"""T-4509 (Unity capstone, epic T-4513): end-to-end proof that the whole
epic composes -- scaffolds `tests/fixtures/unity_sample` onto a private
copy, and proves each GIVEN/WHEN/THEN in the ticket body:

1. `render_unity_project` (T-4503) succeeds and the asmdef-derived
   strata nodes match the fixture's two asmdef files (Game.Runtime,
   Game.Tests) plus Unity's always-present default-assembly node.
2. The fixture's MonoBehaviour lifecycle method (`Update`) and coroutine
   (`RespawnRoutine`, reached via `StartCoroutine`) are NOT flagged dead
   code by `frob check --only dead_symbols` (T-4514's roots).
3. The fixture's Editor-only API call and its BCL/Unity API calls (net,
   fs-write, exec) resolve to exactly the expected capability findings,
   with zero unexpected findings on the fixture's clean paths.
4. Both the NUnit `[Test]` and Unity Test Framework `[UnityTest]` methods
   are collected as bindable node ids (T-4516/T-4517).

CLI CAVEAT (T-4578 not yet on dev): `frob scaffold unity-project` -- the
dedicated CLI leaf T-4578 wires onto `render_unity_project` -- had not
landed on `dev` as of this ticket being worked (confirmed: `frob scaffold
--help` in this worktree lists only list/apply/new/pool). This test calls
`render_unity_project` directly instead, per the ticket's own acceptance
wording's "(or init detection)" allowance -- the same underlying entry
point the CLI leaf itself calls, so this proves the scaffold model's
success/asmdef-node contract identically. Swap the direct call for a real
`python -m frob scaffold unity-project <dir>` subprocess once T-4578
lands, if a future ticket wants the CLI-surface form specifically re-
proven end to end.

`frob vet` CAVEAT: `frob.vet._scan.scan_tree` (the CLI's `frob vet`
verb) scans a project's LOCKFILE DEPENDENCIES (uv.lock/package-lock.json/
Cargo.lock/...), not first-party source -- by design (docs/modules/
vet.md), not a Unity-specific gap. A Unity project ships none of those
lockfiles, so `test_frob_vet_cli_runs_cleanly_against_the_fixture` below
proves the real CLI subprocess runs against a genuine Unity project tree
without crashing -- measured: it exits 1 with a clean, well-formed
`LockfileUnsupported` refusal (never a traceback), not 0, since it finds
no supported lockfile at all -- but the actual capability-finding
assertions
(`test_expected_capability_findings_fire_with_no_false_positives`) call
`frob.vet._capability_scan.scan_file_capabilities` directly, the exact
same primitive `frob vet`'s own package scanner
(`_capability_and_fingerprint_signals`) calls internally to produce a
package verdict's capability set -- so this exercises the identical
detection logic the ticket's acceptance criteria describe, invoked the
way a first-party source-tree audit would (frob vet has no first-party-
tree scan mode as of this writing).

STRATA PARSE CAVEAT: `render_unity_project`'s per-node `design/*.strata`
fragments (T-4512's `render_unity_fragment`) carry no leading `module`
declaration and the unity-project scaffold writes no companion root
`design/frob.strata` either, so `frob check`'s strata loader logs a
`ParseFailed` warning for each fragment when nothing else in the tree
supplies that module header (docs/strata/surface.md's own T-4512 section:
these fragments are meant to be "loaded and merged" alongside SOME root
module file). This does not block `--only dead_symbols` (confirmed clean
exit, 0 diagnostics) or the capability/test-collection assertions below,
none of which touch strata parsing -- filed as T-draft-330aa06d rather
than fixed here (out of this ticket's declared scope:
`src/frob/scaffold/_unity_project.py` is not in T-4509's scope list)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from frob.scaffold._unity_project import render_unity_project
from frob.testing._collect_csharp import collect_csharp_tests
from frob.vet._capability_scan import scan_file_capabilities

FROB = [sys.executable, "-m", "frob"]

_FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures" / "unity_sample"


def _copy_fixture(dest: Path) -> None:
    """Copy the T-4509 Unity capstone fixture to `dest` -- scaffolding
    writes into it, so the tracked fixture tree must never be touched."""
    shutil.copytree(_FIXTURE_ROOT, dest)


class TestUnityScaffoldAndAsmdefNodes:
    """Acceptance criterion 1: scaffolding succeeds and the asmdef-
    derived strata nodes match the fixture's two asmdef files."""

    # frob:ticket T-4509
    # frob:tests tests/system/test_unity_e2e.py::TestUnityScaffoldAndAsmdefNodes.test_scaffold_succeeds_and_nodes_match_the_two_asmdefs  # noqa: E501
    def test_scaffold_succeeds_and_nodes_match_the_two_asmdefs(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "unity_sample"
        _copy_fixture(project)

        result = render_unity_project(project)
        assert result.is_ok, result.err

        assert (project / "frob.toml").exists()
        design_dir = project / "design"
        fragment_names = sorted(p.stem for p in design_dir.glob("*.strata"))
        # The two declared asmdefs (Game.Runtime -> unity_game_runtime,
        # Game.Tests -> unity_game_tests) plus Unity's always-present
        # default-assembly node (build_component_nodes's own contract,
        # T-4512 criterion 3) -- exactly three, matching "two asmdef files"
        # plus the implicit catch-all the Editor/ script (no asmdef of its
        # own, by this ticket's own two-asmdef acceptance wording) falls
        # into.
        assert fragment_names == [
            "unity_default_assembly",
            "unity_game_runtime",
            "unity_game_tests",
        ]


class TestMonoBehaviourAndCoroutineAreNotDeadCode:
    """Acceptance criterion 2: the MonoBehaviour lifecycle method and
    coroutine are NOT flagged as dead code (proves T-4514's roots)."""

    # frob:ticket T-4509
    # frob:tests tests/system/test_unity_e2e.py::TestMonoBehaviourAndCoroutineAreNotDeadCode.test_dead_symbols_gate_reports_zero_findings  # noqa: E501
    def test_dead_symbols_gate_reports_zero_findings(self, tmp_path: Path) -> None:
        project = tmp_path / "unity_sample"
        _copy_fixture(project)
        assert render_unity_project(project).is_ok

        # `--type python` sidesteps `frob check`'s own project-type
        # dispatch gate (CHECK001 "unknown project type") -- that gate
        # exists to pick a LANGUAGE TOOLCHAIN (ruff/ty vs cargo vs tsc),
        # unrelated to `--only dead_symbols`, a graph-level gate that
        # already resolves C# via tree-sitter (frob.lang) regardless of
        # which toolchain string is passed; a Unity project has no
        # pyproject.toml/Cargo.toml/package.json of its own to detect a
        # "real" type from.
        result = subprocess.run(
            FROB
            + [
                "check",
                "--type",
                "python",
                "--only",
                "dead_symbols",
                "--json",
                str(project),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(result.stdout)
        summary_entry = next(
            r for r in report["results"] if r["tool"] == "gate-summary"
        )
        assert "dead_symbols=" in summary_entry["summary"], summary_entry["summary"]
        assert summary_entry["summary"].startswith("0 errors, 0 warnings"), (
            summary_entry["summary"]
        )
        # No DEAD-family diagnostic anywhere in the report -- in
        # particular, Update/Start/RespawnRoutine never appear.
        for entry in report["results"]:
            for diag in entry["diagnostics"]:
                message = diag.get("message") or ""
                assert "DEAD001" not in message, message
                assert "Update" not in message, message
                assert "RespawnRoutine" not in message, message


class TestExpectedCapabilityFindings:
    """Acceptance criterion 3: the Editor-only API call and the BCL/Unity
    API calls (net, fs-write, exec) resolve to exactly the expected
    capability findings, with zero unexpected findings on clean paths."""

    # frob:ticket T-4509
    # frob:tests tests/system/test_unity_e2e.py::TestExpectedCapabilityFindings.test_runtime_script_finds_net_fs_write_and_exec  # noqa: E501
    def test_runtime_script_finds_net_fs_write_and_exec(self, tmp_path: Path) -> None:
        project = tmp_path / "unity_sample"
        _copy_fixture(project)

        found = scan_file_capabilities(project / "Assets" / "Scripts" / "Player.cs")
        # HttpClient.GetAsync -> fetch_url (T-4536 csharp resolver slice,
        # "net" per the ticket's own shorthand), File.WriteAllText ->
        # fs-write, Process.Start -> exec (T-4511's map): exactly these
        # three, nothing else -- the MonoBehaviour lifecycle/coroutine
        # bodies above them make no dangerous calls of their own.
        assert found == frozenset({"fetch_url", "fs-write", "exec"})

    # frob:ticket T-4509
    # frob:tests tests/system/test_unity_e2e.py::TestExpectedCapabilityFindings.test_editor_script_finds_eval_and_fs_write_tagged_editor_only  # noqa: E501
    def test_editor_script_finds_eval_and_fs_write_tagged_editor_only(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "unity_sample"
        _copy_fixture(project)

        found = scan_file_capabilities(project / "Assets" / "Editor" / "BuildTool.cs")
        # AssetDatabase.CreateAsset -> fs-write (Editor asset-write map),
        # plus the disclosed UnityEditor.* editor-api-in-runtime fallback
        # -> eval (src/frob/vet/_capability_registry/_unity_api.py's own
        # module docstring: registered under "eval" unconditionally,
        # tagged unambiguously by its function_or_pattern text naming
        # "editor-api-in-runtime" -- the closest this registry comes to a
        # true editor-vs-runtime tag without a file-path-aware resolver,
        # a disclosed, out-of-scope limitation for BOTH T-4514 and this
        # ticket). Exactly these two, nothing else.
        assert found == frozenset({"fs-write", "eval"})

    # frob:ticket T-4509
    # frob:tests tests/system/test_unity_e2e.py::TestExpectedCapabilityFindings.test_frob_vet_cli_runs_cleanly_against_the_fixture  # noqa: E501
    def test_frob_vet_cli_runs_cleanly_against_the_fixture(
        self, tmp_path: Path
    ) -> None:
        """`frob vet` against a real Unity project tree: zero lockfiles
        (module docstring's `frob vet` CAVEAT) -- a clean, well-formed
        `LockfileUnsupported` refusal, never a crash/traceback, proving
        the CLI runs against a genuine Unity project tree end to end (the
        CLI-surface half of "runs frob check and frob vet against it";
        measured: `frob vet` exits 1 with this message, not 0, on a tree
        with no lockfile at all -- distinct from "0 lockfiles scanned,
        clean")."""
        project = tmp_path / "unity_sample"
        _copy_fixture(project)
        assert render_unity_project(project).is_ok

        result = subprocess.run(
            FROB + ["vet", str(project), "--json"],
            capture_output=True,
            text=True,
        )
        out = result.stdout + result.stderr
        assert result.returncode == 1, out
        assert "Traceback" not in out
        assert "LockfileUnsupported" in out


class TestNUnitAndUnityTestCollection:
    """Acceptance criterion 4: both the NUnit and [UnityTest] tests are
    collected and bindable (proves stories 1-5 compose end to end)."""

    # frob:ticket T-4509
    # frob:tests tests/system/test_unity_e2e.py::TestNUnitAndUnityTestCollection.test_both_test_attribute_families_collected  # noqa: E501
    def test_both_test_attribute_families_collected(self, tmp_path: Path) -> None:
        project = tmp_path / "unity_sample"
        _copy_fixture(project)

        result = collect_csharp_tests(project)
        assert result.is_ok, result.err
        node_ids = result.danger_ok.node_ids
        assert (
            "Assets/Tests/PlayModeTests.cs::Game.Tests.PlayModeTests::"
            "AddScores_ReturnsSum" in node_ids
        )
        assert (
            "Assets/Tests/PlayModeTests.cs::Game.Tests.PlayModeTests::"
            "Player_Respawns_AfterOneFrame" in node_ids
        )
        assert len(node_ids) == 2
