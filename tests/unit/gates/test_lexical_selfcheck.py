"""LEXCHECK001: a gate rule that decides a code fact from raw text with no
symref/AST binding is itself a finding (T-1662/T-2344,
docs/design/gate-semantics-classification.md)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.gates._lexical_selfcheck import lexical_selfcheck_gate


def _init_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)


def _commit(tmp_path: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "c"], cwd=tmp_path, check=True)


def _write_gate_module(tmp_path: Path, name: str, source: str) -> None:
    pkg = tmp_path / "src" / "frob" / "gates"
    pkg.mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "frob" / "__init__.py").write_text("")
    (pkg / "__init__.py").write_text("")
    (pkg / name).write_text(source)


class TestLexcheck001:
    """`lexical_selfcheck_gate`: flags a NEW single-function lexical
    decider, stays silent on allowlisted and non-decision code."""

    def test_new_lexical_decider_is_flagged(self, tmp_path: Path) -> None:
        """A function that both `re.search`-decides and constructs a
        symref-less `Violation` -- the exact REF001-pre-fix shape -- is
        caught, proving this is not a check that always finds nothing."""
        _init_repo(tmp_path)
        _write_gate_module(
            tmp_path,
            "_offender.py",
            "import re\n"
            "from frob.gates._models import Severity, Violation\n"
            "\n"
            "_MARKER_RE = re.compile(r'x')\n"
            "\n"
            "def _bad_gate(rel_path, text):\n"
            "    if re.search(r'needle', text):\n"
            "        return Violation(rule='X', severity=Severity.ERROR, "
            "file=rel_path, line=1, message='m')\n"
            "    return None\n",
        )
        _commit(tmp_path)

        violations = lexical_selfcheck_gate(tmp_path)

        hits = [v for v in violations if v.rule == "LEXCHECK001"]
        assert len(hits) == 1
        assert hits[0].file == "src/frob/gates/_offender.py"
        assert "_bad_gate" in hits[0].message

    def test_allowlisted_function_is_silent(self, tmp_path: Path) -> None:
        """The identical decider shape, at an `_ALLOWLIST`-listed (module,
        function) pair, is not flagged -- an allowlist entry actually
        suppresses, it is not decorative."""
        from frob.gates import _lexical_selfcheck as mod

        _init_repo(tmp_path)
        _write_gate_module(
            tmp_path,
            "_secrets.py",
            "import re\n"
            "from frob.gates._models import Severity, Violation\n"
            "\n"
            "def _stale_fake_marker_violations(rel_path, text):\n"
            "    if re.search(r'needle', text):\n"
            "        return [Violation(rule='SEC004', severity=Severity.WARN, "
            "file=rel_path, line=1, message='m')]\n"
            "    return []\n",
        )
        _commit(tmp_path)

        assert (
            "src/frob/gates/_secrets.py",
            "_stale_fake_marker_violations",
        ) in mod._ALLOWLIST
        violations = lexical_selfcheck_gate(tmp_path)
        assert [v for v in violations if v.rule == "LEXCHECK001"] == []

    def test_semantic_function_with_incidental_regex_is_silent(
        self, tmp_path: Path
    ) -> None:
        """A function that DOES call `re.search` but only attaches
        `symref=` on every `Violation` it builds is not flagged -- the
        regex call alone is not the signal, a symref-less finding is."""
        _init_repo(tmp_path)
        _write_gate_module(
            tmp_path,
            "_semantic.py",
            "import re\n"
            "from frob.gates._models import Severity, Violation\n"
            "\n"
            "def _good_gate(rel_path, symref, text):\n"
            "    if re.search(r'needle', text):\n"
            "        return Violation(rule='X', severity=Severity.ERROR, "
            "file=rel_path, line=1, message='m', symref=symref)\n"
            "    return None\n",
        )
        _commit(tmp_path)

        violations = lexical_selfcheck_gate(tmp_path)
        assert [v for v in violations if v.rule == "LEXCHECK001"] == []

    def test_non_gate_code_never_scanned(self, tmp_path: Path) -> None:
        """A lexical decider OUTSIDE `src/frob/gates/` (this gate's own
        declared scope, T-2344) is never scanned -- this check is about
        gate rules specifically, not a repo-wide lint."""
        _init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob" / "app"
        pkg.mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (pkg / "__init__.py").write_text("")
        (pkg / "offender_runner.py").write_text(
            "import re\n"
            "from frob.gates._models import Severity, Violation\n"
            "\n"
            "def _bad(rel_path, text):\n"
            "    if re.search(r'needle', text):\n"
            "        return Violation(rule='X', severity=Severity.ERROR, "
            "file=rel_path, line=1, message='m')\n"
            "    return None\n"
        )
        _commit(tmp_path)

        violations = lexical_selfcheck_gate(tmp_path)
        assert [v for v in violations if v.rule == "LEXCHECK001"] == []

    def test_every_known_gates_module_module_stays_clean(self) -> None:
        """This repo's OWN `src/frob/gates/**` scans against the real
        checkout (the same target the wired-in `lexcheck` stage evaluates
        at `frob check` time): every real instance this gate found during
        T-2344's own development is either allowlisted (a stated class-(b)
        reason) or waived in-file with a follow-up ticket citation --
        `_wire001_cli_dest_violations` (T-2348) is the ONE known, waived
        exception. `lexical_selfcheck_gate` itself does not apply waivers
        (that is `frob check`'s own outer pass, matching every other gate
        in this repo), so this asserts the RAW finding set is exactly that
        one known site -- a regression here means a NEW, unaccounted-for
        lexical decider landed."""
        from frob.gitio import repo_root

        root = repo_root(Path(__file__).parent).danger_ok
        violations = lexical_selfcheck_gate(root)
        hits = [v for v in violations if v.rule == "LEXCHECK001"]
        assert [v.file for v in hits] == ["src/frob/gates/_wire.py"]
