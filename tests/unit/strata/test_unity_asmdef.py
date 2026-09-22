"""Unit tests for `frob.strata._unity_asmdef` (T-4512).

Reads the static fixture at `tests/fixtures/unity_sample_asmdef/`: four
asmdefs (Runtime, RuntimeUtils, Editor, Tests -- one Editor-only, one
referencing by GUID, one referencing a name that does not exist) plus a
loose `.cs` file no asmdef covers, so each acceptance criterion (distinct
nodes per asmdef, resolved reference edges, default-assembly catch-all)
has real fixture data behind it rather than a synthetic in-test dict.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata._unity_asmdef import (
    UNITY_DEFAULT_ASSEMBLY_NODE,
    UnityAsmdefError,
    build_component_nodes,
    discover_asmdefs,
    render_unity_fragment,
    write_unity_fragment,
)

FIXTURE_ROOT = Path(__file__).parent.parent.parent / "fixtures" / "unity_sample_asmdef"


def _discovered():
    result = discover_asmdefs(FIXTURE_ROOT)
    assert result.is_ok, result.err
    return result.danger_ok


class TestDiscoverAsmdefs:
    """`discover_asmdefs` walks Assets/+Packages/ for every `*.asmdef`."""

    # frob:tests src/frob/strata/_unity_asmdef.py::discover_asmdefs  # noqa: E501
    # frob:tests src/frob/strata/_unity_asmdef.py::AsmdefInfo  # noqa: E501
    def test_finds_all_four_asmdefs(self):
        """The fixture's four asmdefs are all discovered, by name."""
        infos = _discovered()
        names = {info.name for info in infos}
        assert names == {
            "Game.Runtime",
            "Game.RuntimeUtils",
            "Game.Editor",
            "Game.Tests",
        }

    def test_editor_asmdef_flagged_editor_only(self):
        """The asmdef whose includePlatforms == ["Editor"] is flagged."""
        infos = _discovered()
        by_name = {info.name: info for info in infos}
        assert by_name["Game.Editor"].is_editor_only is True
        assert by_name["Game.Runtime"].is_editor_only is False

    def test_meta_guid_read(self):
        """Each asmdef's `.asmdef.meta` sidecar guid is read back."""
        infos = _discovered()
        by_name = {info.name: info for info in infos}
        assert by_name["Game.Runtime"].guid == "11111111111111111111111111111111"

    # frob:tests src/frob/strata/_unity_asmdef.py::UnityAsmdefError  # noqa: E501
    def test_not_a_unity_project_errs(self, tmp_path):
        """A directory with none of Unity's own markers is Err, not []."""
        result = discover_asmdefs(tmp_path)
        assert result.is_err
        assert result.danger_err == UnityAsmdefError.NotAUnityProject


class TestBuildComponentNodes:
    """`build_component_nodes` maps discovered asmdefs to strata nodes."""
# frob:tests src/frob/strata/_unity_asmdef.py::build_component_nodes  # noqa: E501

    def test_two_asmdefs_two_distinct_nodes(self):
        """Acceptance 1: each discovered asmdef becomes its own node id."""
        model = build_component_nodes(_discovered(), FIXTURE_ROOT)
        node_ids = {node.node_id for node in model.nodes}
        assert "unity_game_runtime" in node_ids
        assert "unity_game_editor" in node_ids
        assert "unity_game_runtime" != "unity_game_editor"

    def test_reference_by_name_resolves_to_edge(self):
        """Acceptance 2: a plain-name `references` entry becomes a `depends` edge."""
        model = build_component_nodes(_discovered(), FIXTURE_ROOT)
        by_id = {node.node_id: node for node in model.nodes}
        assert "unity_game_runtimeutils" in by_id["unity_game_runtime"].depends

    # frob:tests src/frob/strata/_unity_asmdef.py::build_component_nodes  # noqa: E501
    def test_reference_by_guid_resolves_to_edge(self):
        """A `GUID:<hex>` reference resolves via the referenced asmdef's own `.meta`."""
        model = build_component_nodes(_discovered(), FIXTURE_ROOT)
        by_id = {node.node_id: node for node in model.nodes}
        assert "unity_game_runtime" in by_id["unity_game_editor"].depends

    # frob:tests src/frob/strata/_unity_asmdef.py::UnresolvedReference  # noqa: E501
    def test_unresolvable_reference_recorded_not_dropped(self):
        """A `references` entry naming no discovered asmdef is recorded, not silently dropped."""
        model = build_component_nodes(_discovered(), FIXTURE_ROOT)
        unresolved_raw = {u.raw_reference for u in model.unresolved_references}
        assert "Game.MissingAssembly" in unresolved_raw

    # frob:tests src/frob/strata/_unity_asmdef.py::UnityAssemblyModel  # noqa: E501
    def test_default_assembly_node_always_present(self):
        """Acceptance 3: a `.cs` file outside every asmdef lands in the default node."""
        model = build_component_nodes(_discovered(), FIXTURE_ROOT)
        node_ids = {node.node_id for node in model.nodes}
        assert UNITY_DEFAULT_ASSEMBLY_NODE in node_ids

    # frob:tests src/frob/strata/_unity_asmdef.py::UnityComponentNode  # noqa: E501
    def test_editor_flag_carried_onto_node(self):
        """An Editor-only asmdef's node carries `is_editor_only=True`."""
        model = build_component_nodes(_discovered(), FIXTURE_ROOT)
        by_id = {node.node_id: node for node in model.nodes}
        assert by_id["unity_game_editor"].is_editor_only is True


