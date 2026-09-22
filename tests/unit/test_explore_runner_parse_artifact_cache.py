"""T-5201: `frob.app.explore_runner._stamp_read_only_parse_artifact_cache_env`
opens the persistent parse-artifact cache read-only for single-process
`frob explore` commands, mirroring what gate workers already get.
"""

from __future__ import annotations

from pathlib import Path

from frob.app.explore_runner import _stamp_read_only_parse_artifact_cache_env
from frob.lang import PARSE_ARTIFACT_CACHE_ENV


class TestStampReadOnlyParseArtifactCacheEnv:
    """`_stamp_read_only_parse_artifact_cache_env` stamps
    `PARSE_ARTIFACT_CACHE_ENV` only when `.frob/parse-artifacts.db`
    already exists, and never creates it itself -- see T-5201 for the
    design rationale."""

    # frob:tests src/frob/app/explore_runner.py::run  # noqa: E501
    def test_stamps_env_when_cache_db_exists(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests \
        # src/frob/app/explore_runner.py::_stamp_read_only_parse_artifact_cache_env \
        # kind="unit"
        cache_dir = tmp_path / ".frob"
        cache_dir.mkdir()
        cache_path = cache_dir / "parse-artifacts.db"
        cache_path.write_bytes(b"")  # existence is all this reads

        monkeypatch.delenv(PARSE_ARTIFACT_CACHE_ENV, raising=False)
        monkeypatch.setenv("FROB_ROOT", str(tmp_path))

        _stamp_read_only_parse_artifact_cache_env()

        import os as _os

        assert Path(_os.environ[PARSE_ARTIFACT_CACHE_ENV]) == cache_path.resolve()

    def test_does_not_stamp_when_no_cache_db_exists(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # src/frob/app/explore_runner.py::_stamp_read_only_parse_artifact_cache_env \
        # kind="unit"
        # T-5201: a repo that has never run `frob check` has no
        # .frob/parse-artifacts.db -- explore must never create one
        # itself, only opportunistically reuse an existing one.
        monkeypatch.delenv(PARSE_ARTIFACT_CACHE_ENV, raising=False)
        monkeypatch.setenv("FROB_ROOT", str(tmp_path))

        _stamp_read_only_parse_artifact_cache_env()

        import os as _os

        assert PARSE_ARTIFACT_CACHE_ENV not in _os.environ
        assert not (tmp_path / ".frob" / "parse-artifacts.db").exists()
