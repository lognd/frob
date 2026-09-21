"""CONFIGPATH001 tests (F-307 H3-5, frob:ticket T-4114): a pydantic config
path field whose default is a relative path should be flagged, decided
purely from the parsed annotation/default AST, never from source text."""

from pathlib import Path

from frob.findings import Severity
from frob.gates._config_path_defaults import config_path_default_gate
from tests.conftest import _git_init, _write


class TestConfigPathDefaultGate:
    """Positive-control fixture pair for CONFIGPATH001: a synthetic
    pydantic model in the test module itself (T-4114's own directive --
    prefer a synthetic fixture over grepping frob's real config classes,
    which may not have a naturally occurring instance or may change out
    from under this test)."""

    # frob:tests src/frob/gates/_config_path_defaults.py::config_path_default_gate
    def test_relative_path_default_fires(self, tmp_path: Path) -> None:
        """FAIL before this rule exists (`frob.gates._config_path_defaults`
        did not exist -- the import itself would raise `ModuleNotFoundError`);
        PASS after: a `*_path` field defaulted to a relative literal is
        reported. Must-fire fixture from T-4114's own ticket body."""
        _write(
            tmp_path,
            "src/pkg/config.py",
            "from pydantic import BaseModel, Field\n\n\n"
            "class AppConfig(BaseModel):\n"
            '    state_path: str = Field(default="relative/dir/state.json")\n',
        )
        _git_init(tmp_path)
        violations = config_path_default_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "CONFIGPATH001"
        assert violations[0].severity == Severity.WARN
        assert violations[0].file == "src/pkg/config.py"
        assert violations[0].line == 5
        assert "state_path" in violations[0].message
        assert "relative/dir/state.json" in violations[0].message

    # frob:tests src/frob/gates/_config_path_defaults.py::config_path_default_gate
    def test_absolute_path_default_is_silent(self, tmp_path: Path) -> None:
        """Must-stay-quiet fixture from T-4114's own ticket body: an
        absolute default on a `*_path` field is not a footgun."""
        _write(
            tmp_path,
            "src/pkg/config.py",
            "from pydantic import BaseModel, Field\n\n\n"
            "class AppConfig(BaseModel):\n"
            '    state_path: str = Field(default="/abs/dir/state.json")\n',
        )
        _git_init(tmp_path)
        assert config_path_default_gate(tmp_path) == ()

    # frob:tests src/frob/gates/_config_path_defaults.py::config_path_default_gate
    def test_none_default_is_silent(self, tmp_path: Path) -> None:
        """Must-stay-quiet fixture from T-4114's own ticket body: `default=
        None` on a `*_path` field is the documented escape hatch, not a
        relative-path footgun."""
        _write(
            tmp_path,
            "src/pkg/config.py",
            "from pydantic import BaseModel, Field\n\n\n"
            "class AppConfig(BaseModel):\n"
            "    state_path: str | None = Field(default=None)\n",
        )
        _git_init(tmp_path)
        assert config_path_default_gate(tmp_path) == ()

    # frob:tests src/frob/gates/_config_path_defaults.py::config_path_default_gate
    def test_required_field_with_no_default_is_silent(self, tmp_path: Path) -> None:
        """Must-stay-quiet fixture from T-4114's own ticket body: a
        `*_path` field with no default at all (required) has nothing to
        evaluate -- `Field(...)`'s Ellipsis sentinel is not a `default=`
        keyword at all."""
        _write(
            tmp_path,
            "src/pkg/config.py",
            "from pydantic import BaseModel, Field\n\n\n"
            "class AppConfig(BaseModel):\n"
            "    state_path: str = Field(...)\n",
        )
        _git_init(tmp_path)
        assert config_path_default_gate(tmp_path) == ()

    def test_path_annotated_field_without_path_suffix_fires(
        self, tmp_path: Path
    ) -> None:
        """The annotation-based signal: a field annotated `Path` with a
        relative default fires even when its name does not end in
        `_path` -- T-4114's own "check the more reliable of the two
        signals" (both are checked)."""
        _write(
            tmp_path,
            "src/pkg/config.py",
            "from pathlib import Path\n"
            "from pydantic import BaseModel, Field\n\n\n"
            "class AppConfig(BaseModel):\n"
            '    workdir: Path = Field(default=Path("relative/dir"))\n',
        )
        _git_init(tmp_path)
        violations = config_path_default_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].file == "src/pkg/config.py"

    def test_file_scoped_waiver_covers_it(self, tmp_path: Path) -> None:
        """A `frob:waive CONFIGPATH001` directive anywhere in the same
        source file waives the finding -- the standard file-scoped
        waiver mechanism, for a deliberately relative-to-package-root
        default."""
        _write(
            tmp_path,
            "src/pkg/config.py",
            '# frob:waive CONFIGPATH001 reason="deliberately relative to package root"\n'
            "from pydantic import BaseModel, Field\n\n\n"
            "class AppConfig(BaseModel):\n"
            '    state_path: str = Field(default="relative/dir/state.json")\n',
        )
        _git_init(tmp_path)
        from frob.gates import _apply_waivers  # noqa: PLC0415 - internal, test-only
        from tests.conftest import _snapshot  # noqa: PLC0415 - internal, test-only

        snapshot = _snapshot(tmp_path)
        raw = config_path_default_gate(tmp_path)
        assert len(raw) == 1
        kept, waived = _apply_waivers(raw, snapshot)
        assert kept == ()
        assert len(waived) == 1

    def test_non_path_field_default_is_ignored(self, tmp_path: Path) -> None:
        """A field with no `*_path` name and no `Path` annotation is not
        this gate's concern at all, regardless of its default value."""
        _write(
            tmp_path,
            "src/pkg/config.py",
            "from pydantic import BaseModel, Field\n\n\n"
            "class AppConfig(BaseModel):\n"
            '    name: str = Field(default="relative/looking/but/irrelevant")\n',
        )
        _git_init(tmp_path)
        assert config_path_default_gate(tmp_path) == ()

    def test_no_python_files_is_silent(self, tmp_path: Path) -> None:
        _write(tmp_path, "README.md", "hello\n")
        _git_init(tmp_path)
        assert config_path_default_gate(tmp_path) == ()