class TestRenderUnityFragment:
    """`render_unity_fragment` is a pure, deterministic text renderer."""

    # frob:tests src/frob/strata/_unity_asmdef.py::render_unity_fragment  # noqa: E501
    def test_render_is_deterministic(self):
        """Two renders of the same model produce byte-identical text."""
        model = build_component_nodes(_discovered(), FIXTURE_ROOT)
        assert render_unity_fragment(model) == render_unity_fragment(model)

    def test_render_contains_every_node_and_a_dependency_flow(self):
        """The rendered text declares every node id and at least one flow edge."""
        model = build_component_nodes(_discovered(), FIXTURE_ROOT)
        text = render_unity_fragment(model)
        for node in model.nodes:
            assert f"node {node.node_id} : trusted {{" in text
        assert "flow f_unity_game_runtime_unity_game_runtimeutils" in text

    # frob:tests src/frob/strata/_unity_asmdef.py::render_unity_fragment  # noqa: E501
    def test_editor_node_gets_editor_attr(self):
        """The Editor-only node's block carries `attr editor;`."""
        model = build_component_nodes(_discovered(), FIXTURE_ROOT)
        text = render_unity_fragment(model)
        editor_block_start = text.index("node unity_game_editor : trusted {")
        editor_block_end = text.index("}", editor_block_start)
        assert "attr editor;" in text[editor_block_start:editor_block_end]


class TestWriteUnityFragment:
    """`write_unity_fragment` is the module's one I/O boundary."""

    # frob:tests src/frob/strata/_unity_asmdef.py::write_unity_fragment  # noqa: E501
    def test_writes_fragment_file(self, tmp_path):
        """A real write produces a readable file whose text round-trips through render."""
        output_path = tmp_path / "unity-assemblies.strata"
        result = write_unity_fragment(FIXTURE_ROOT, output_path)
        assert result.is_ok, result.err
        written_text = output_path.read_text(encoding="utf-8")
        assert written_text == render_unity_fragment(result.danger_ok)

    # frob:tests src/frob/strata/_unity_asmdef.py::write_unity_fragment  # noqa: E501
    def test_write_is_idempotent(self, tmp_path):
        """Re-running the writer against an unchanged project is byte-identical."""
        output_path = tmp_path / "unity-assemblies.strata"
        write_unity_fragment(FIXTURE_ROOT, output_path)
        first_text = output_path.read_text(encoding="utf-8")
        write_unity_fragment(FIXTURE_ROOT, output_path)
        second_text = output_path.read_text(encoding="utf-8")
        assert first_text == second_text

    def test_write_fails_closed_for_non_unity_root(self, tmp_path):
        """A non-Unity root Errs rather than writing an empty/garbage fragment."""
        output_path = tmp_path / "unity-assemblies.strata"
        result = write_unity_fragment(tmp_path, output_path)
        assert result.is_err
        assert result.danger_err == UnityAsmdefError.NotAUnityProject
        assert not output_path.exists()
