"""Tests for `frob.doctor.native_degrade_warning` (T-3011): the loud,
by-name, PLATFORM001-doctrine stderr warning printed on every subcommand
when `frob_core`/`strata_core` are not importable -- see the function's
own docstring and docs/guides/release.md's "Decision 2" for the full
reasoning (an sdist-fallback silent Rust build was rejected in favor of
this)."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob import doctor
from frob.doctor import (
    ExternalToolStatus,
    NativeExtensionStatus,
    ToolCategory,
    UnityEditorStatus,
    _diagnose_unity_toolchain,
    _external_tools_remediation,
    _locate_unity_editor,
    native_degrade_warning,
    scan_external_tools,
)


class TestNativeDegradeWarning:
    """Must-fire fixture: a wheel-less/natives-less environment MUST
    produce a loud message naming every missing extension, and a fully-
    accelerated environment MUST NOT produce any message at all."""

    def test_missing_extensions_named_loudly(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Both natives missing: the message names BOTH `frob_core` and
        `strata_core` explicitly -- not a generic "something is missing"
        line. This is the must-fire case the whole degrade doctrine
        exists to guarantee."""
        monkeypatch.setattr(
            doctor,
            "_extension_status",
            lambda name: NativeExtensionStatus(name=name, available=False),
        )
        message = native_degrade_warning(tmp_path)
        assert message is not None
        assert "frob_core" in message
        assert "strata_core" in message
        assert "pure-Python mode" in message

    def test_fully_accelerated_produces_no_warning(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Both natives importable: `None`, not an empty/quiet message --
        this is the common case and it must never fire here."""
        monkeypatch.setattr(
            doctor,
            "_extension_status",
            lambda name: NativeExtensionStatus(
                name=name, available=True, version="0.1.0"
            ),
        )
        assert native_degrade_warning(tmp_path) is None

    def test_partial_availability_still_names_the_missing_one(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Only one of the two natives missing: the message names exactly
        the missing one, not the available one -- proves this is a real
        per-extension check, not an all-or-nothing flag."""

        def fake_status(name: str) -> NativeExtensionStatus:
            return NativeExtensionStatus(
                name=name, available=(name == "frob_core"), version=None
            )

        monkeypatch.setattr(doctor, "_extension_status", fake_status)
        message = native_degrade_warning(tmp_path)
        assert message is not None
        assert "strata_core" in message
        assert "frob_core" not in message.split("--")[0].split("(")[1]

    def test_source_checkout_gets_make_core_hint(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A `repo_root` containing `frob-core/Cargo.toml` (a source
        checkout) gets pointed at `make core`, not the PyPI extra -- the
        wrong remediation for a dev checkout would send a contributor on
        a pointless `pip install` detour."""
        monkeypatch.setattr(
            doctor,
            "_extension_status",
            lambda name: NativeExtensionStatus(name=name, available=False),
        )
        (tmp_path / "frob-core").mkdir()
        (tmp_path / "frob-core" / "Cargo.toml").write_text("", encoding="utf-8")
        message = native_degrade_warning(tmp_path)
        assert message is not None
        assert "make core" in message

    def test_installed_package_gets_pip_extra_hint(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """No source checkout under `repo_root` (or `repo_root=None`): the
        remediation names the PyPI `frob[native]` extra, not `make core`
        (which an installed-package adopter has no Rust toolchain or
        source tree to run)."""
        monkeypatch.setattr(
            doctor,
            "_extension_status",
            lambda name: NativeExtensionStatus(name=name, available=False),
        )
        message = native_degrade_warning(tmp_path)
        assert message is not None
        assert "frob[native]" in message
        assert native_degrade_warning(None) is not None


class TestScanExternalTools:
    """T-3276: `scan_external_tools` probes every `_EXTERNAL_TOOLS` entry
    -- binaries via `shutil.which`+`--version`, Python packages via
    `importlib.metadata.version` -- and never raises regardless of what
    is present or absent."""

    def test_present_binary_reports_version(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A binary found on PATH reports present=True with a probed
        version string."""
        monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/usr/bin/{name}")
        monkeypatch.setattr(doctor, "_probe_binary_version", lambda name: f"{name} 1.0")
        statuses = {s.name: s for s in scan_external_tools()}
        assert statuses["git"].present is True
        assert statuses["git"].version == "git 1.0"

    def test_missing_binary_reports_absent_with_install_hint(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A binary NOT found on PATH reports present=False, version=None,
        and still carries its `install_hint` (T-3276's must-fire fixture:
        the loud failure must name the tool and how to install it)."""
        monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
        statuses = {s.name: s for s in scan_external_tools()}
        assert statuses["git"].present is False
        assert statuses["git"].version is None
        assert statuses["git"].install_hint

    def test_present_package_reports_version_via_importlib(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A Python-plugin entry (pytest-xdist/pytest-cov) is probed via
        `importlib.metadata.version`, never `shutil.which` (it is loaded
        in-process by pytest, not spawned as its own binary)."""
        monkeypatch.setattr(doctor, "version", lambda name: "3.8.0")
        statuses = {s.name: s for s in scan_external_tools()}
        assert statuses["pytest-xdist"].present is True
        assert statuses["pytest-xdist"].version == "3.8.0"

    def test_missing_package_reports_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`importlib.metadata.version` raising (package not installed)
        reports present=False, never propagates the exception -- this is
        the exact F-011 shape: pytest-xdist absent in a consumer venv."""

        def _raise(name: str) -> str:
            raise ModuleNotFoundError(name)

        monkeypatch.setattr(doctor, "version", _raise)
        statuses = {s.name: s for s in scan_external_tools()}
        assert statuses["pytest-xdist"].present is False
        assert statuses["pytest-xdist"].version is None


class TestExternalToolsRemediation:
    """T-3276: only a missing REQUIRED tool produces a remediation line --
    the category rule (`ToolCategory`'s own docstring) applied."""

    def test_missing_required_tool_names_it_and_the_install_command(self) -> None:
        """Must-fire fixture: a REQUIRED tool's absence names the tool
        and the install command in the returned remediation text."""
        statuses = [
            ExternalToolStatus(
                name="git",
                category=ToolCategory.REQUIRED,
                present=False,
                version=None,
                install_hint="install git (https://git-scm.com)",
            )
        ]
        remediation = _external_tools_remediation(statuses)
        assert remediation is not None
        assert "git" in remediation
        assert "git-scm.com" in remediation

    def test_missing_optional_tool_is_silent(self) -> None:
        """An OPTIONAL or OPTIONAL_FOR_GATE tool's absence never produces
        a `frob doctor` remediation line -- that is the affected gate's
        own UNMEASURED concern, never a doctor health failure."""
        statuses = [
            ExternalToolStatus(
                name="cargo",
                category=ToolCategory.OPTIONAL,
                present=False,
                version=None,
                install_hint="install rustup",
            ),
            ExternalToolStatus(
                name="pytest-xdist",
                category=ToolCategory.OPTIONAL_FOR_GATE,
                present=False,
                version=None,
                install_hint="pip install pytest-xdist",
            ),
        ]
        assert _external_tools_remediation(statuses) is None


class TestRelevantToolFindings:
    """T-5139: a gate-serving tool (`_RELEVANT_TOOLS`) is reported only
    when its `relevant_when` predicate is true for this repo AND it is
    missing/failed -- "not needed here" is never a finding."""

    def test_relevant_missing_tool_is_a_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/doctor.py::relevant_tool_findings kind="unit"
        # Positive control: a planted Cargo.lock (cargo-audit's own
        # relevant_when) plus a guaranteed-absent binary must yield a
        # real finding naming VET005 and the install remedy.
        from frob import doctor

        (tmp_path / "Cargo.lock").write_text("", encoding="utf-8")
        monkeypatch.setattr(doctor.shutil, "which", lambda _name: None)

        findings = doctor.relevant_tool_findings(tmp_path)
        assert len(findings) == 1
        finding = findings[0]
        assert finding.entry.name == "cargo-audit"
        assert "VET005" in finding.entry.rules_it_serves
        assert finding.kind == doctor.RelevantToolFailureKind.MISSING
        assert "cargo install cargo-audit" == finding.entry.install_remedy

    def test_irrelevant_missing_tool_is_not_a_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/doctor.py::relevant_tool_findings kind="unit"
        # No Cargo.lock: cargo-audit's absence is "not needed here", not
        # a finding, even though the binary is still absent.
        from frob import doctor

        monkeypatch.setattr(doctor.shutil, "which", lambda _name: None)

        assert doctor.relevant_tool_findings(tmp_path) == []

    def test_relevant_present_tool_is_not_a_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/doctor.py::relevant_tool_findings kind="unit"
        from frob import doctor

        (tmp_path / "Cargo.lock").write_text("", encoding="utf-8")
        monkeypatch.setattr(
            doctor.shutil, "which", lambda _name: "/usr/bin/cargo-audit"
        )

        assert doctor.relevant_tool_findings(tmp_path) == []


class TestUnityEditorStatus:
    """T-4501: `_locate_unity_editor` searches env vars, then Unity Hub's
    default per-OS install root, then PATH, in that precedence order, and
    never raises regardless of what is present or absent."""

    def test_present_via_env_reports_version(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """`UNITY_PATH` pointing at an existing file wins over every other
        source -- an explicit pinned override always wins."""
        binary = tmp_path / "Unity"
        binary.write_text("", encoding="utf-8")
        monkeypatch.setenv("UNITY_PATH", str(binary))
        monkeypatch.delenv("UNITY_EDITOR", raising=False)
        status = _locate_unity_editor()
        assert status.present is True
        assert status.path == str(binary)

    def test_present_via_hub_default_root(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """No env override: a Unity Hub default install root with a
        versioned editor directory is found, and the newest version (by
        name, sorted descending) is reported when more than one exists."""
        monkeypatch.delenv("UNITY_PATH", raising=False)
        monkeypatch.delenv("UNITY_EDITOR", raising=False)
        monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
        hub_root = tmp_path / "Hub" / "Editor"
        for v in ("2021.3.1f1", "2022.3.5f1"):
            version_dir = hub_root / v
            binary = doctor._unity_editor_binary_for_version_dir(version_dir)
            binary.parent.mkdir(parents=True)
            binary.write_text("", encoding="utf-8")
        monkeypatch.setattr(doctor, "_unity_hub_default_roots", lambda: (hub_root,))
        status = _locate_unity_editor()
        assert status.present is True
        assert status.version == "2022.3.5f1"

    def test_present_via_path(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """No env override and no Hub default root present: falls back to
        a plain PATH lookup for the `Unity`/`unity` binary."""
        monkeypatch.delenv("UNITY_PATH", raising=False)
        monkeypatch.delenv("UNITY_EDITOR", raising=False)
        monkeypatch.setattr(doctor, "_unity_hub_default_roots", lambda: ())
        monkeypatch.setattr(doctor.shutil, "which", lambda name: "/usr/local/bin/Unity")
        status = _locate_unity_editor()
        assert status.present is True
        assert status.path == "/usr/local/bin/Unity"

    def test_absent_reports_not_found(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """No env override, no Hub default root, nothing on PATH: reports
        `present=False` -- never raises, never a `frob doctor` failure
        (OPTIONAL category)."""
        monkeypatch.delenv("UNITY_PATH", raising=False)
        monkeypatch.delenv("UNITY_EDITOR", raising=False)
        monkeypatch.setattr(doctor, "_unity_hub_default_roots", lambda: ())
        monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
        status = _locate_unity_editor()
        assert status.present is False
        assert status.path is None


class TestUnityProjectDiagnosis:
    """T-4501: `_diagnose_unity_toolchain` gates Unity editor detection on
    `detect_unity_project` -- a non-Unity root must never attempt Unity
    detection at all (the story's own third acceptance criterion)."""

    def test_unity_project_reports_editor_status(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A genuine Unity project root (Assets/ + ProjectVersion.txt)
        reports both the project info (with its editor version) and the
        located editor status."""
        (tmp_path / "Assets").mkdir()
        settings = tmp_path / "ProjectSettings"
        settings.mkdir()
        (settings / "ProjectVersion.txt").write_text(
            "m_EditorVersion: 2022.3.5f1\n", encoding="utf-8"
        )
        monkeypatch.setattr(
            doctor,
            "_locate_unity_editor",
            lambda: UnityEditorStatus(present=False),
        )
        project, editor = _diagnose_unity_toolchain(tmp_path)
        assert project is not None
        assert project.editor_version == "2022.3.5f1"
        assert editor is not None
        assert editor.present is False

    def test_non_unity_project_skips_unity_detection(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A plain, non-Unity root never even calls `_locate_unity_editor`
        -- no spurious 'Unity not found' noise for unrelated projects."""
        called = False

        def _fail_if_called() -> UnityEditorStatus:
            nonlocal called
            called = True
            return UnityEditorStatus(present=False)

        monkeypatch.setattr(doctor, "_locate_unity_editor", _fail_if_called)
        project, editor = _diagnose_unity_toolchain(tmp_path)
        assert project is None
        assert editor is None
        assert called is False


class TestProfileRecommendation:
    """`profile_recommendation` (T-4416): advisory-only nudge toward
    `[profile] profile = "rapid"` once `root` crosses `doctor.
    _PROFILE_RECOMMEND_THRESHOLD` on either the ticket-count or
    file-count axis; `None` (no recommendation, never force `rapid`)
    below both -- matching this ticket's acceptance criteria 2/3."""

    def test_below_threshold_recommends_nothing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_doctor.py::TestProfileRecommendation.test_below_threshold_recommends_nothing  # noqa: E501
        """A tiny repo (both axes at 0) gets no recommendation at all --
        acceptance criterion 3: never force `rapid` below threshold."""
        monkeypatch.setattr("frob.excludes.iter_files", lambda root, **_: ())

        class _EmptyQueue:
            tickets: tuple = ()

        from typani.result import Ok

        monkeypatch.setattr("frob.tickets.load_queue", lambda root: Ok(_EmptyQueue()))
        assert doctor.profile_recommendation(tmp_path) is None

    def test_ticket_count_above_threshold_recommends_rapid(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_doctor.py::TestProfileRecommendation.test_ticket_count_above_threshold_recommends_rapid  # noqa: E501
        """Ticket count alone above `_PROFILE_RECOMMEND_THRESHOLD.
        ticket_count` is enough to recommend `rapid` (an OR check,
        matching acceptance criterion 2) -- the message cites the
        measured ticket count."""
        monkeypatch.setattr("frob.excludes.iter_files", lambda root, **_: ())

        class _BigQueue:
            tickets = tuple(range(5000))

        from typani.result import Ok

        monkeypatch.setattr("frob.tickets.load_queue", lambda root: Ok(_BigQueue()))
        message = doctor.profile_recommendation(tmp_path)
        assert message is not None
        assert "5000" in message
        assert "rapid" in message

    def test_file_count_above_threshold_recommends_rapid(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_doctor.py::TestProfileRecommendation.test_file_count_above_threshold_recommends_rapid  # noqa: E501
        """File count alone above `_PROFILE_RECOMMEND_THRESHOLD.
        file_count` is enough to recommend `rapid`, even with zero
        tickets -- the message cites the measured file count."""
        monkeypatch.setattr(
            "frob.excludes.iter_files",
            lambda root, **_: tuple(Path(f"f{i}.py") for i in range(1500)),
        )

        class _EmptyQueue:
            tickets: tuple = ()

        from typani.result import Ok

        monkeypatch.setattr("frob.tickets.load_queue", lambda root: Ok(_EmptyQueue()))
        message = doctor.profile_recommendation(tmp_path)
        assert message is not None
        assert "1500" in message
        assert "rapid" in message


class TestLandProfilesDocMatchesCode:
    """T-4416 acceptance criterion 1: `docs/modules/land-profiles.md`
    describes `rapid` as scoped-synchronous (diff plus dependents) and
    `standard` as unscoped-synchronous (full check), matching their
    actual post-T-4413 behavior -- a plain text assertion, since the
    doc's whole job here is to state that correctly in prose."""

    def test_doc_names_rapid_scoped_and_standard_unscoped(self) -> None:
        # frob:tests tests/unit/test_doctor.py::TestLandProfilesDocMatchesCode.test_doc_names_rapid_scoped_and_standard_unscoped  # noqa: E501
        doc_path = (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "modules"
            / "land-profiles.md"
        )
        text = doc_path.read_text(encoding="utf-8")
        assert "rapid = scoped-synchronous" in text
        assert "standard = unscoped-synchronous" in text
        assert "diff-touched files plus their DIRECT dependents" in text
