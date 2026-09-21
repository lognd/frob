"""Tests for the derived-wrapper generation and drift gate (T-4760):
`frob.scaffold._managed`'s Makefile/make.bat wrapper-target managed
blocks, and `frob.gates._wrapper_drift.wrapper_drift_gate`.
"""

from __future__ import annotations

from frob.gates._wrapper_drift import wrapper_drift_gate
from frob.scaffold._managed import apply_managed_blocks


def _write_frob_toml(root, body: str) -> None:
    """Write `body` as `root`'s `frob.toml`."""
    (root / "frob.toml").write_text(body)


class TestApplyGeneratesWrapperBlocks:
    """`apply_managed_blocks` regenerating the Makefile/make.bat wrapper
    targets from a project's `[commands]` table."""

    def test_no_frob_toml_emits_native_default_names(self, tmp_path):
        """With no `frob.toml` at all, both wrapper files still get the
        four always-invocable native-default names."""
        result = apply_managed_blocks(tmp_path)
        assert result.is_ok
        makefile = (tmp_path / "Makefile").read_text()
        makebat = (tmp_path / "make.bat").read_text()
        for name in ("check", "format", "lint", "test"):
            assert f"{name}:\n\tfrob run {name}" in makefile
            assert f'if "%1"=="{name}" (frob run {name}' in makebat

    def test_declared_commands_entry_gets_a_wrapper_target(self, tmp_path):
        """A `[commands]` entry with no native default (e.g. `build`)
        still gets a generated wrapper target once declared."""
        _write_frob_toml(tmp_path, '[commands]\nbuild = ["cmake", "--build", "."]\n')
        result = apply_managed_blocks(tmp_path)
        assert result.is_ok
        makefile = (tmp_path / "Makefile").read_text()
        assert "build:\n\tfrob run build" in makefile

    def test_second_apply_is_byte_identical(self, tmp_path):
        """Running `apply` twice produces byte-identical wrapper files
        (acceptance criterion 3)."""
        apply_managed_blocks(tmp_path)
        makefile_1 = (tmp_path / "Makefile").read_text()
        makebat_1 = (tmp_path / "make.bat").read_text()
        result = apply_managed_blocks(tmp_path)
        assert result.is_ok
        assert any("already current" in line for line in result.danger_ok)
        assert (tmp_path / "Makefile").read_text() == makefile_1
        assert (tmp_path / "make.bat").read_text() == makebat_1

    def test_makefile_and_makebat_target_sets_are_equal(self, tmp_path):
        """Acceptance criterion 4: the generated Makefile and make.bat
        target sets match."""
        _write_frob_toml(tmp_path, '[commands]\nbuild = ["cmake", "--build", "."]\n')
        apply_managed_blocks(tmp_path)
        assert wrapper_drift_gate(tmp_path) == ()

    def test_core_shim_skipped_when_no_stamp_defined(self, tmp_path):
        """The native-build core-shim is not applied to a Makefile that
        defines no `STAMP` variable (T-4760's cpp defect fix): applying
        it there left `core: $(STAMP)` expanding to an unconditional
        prerequisite with no venv to gate a native build behind."""
        (tmp_path / "Makefile").write_text("BUILD_DIR := build\n\nall:\n\techo hi\n")
        result = apply_managed_blocks(tmp_path)
        assert result.is_ok
        assert any(
            "makefile-core-shim" in line and "skipped" in line
            for line in result.danger_ok
        )
        assert "core:" not in (tmp_path / "Makefile").read_text()

    def test_core_shim_applied_when_stamp_defined(self, tmp_path):
        """The core-shim still applies normally to a Makefile that does
        define `STAMP` (python's own reference Makefile shape)."""
        (tmp_path / "Makefile").write_text(
            "STAMP := .venv/.install-stamp\n\ninstall: $(STAMP)\n"
        )
        result = apply_managed_blocks(tmp_path)
        assert result.is_ok
        assert "core: $(STAMP)" in (tmp_path / "Makefile").read_text()


class TestWrapperDriftGate:
    """`wrapper_drift_gate` over an applied project."""

    def test_no_managed_block_is_clean(self, tmp_path):
        """A project with no wrapper managed block at all (never ran
        `frob scaffold apply`) reports no drift -- there is nothing
        generated yet to have drifted from."""
        assert wrapper_drift_gate(tmp_path) == ()

    def test_freshly_applied_project_is_clean(self, tmp_path):
        """Immediately after `apply`, the gate finds nothing to report."""
        apply_managed_blocks(tmp_path)
        assert wrapper_drift_gate(tmp_path) == ()

    def test_inline_sequence_in_target_body_is_wrap001(self, tmp_path):
        """Acceptance criterion 1: a target body that expands two steps
        inline is reported, and the message names the target."""
        apply_managed_blocks(tmp_path)
        makefile = tmp_path / "Makefile"
        text = makefile.read_text()
        text = text.replace(
            "check:\n\tfrob run check",
            "check:\n\tfrob run lint && frob run test",
        )
        makefile.write_text(text)
        violations = wrapper_drift_gate(tmp_path)
        assert any(v.rule == "WRAP001" and "check" in v.message for v in violations)

    def test_target_for_removed_commands_entry_is_wrap002(self, tmp_path):
        """Acceptance criterion 2: a Makefile target naming an entry that
        is not (or no longer) declared in `[commands]` -- here forged
        directly, standing in for a stale post-removal Makefile -- is
        reported."""
        apply_managed_blocks(tmp_path)
        makefile = tmp_path / "Makefile"
        text = makefile.read_text()
        text = text.replace(
            "# frob:managed-block END makefile-wrapper-targets",
            "not-a-real-entry:\n\tfrob run not-a-real-entry\n"
            "# frob:managed-block END makefile-wrapper-targets",
        )
        makefile.write_text(text)
        violations = wrapper_drift_gate(tmp_path)
        assert any(
            v.rule == "WRAP002" and "not-a-real-entry" in v.message for v in violations
        )

    def test_mismatched_target_sets_is_wrap003(self, tmp_path):
        """Makefile and make.bat with different target/branch sets is
        reported as WRAP003."""
        apply_managed_blocks(tmp_path)
        makebat = tmp_path / "make.bat"
        text = makebat.read_text()
        text = text.replace(
            ":: frob:managed-block END makebat-wrapper-targets",
            'if "%1"=="lonely" (frob run lonely & exit /b %errorlevel%)\n'
            ":: frob:managed-block END makebat-wrapper-targets",
        )
        makebat.write_text(text)
        violations = wrapper_drift_gate(tmp_path)
        assert any(v.rule == "WRAP003" for v in violations)

    def test_uv_run_prefixed_delegation_is_not_drift(self, tmp_path):
        """`uv run frob run <name>` is an equally valid single delegating
        call, not drift -- some project types invoke frob through their
        own venv rather than the global tool install."""
        apply_managed_blocks(tmp_path)
        makefile = tmp_path / "Makefile"
        text = makefile.read_text().replace(
            "check:\n\tfrob run check", "check:\n\tuv run frob run check"
        )
        makefile.write_text(text)
        violations = wrapper_drift_gate(tmp_path)
        assert not any(v.rule == "WRAP001" for v in violations)
