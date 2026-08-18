"""LEXCHECK001: a gate rule that decides a code fact from raw text with no
symref/AST binding is itself a finding (T-1662/T-2344,
docs/design/gate-semantics-classification.md)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

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

    #: T-2466's OWN widening surfaced 5 real, previously-unscanned
    #: LEXCHECK001 hits (module docstring's own T-2466 note) --
    #: `src/frob/vet/_supplychain.py` decided from `re.search`/`re.match`
    #: over TOML/JSON/YAML manifest text and built a symref-less
    #: `Violation` in five separate functions. T-2469 fixed all five at
    #: the ROOT rather than allowlisting them: each detector now decides
    #: from a REAL parse of its manifest format (`tomllib`/`json`/
    #: `packaging.requirements.Requirement`/`ast`/`configparser`/`yaml`)
    #: instead of a text regex, so `_supplychain.py` no longer imports
    #: `re` at all -- mirrors the T-2348/`_wire001_cli_dest_violations`
    #: precedent this test used to cite for the identical situation, one
    #: level further: T-2348 kept the regex but added a `symref=`;
    #: T-2469 removed the regex entirely. This backlog set is therefore
    #: EMPTY again -- kept as a named (not deleted) frozenset so a FUTURE
    #: regression in this same package restores it by name rather than
    #: reaching for a blind `== []`.
    _KNOWN_SUPPLYCHAIN_LEXCHECK001_BACKLOG: frozenset[tuple[str, str]] = frozenset()

    def test_supplychain_lexcheck001_backlog_is_empty_t2469(self) -> None:
        """This repo's OWN `DETECTOR_PACKAGE_ROOTS` scan (T-2466: widened
        past `src/frob/gates/**` alone to include `vet/`/`strata/`/
        `check/` too) against the real checkout (the same target the
        wired-in `lexcheck` stage evaluates at `frob check` time): every
        real instance this gate found during T-2344's own development is
        either allowlisted (a stated class-(b) reason) or fixed outright.
        T-2469 fixed the last disclosed exception
        (`_KNOWN_SUPPLYCHAIN_LEXCHECK001_BACKLOG`, see its own comment)
        at the root, so this asserts the RAW finding set is EXACTLY
        empty -- a regression here means a NEW, unaccounted-for lexical
        decider landed in ANY of the widened scope's packages, not just
        `gates/`."""
        from frob.gitio import repo_root

        root = repo_root(Path(__file__).parent).danger_ok
        violations = lexical_selfcheck_gate(root)
        hits = [v for v in violations if v.rule == "LEXCHECK001"]
        # (file, function) read directly off each Violation's own fields
        # (`.file` plus the function-name token in `.message`) rather
        # than re-deriving either from scratch.
        hit_keys = {(hit.file, hit.message.split(" ")[2]) for hit in hits}
        assert hit_keys == self._KNOWN_SUPPLYCHAIN_LEXCHECK001_BACKLOG

    def test_vet_needle_matcher_shape_is_flagged(self, tmp_path: Path) -> None:
        """T-2466's own must-now-fire control: a detector living under
        `src/frob/vet/` that decides via `bytes.find` needle matching (the
        literal mechanism T-2457's pre-fix `fs.write` detector used) and
        constructs a symref-less `Violation` is caught, where it would
        NOT have been before this ticket (wrong package, wrong trigger).
        This is a single-function COLLAPSE of T-2457's real cross-module
        shape (module docstring's "Known v1 limitation" note explains
        why a byte-for-byte reproduction cannot be caught by the v1
        per-function detection shape either, before or after T-2466)."""
        _init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob" / "vet"
        pkg.mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (pkg / "__init__.py").write_text("")
        (pkg / "_offender_capability.py").write_text(
            "from frob.gates._models import Severity, Violation\n"
            "\n"
            "def _matched_capabilities(rel_path, text, needles):\n"
            "    for needle in needles:\n"
            "        idx = text.find(needle)\n"
            "        if idx != -1:\n"
            "            return Violation(rule='SELFAUDIT001', "
            "severity=Severity.ERROR, file=rel_path, line=1, message='m')\n"
            "    return None\n",
        )
        _commit(tmp_path)

        violations = lexical_selfcheck_gate(tmp_path)

        hits = [v for v in violations if v.rule == "LEXCHECK001"]
        assert len(hits) == 1
        assert hits[0].file == "src/frob/vet/_offender_capability.py"
        assert "_matched_capabilities" in hits[0].message

    def test_elementtree_find_is_not_a_trigger(self, tmp_path: Path) -> None:
        """The `.find(` trigger excludes an ElementTree-shaped call (this
        repo's own `_el`/`_element` naming convention, `_coverage.py`'s
        real `class_el.find("lines")` shape) -- widening the trigger past
        `re.*` must not turn a coverage-XML tree lookup into a false
        LEXCHECK001 positive."""
        _init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob" / "vet"
        pkg.mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (pkg / "__init__.py").write_text("")
        (pkg / "_offender_xml.py").write_text(
            "from frob.gates._models import Severity, Violation\n"
            "\n"
            "def _xml_gate(rel_path, root_el):\n"
            "    sources_el = root_el.find('sources')\n"
            "    if sources_el is None:\n"
            "        return Violation(rule='X', severity=Severity.ERROR, "
            "file=rel_path, line=1, message='m')\n"
            "    return None\n",
        )
        _commit(tmp_path)

        violations = lexical_selfcheck_gate(tmp_path)
        assert [v for v in violations if v.rule == "LEXCHECK001"] == []

    def test_scans_scope_is_disclosed_in_log(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T-2466's must-report-scope control: every run logs the scanned
        package-root set alongside its count, PORT001's own T-2388
        convention, so a caller can never read a count as repo-wide when
        it names only `DETECTOR_PACKAGE_ROOTS`."""
        import logging

        from frob.gates._detector_scope import DETECTOR_PACKAGE_ROOTS

        _init_repo(tmp_path)
        _write_gate_module(
            tmp_path, "_noop.py", "def _harmless():\n    return None\n"
        )
        _commit(tmp_path)

        with caplog.at_level(logging.WARNING):
            lexical_selfcheck_gate(tmp_path)

        [scope_line] = [
            r.message for r in caplog.records if "lexical_selfcheck_gate: scanned" in r.message
        ]
        assert "ONLY" in scope_line
        for root_prefix in DETECTOR_PACKAGE_ROOTS:
            assert root_prefix in scope_line
