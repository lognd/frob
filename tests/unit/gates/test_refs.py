"""Tests for T-1665: REF001/REF002 decide `.py` inbound references from a
real resolved import (`frob.graph.imports.build_import_graph`), not a
path/basename TEXT mention -- plus T-1664's `Severity.UNRESOLVED` for a
`.py` target this substrate genuinely cannot determine (a dynamic
import/dispatch call that plausibly names it).

Fixtures are synthetic tempfile-backed git repos, same posture as
`tests/test_refs_gate.py` (the pre-existing, broader REF001/002/003
suite this file complements rather than duplicates -- see that file for
the round-2/round-3 regression coverage and the markdown-waiver/native-
stub/entrypoint-allowlist tests, none of which this ticket's semantic
change touches).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.findings import Severity
from frob.gates._refs import ref_gate


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


# frob:waive DUP001 reason="synthetic-tempfile-git-repo fixture helper, already \
# duplicated verbatim across 10+ existing gate test files (test_docblocks_gate.py, \
# test_docptr_gate.py, test_gitio.py, test_pii_structural_gate.py, test_refs_gate.py, \
# test_secrets_gate.py, test_testing.py, test_tickets_mutation_evidence.py, \
# test_walk_lint_gate.py, test_walk_migration.py) with no shared extraction anywhere \
# in the repo -- this file matches the same established, if imperfect, per-test-file \
# convention rather than being the one file that diverges from it; a real \
# shared-fixture extraction is a repo-wide follow-up, not this ticket's scope"
def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "main")


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# frob:ticket T-1665
class TestResolvedImportChannel:
    """A `.py` target's inbound reference is a REAL AST-resolved import,
    not a text token that merely LOOKS like one.

    frob:ticket T-2369
    """

    def test_import_alias_reaches_the_real_target_not_the_alias_name(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_refs.py::ref_gate
        # An import alias (`import pkg.target as t`) never spells the
        # target's own path/basename anywhere in the importer's text --
        # the OLD text-token scan could not see this at all. The real
        # AST resolver reads the import statement's actual module name,
        # unaffected by what the caller chooses to alias it as.
        _init_repo(tmp_path)
        _write(tmp_path, "pkg/target.py", "def run(): pass\n")
        _write(tmp_path, "pkg/__init__.py", "")
        _write(
            tmp_path,
            "caller.py",
            "import pkg.target as t\nt.run()\n",
        )
        _write(
            tmp_path,
            "other_caller.py",
            "import pkg.target as t2\nt2.run()\n",
        )
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert [v for v in violations if v.file == "pkg/target.py"] == []

    def test_constructed_path_from_a_variable_is_not_a_resolved_import(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_refs.py::ref_gate
        # `Path(__file__).parent / (stem + ".py")` never spells
        # `sibling.py` literally ANYWHERE in the importer's text (the
        # stem comes from a variable, not a string literal) -- neither
        # the resolved-import channel nor the narrowed text channel can
        # see it. Must still fire REF001 (not a silent pass) -- this is
        # a genuine orphan from this substrate's own honest point of
        # view, exactly the shape a `frob:used-by` declaration exists to
        # cover explicitly. (A LITERAL `"sibling.py"` string, by
        # contrast, is still a real reference -- T-0396's own
        # full-basename-in-a-quoted-string rule, unaffected by T-1665;
        # this test is deliberately about the variable-built case that
        # rule was never meant to catch.)
        _init_repo(tmp_path)
        _write(tmp_path, "pkg/sibling.py", "def run(): pass\n")
        _write(
            tmp_path,
            "pkg/loader.py",
            "from pathlib import Path\n"
            'stem = "sib" + "ling"\n'
            'p = Path(__file__).parent / (stem + ".py")\n',
        )
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        rules = [v.rule for v in [v for v in violations if v.file == "pkg/sibling.py"]]
        assert "REF001" in rules
        severities = [
            v.severity
            for v in [v for v in violations if v.file == "pkg/sibling.py"]
            if v.rule == "REF001"
        ]
        assert severities == [Severity.ERROR]


# frob:ticket T-1665
class TestUnresolvedSeverity:
    """T-1664's third outcome: a `.py` target this substrate KNOWS it
    cannot determine reports `Severity.UNRESOLVED`, never a silent pass
    and never a false-certain REF001.

    frob:ticket T-2369
    """

    def test_dynamic_import_call_naming_the_target_reports_unresolved(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_refs.py::ref_gate
        _init_repo(tmp_path)
        _write(tmp_path, "plugins/greet.py", "def run(): pass\n")
        _write(
            tmp_path,
            "loader.py",
            'import importlib\nimportlib.import_module("plugins.greet")\n',
        )
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        matches = [v for v in violations if v.file == "plugins/greet.py"]
        assert len(matches) == 1
        assert matches[0].rule == "REF001"
        assert matches[0].severity == Severity.UNRESOLVED

    def test_unrelated_dynamic_import_does_not_launder_a_real_orphan(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_refs.py::ref_gate
        # A dynamic import call elsewhere in the repo that names a
        # DIFFERENT module must not blanket every zero-inbound `.py`
        # file as UNRESOLVED -- only a target the call's own text
        # plausibly names gets the benefit of the doubt.
        _init_repo(tmp_path)
        _write(tmp_path, "plugins/greet.py", "def run(): pass\n")
        _write(tmp_path, "plugins/truly_dead.py", "def unused(): pass\n")
        _write(
            tmp_path,
            "loader.py",
            'import importlib\nimportlib.import_module("plugins.greet")\n',
        )
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        dead = [
            v
            for v in [v for v in violations if v.file == "plugins/truly_dead.py"]
            if v.rule == "REF001"
        ]
        assert len(dead) == 1
        assert dead[0].severity == Severity.ERROR

    def test_resolved_import_wins_over_unresolved_when_both_exist(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_refs.py::ref_gate
        # A target with a REAL resolved import from one file, plus an
        # unrelated dynamic-import call elsewhere that also happens to
        # name it, is REFERENCED (inbound is non-empty, count 1 here) --
        # UNRESOLVED only ever applies when inbound is EMPTY, so this
        # reports the ordinary REF002 single-anchor tier, never
        # UNRESOLVED layered on top of a real, proven reference.
        _init_repo(tmp_path)
        _write(tmp_path, "plugins/greet.py", "def run(): pass\n")
        _write(tmp_path, "real_caller.py", "from plugins import greet\ngreet.run()\n")
        _write(
            tmp_path,
            "loader.py",
            'import importlib\nimportlib.import_module("plugins.greet")\n',
        )
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        matches = [v for v in violations if v.file == "plugins/greet.py"]
        assert [v.rule for v in matches] == ["REF002"]
        assert matches[0].severity == Severity.ERROR


# frob:ticket T-2928
class TestRef002FileGranularityMissesDeadSymbols:
    """T-2928: measured on a real controlled deletion (T-2900/T-2905, two
    provably dead private helpers), REF002 MISSED both -- it never fired
    at all against a symbol with zero real callers. Root cause,
    confirmed here rather than inferred: REF001/REF002 count inbound
    REFERENCES TO A FILE (`_ref001_or_002`'s own `inbound: set[str]` is a
    set of CONSUMER FILES, never symbols within a file) -- see this
    module's own docstring and `frob.gates._refs`'s module docstring
    ("anti-orphan gate over every git-tracked file"). A file with two or
    more real, independent consumers clears REF002's 2+ pass bar even
    when ONE particular symbol defined inside that file has zero
    callers anywhere -- the dead symbol is invisible to a check that
    only ever asks "is this FILE referenced", never "is this SYMBOL
    referenced". This is DEAD001's job (`frob.gates._dead_symbols`,
    symbol-granularity, WARN not ERROR) and is NOT fixable inside
    REF001/REF002 without turning them into a second, ERROR-severity
    symbol-level dead-code gate -- a distinct feature, not a bug fix,
    and out of this ticket's scope. Recorded here as a structural
    limitation, not silently left uncovered."""

    def test_dead_private_symbol_in_a_well_referenced_file_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_refs.py::ref_gate
        # Reconstructs the T-2900/T-2905 shape directly: a module with a
        # dead private helper (_parse_bash/_parse_csharp's own shape --
        # zero callers anywhere) living alongside a real, exported
        # symbol that TWO other files genuinely import -- confirms REF002
        # stays silent on the file as a whole (it has 2 real consumers)
        # and, separately, never produces any finding scoped to the dead
        # symbol itself (REF002 has no such granularity to report at).
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "pkg/walker.py",
            "def _dead_helper():\n"
            "    return 1\n\n"
            "\n"
            "def walk():\n"
            "    return 2\n",
        )
        _write(tmp_path, "caller_one.py", "from pkg import walker\nwalker.walk()\n")
        _write(tmp_path, "caller_two.py", "from pkg import walker\nwalker.walk()\n")
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        file_findings = [v for v in violations if v.file == "pkg/walker.py"]
        assert file_findings == [], (
            "REF002 must stay quiet -- pkg/walker.py genuinely has 2 real "
            "file-level consumers, exactly clearing its 2+ pass bar"
        )
        assert not any("_dead_helper" in v.message for v in violations), (
            "REF001/REF002 have no symbol-level granularity at all -- "
            "confirming the miss is structural, not a message that just "
            "failed to mention the symbol by name"
        )

    def test_file_containing_only_the_dead_symbol_still_fires_ref001(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_refs.py::ref_gate
        # Must-still-fire control: when the dead symbol IS effectively
        # the whole file's own content (no other symbol gives the file a
        # second life), REF001 fires exactly as designed -- proving
        # REF001/REF002 are not simply broken, only scoped to the FILE,
        # never the symbol, by design.
        _init_repo(tmp_path)
        _write(tmp_path, "pkg/only_dead.py", "def _dead_helper():\n    return 1\n")
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        dead = [v for v in violations if v.file == "pkg/only_dead.py"]
        assert len(dead) == 1
        assert dead[0].rule == "REF001"
        assert dead[0].severity == Severity.ERROR
