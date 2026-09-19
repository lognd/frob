"""T-4514: `_UNITY_OPERATIONS` (`frob.vet._capability_registry._unity_api`)
-- direct unit coverage over the registry TABLE itself, one test per
mapped API family from the ticket brief.

WIRING NOTE (T-4514 Done report, repeated here so a reader of this test
file sees it too): `_UNITY_OPERATIONS` is NOT yet concatenated into
`DANGEROUS_OPERATIONS` (`_capability_registry/_matrix.py`) -- that file
was leased by the concurrently in-progress T-4511 at the time this
ticket ran, and the hard rule ("a lease refusal naming another ticket
means stop and report, never --steal") applies. These tests therefore
exercise the table's OWN content directly (`_UNITY_OPERATIONS`) rather
than through `frob.vet._capability.scan_file_capabilities` end to end --
the one-line matrix wiring is the coordinator's follow-up once T-4511
releases the `_matrix.py` lease (T-4514's Done report names the exact
two lines to add)."""

from __future__ import annotations

from frob.vet._capability_registry._unity_api import _UNITY_OPERATIONS


def _kinds_for(needle_substring: str) -> set[str]:
    return {
        op.capability_kind
        for op in _UNITY_OPERATIONS
        if any(needle_substring in n for n in op.needles)
    }


class TestUnityApiRegistry:
    """T-4514: UnityEngine/UnityEditor API surface -> capability kind."""

    def test_unity_web_request_maps_to_fetch_url(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_unity_api.py::_UNITY_OPERATIONS kind="unit"
        assert "fetch_url" in _kinds_for("UnityWebRequest.Get(")

    def test_unity_web_request_maps_to_net(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_unity_api.py::_UNITY_OPERATIONS kind="unit"
        # T-4514's own acceptance criterion: "GIVEN a call to
        # UnityEngine.Networking.UnityWebRequest.Get ... THEN it maps to
        # the net capability." T-4554: the bare "net" capability_kind
        # this asserted was a RETIRED scanner kind (T-0771's net-connect/
        # net-listen split) that had slipped back in unnoticed, tripping
        # TestExtendedKindsDriftLock on dev; recategorized to the precise
        # "net-connect" kind, which a coarse `may "net"` declaration
        # still covers (`_kinds.py`'s WIRED_MODE_FAMILIES) -- same
        # capability, name unchanged (existing evidence citations point
        # here), assertion updated to match.
        assert "net-connect" in _kinds_for("UnityWebRequest.Get(")

    def test_legacy_www_maps_to_net(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_unity_api.py::_UNITY_OPERATIONS kind="unit"
        # T-4554: net -> net-connect, see test_unity_web_request_maps_to_net above.
        assert "net-connect" in _kinds_for("new WWW(")

    def test_network_manager_maps_to_net(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_unity_api.py::_UNITY_OPERATIONS kind="unit"
        # T-4554: net -> net-connect, see test_unity_web_request_maps_to_net above.
        assert "net-connect" in _kinds_for("NetworkManager.Singleton")

    def test_open_url_maps_to_both_net_and_exec(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_unity_api.py::_UNITY_OPERATIONS kind="unit"
        # T-4554: net -> net-connect, see test_unity_web_request_maps_to_net above.
        kinds = _kinds_for("Application.OpenURL(")
        assert "net-connect" in kinds
        assert "exec" in kinds

    def test_player_prefs_set_maps_to_fs_write(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_unity_api.py::_UNITY_OPERATIONS kind="unit"
        assert "fs-write" in _kinds_for("PlayerPrefs.SetString(")

    def test_player_prefs_get_maps_to_fs_read(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_unity_api.py::_UNITY_OPERATIONS kind="unit"
        assert "fs-read" in _kinds_for("PlayerPrefs.GetString(")

    def test_resources_load_maps_to_fs_read(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_unity_api.py::_UNITY_OPERATIONS kind="unit"
        assert "fs-read" in _kinds_for("Resources.Load(")

    def test_asset_database_load_maps_to_fs_read(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_unity_api.py::_UNITY_OPERATIONS kind="unit"
        assert "fs-read" in _kinds_for("AssetDatabase.LoadAssetAtPath(")

    def test_addressables_load_maps_to_fs_read(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_unity_api.py::_UNITY_OPERATIONS kind="unit"
        assert "fs-read" in _kinds_for("Addressables.LoadAssetAsync(")

    def test_asset_database_create_delete_import_maps_to_fs_write(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_unity_api.py::_UNITY_OPERATIONS kind="unit"
        assert "fs-write" in _kinds_for("AssetDatabase.CreateAsset(")
        assert "fs-write" in _kinds_for("AssetDatabase.DeleteAsset(")
        assert "fs-write" in _kinds_for("AssetDatabase.ImportAsset(")

    def test_unity_editor_namespace_usage_flagged_as_eval_with_clear_name(
        self,
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_unity_api.py::_UNITY_OPERATIONS kind="unit"
        # Registry-limitation fallback (module docstring): no file-path-
        # conditional kind exists, so every UnityEditor.* reference is
        # flagged unconditionally under "eval", with a needle name that
        # says exactly why rather than reading as a bare, unexplained hit.
        matches = [op for op in _UNITY_OPERATIONS if "UnityEditor." in op.needles]
        assert len(matches) == 1
        op = matches[0]
        assert op.capability_kind == "eval"
        assert "editor-api-in-runtime" in op.function_or_pattern

    def test_every_entry_is_csharp(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_unity_api.py::_UNITY_OPERATIONS kind="unit"
        assert all(op.language == "csharp" for op in _UNITY_OPERATIONS)

    def test_every_capability_kind_is_registered(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_unity_api.py::_UNITY_OPERATIONS kind="unit"
        from frob.vet._capability_registry._kinds import CAPABILITY_KINDS

        assert all(op.capability_kind in CAPABILITY_KINDS for op in _UNITY_OPERATIONS)
