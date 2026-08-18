"""T-2467: unit tests for the persisted waive-audit watermark."""

from __future__ import annotations

from pathlib import Path

from frob.gates._waive_audit_watermark import (
    WaiveAuditWatermark,
    WaiveAuditWatermarkError,
    load_watermark,
    save_watermark,
    utc_now,
    watermark_path,
)


class TestLoadWatermark:
    def test_missing_file_is_not_found(self, tmp_path: Path) -> None:
        result = load_watermark(tmp_path)
        assert result.is_err
        assert result.err is WaiveAuditWatermarkError.NotFound

    def test_malformed_json_is_malformed(self, tmp_path: Path) -> None:
        path = watermark_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json")
        result = load_watermark(tmp_path)
        assert result.is_err
        assert result.err is WaiveAuditWatermarkError.Malformed

    def test_valid_file_round_trips(self, tmp_path: Path) -> None:
        watermark = WaiveAuditWatermark(
            commit_sha="deadbeef",
            audited_at=utc_now(),
            waivers_audited=12,
        )
        save_watermark(tmp_path, watermark)
        result = load_watermark(tmp_path)
        assert result.is_ok
        loaded = result.danger_ok
        assert loaded.commit_sha == "deadbeef"
        assert loaded.waivers_audited == 12
        assert loaded.catchup_remaining == 0


class TestSaveWatermark:
    def test_round_trips_through_load(self, tmp_path: Path) -> None:
        watermark = WaiveAuditWatermark(
            commit_sha="cafef00d",
            audited_at=utc_now(),
            waivers_audited=3,
            catchup_remaining=7,
        )
        saved = save_watermark(tmp_path, watermark)
        assert saved.is_ok
        reloaded = load_watermark(tmp_path).danger_ok
        assert reloaded.commit_sha == "cafef00d"
        assert reloaded.catchup_remaining == 7

    def test_creates_frob_dir_if_missing(self, tmp_path: Path) -> None:
        assert not (tmp_path / ".frob").exists()
        watermark = WaiveAuditWatermark(
            commit_sha="abc", audited_at=utc_now(), waivers_audited=0
        )
        result = save_watermark(tmp_path, watermark)
        assert result.is_ok
        assert (tmp_path / ".frob").is_dir()
        assert watermark_path(tmp_path).exists()
