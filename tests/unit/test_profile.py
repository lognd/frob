"""Unit tests for `frob.tickets._profile` (T-1575)."""

from __future__ import annotations

from pathlib import Path

from frob.tickets._profile import (
    ProfileName,
    configured_profile,
    downgrade_profile_ratchet,
    effective_profile,
    ratchet_override_enabled,
)


class TestConfiguredProfile:
    """`configured_profile` reads the raw `[profile]` value, no ratchet."""

    def test_absent_frob_toml_is_standard(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_profile.py::TestConfiguredProfile.test_absent_frob_toml_is_standard  # noqa: E501
        result = configured_profile(tmp_path)
        assert result.is_ok
        assert result.danger_ok is ProfileName.STANDARD

    def test_explicit_rapid_parses(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_profile.py::TestConfiguredProfile.test_explicit_rapid_parses  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            '[profile]\nprofile = "rapid"\n', encoding="utf-8"
        )
        result = configured_profile(tmp_path)
        assert result.is_ok
        assert result.danger_ok is ProfileName.RAPID

    def test_unknown_value_errors(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_profile.py::TestConfiguredProfile.test_unknown_value_errors  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            '[profile]\nprofile = "bogus"\n', encoding="utf-8"
        )
        result = configured_profile(tmp_path)
        assert result.is_err


class TestEffectiveProfile:
    """`effective_profile` applies the one-way auto-ratchet on top of
    `configured_profile`."""

    def test_standard_is_unaffected_by_ratchet(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_profile.py::TestEffectiveProfile.test_standard_is_unaffected_by_ratchet  # noqa: E501
        result = effective_profile(tmp_path)
        assert result.is_ok
        assert result.danger_ok is ProfileName.STANDARD
        assert not (tmp_path / ".frob" / "profile-ratchet.json").exists()

    def test_rapid_below_threshold_stays_rapid(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_profile.py::TestEffectiveProfile.test_rapid_below_threshold_stays_rapid  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            '[profile]\nprofile = "rapid"\n', encoding="utf-8"
        )
        result = effective_profile(tmp_path)
        assert result.is_ok
        assert result.danger_ok is ProfileName.RAPID
        assert not (tmp_path / ".frob" / "profile-ratchet.json").exists()

    def test_rapid_above_threshold_ratchets_to_standard(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_profile.py::TestEffectiveProfile.test_rapid_above_threshold_ratchets_to_standard  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            '[profile]\nprofile = "rapid"\n', encoding="utf-8"
        )
        import frob.tickets._profile as profile_mod

        monkeypatch.setattr(profile_mod, "_repo_file_count", lambda root: 99999)

        result = effective_profile(tmp_path)
        assert result.is_ok
        assert result.danger_ok is ProfileName.STANDARD
        assert (tmp_path / ".frob" / "profile-ratchet.json").exists()

    def test_persisted_ratchet_wins_even_if_thresholds_no_longer_trip(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_profile.py::TestEffectiveProfile.test_persisted_ratchet_wins_even_if_thresholds_no_longer_trip  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            '[profile]\nprofile = "rapid"\n', encoding="utf-8"
        )
        import frob.tickets._profile as profile_mod

        monkeypatch.setattr(profile_mod, "_repo_file_count", lambda root: 99999)
        first = effective_profile(tmp_path)
        assert first.danger_ok is ProfileName.STANDARD

        monkeypatch.setattr(profile_mod, "_repo_file_count", lambda root: 0)
        second = effective_profile(tmp_path)
        assert second.is_ok
        assert second.danger_ok is ProfileName.STANDARD


class TestDowngrade:
    """`downgrade_profile_ratchet` is the only way to clear a ratchet."""

    def test_downgrade_clears_persisted_ratchet(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_profile.py::TestDowngrade.test_downgrade_clears_persisted_ratchet  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            '[profile]\nprofile = "rapid"\n', encoding="utf-8"
        )
        import frob.tickets._profile as profile_mod

        monkeypatch.setattr(profile_mod, "_repo_file_count", lambda root: 99999)
        effective_profile(tmp_path)
        assert (tmp_path / ".frob" / "profile-ratchet.json").exists()

        result = downgrade_profile_ratchet(tmp_path, reason="test cleanup")
        assert result.is_ok
        assert result.danger_ok is True
        assert not (tmp_path / ".frob" / "profile-ratchet.json").exists()

    def test_downgrade_is_noop_when_nothing_ratcheted(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_profile.py::TestDowngrade.test_downgrade_is_noop_when_nothing_ratcheted  # noqa: E501
        result = downgrade_profile_ratchet(tmp_path, reason="no-op check")
        assert result.is_ok
        assert result.danger_ok is False


# frob:ticket T-1684
class TestRatchetOverride:
    """`ratchet_override_enabled` (T-1681): the explicit, tracked owner
    decision to keep `rapid` in a repo the size ratchet would upgrade."""

    def test_absent_frob_toml_is_not_overridden(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_profile.py::TestRatchetOverride.test_absent_frob_toml_is_not_overridden  # noqa: E501
        assert ratchet_override_enabled(tmp_path) is False

    def test_absent_key_is_not_overridden(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_profile.py::TestRatchetOverride.test_absent_key_is_not_overridden  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            '[profile]\nprofile = "rapid"\n', encoding="utf-8"
        )
        assert ratchet_override_enabled(tmp_path) is False

    def test_explicit_true_overrides(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_profile.py::TestRatchetOverride.test_explicit_true_overrides  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            '[profile]\nprofile = "rapid"\noverride_ratchet = true\n', encoding="utf-8"
        )
        assert ratchet_override_enabled(tmp_path) is True

    def test_malformed_toml_fails_strict_not_relaxed(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_profile.py::TestRatchetOverride.test_malformed_toml_fails_strict_not_relaxed  # noqa: E501
        # A broken config can only ever make the ceremony STRICTER.
        (tmp_path / "frob.toml").write_text("[profile\n", encoding="utf-8")
        assert ratchet_override_enabled(tmp_path) is False
