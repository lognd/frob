"""T-3104: end-to-end demonstration that an environment-absence bug (the
class T-3075's own five tests hit -- a defect whose trigger is something
MISSING from the environment, which this repo's own verification sandbox
always HAS) can genuinely reproduce at the parent commit through BUG002's
own tooling, via the `frob:env-absent VAR,...` directive.

Deliberately its own file, importing only `frob.gates.bug_repro_outcome_at_ref`
(the PUBLIC entrypoint, already present before this ticket's change) rather
than the new private helpers `tests/test_gates_mutation_evidence.py` also
covers -- at the parent commit `env_absent` is not yet a parameter that
function accepts at all, so passing it raises `TypeError` from INSIDE the
test body (a clean pytest failure, exit 1), not a module-level import
error that would make BUG002's designated-repro checkout fail to collect
ANY test in the file (which `TEST_ABSENT_AT_PARENT`/`NO_VERDICT` would
misreport as "cannot verify" rather than the genuine "yes, this fails at
the parent" this ticket needs to prove)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.gates import bug_repro_outcome_at_ref
from tests.test_tickets_mutation_evidence import _commit, _git, _init_repo  # noqa: F401


class TestEnvAbsentBug002Repro:
    """`bug_repro_outcome_at_ref`'s `env_absent` kwarg (T-3104), exercised
    end to end against a real environment-absence defect."""

    def test_env_absent_kwarg_reproduces_identity_absence_defect_at_parent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/gates/test_env_absent_bug002_repro.py::TestEnvAbsentBug002Repro.test_env_absent_kwarg_reproduces_identity_absence_defect_at_parent kind="integration"  # noqa: E501
        # T-3075's own shape, reconstructed: `do_the_thing` reads
        # FROB_T3104_MARK directly with no fallback. This sandbox (and
        # this test process) always has the variable SET, standing in for
        # a developer machine's ambient git identity -- an ordinary repro
        # subprocess inherits that unconditionally and can never observe
        # the genuinely-absent case a real bare-CI/no-identity environment
        # would hit.
        monkeypatch.setenv("FROB_T3104_MARK", "present-in-this-sandbox")

        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "src").mkdir()
        (repo / "src" / "thing.py").write_text(
            "import os\n\n"
            "def do_the_thing() -> str:\n"
            "    return os.environ['FROB_T3104_MARK']\n",
            encoding="utf-8",
        )
        (repo / "tests").mkdir()
        (repo / "tests" / "test_thing.py").write_text(
            "import sys\n"
            "sys.path.insert(0, 'src')\n"
            "import thing\n\n"
            "def test_works_without_the_var():\n"
            "    thing.do_the_thing()  # must not raise, var or no var\n",
            encoding="utf-8",
        )
        _commit(repo, "parent: no fallback, crashes when FROB_T3104_MARK is unset")
        parent = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        # fix: fall back to a default when the var is genuinely absent --
        # a separate commit so `parent` and `HEAD` differ (T-1678:
        # base_ref resolving to HEAD itself is a vacuous, SAME_AS_HEAD
        # comparison, not a real pre-fix reproduction).
        (repo / "src" / "thing.py").write_text(
            "import os\n\n"
            "def do_the_thing() -> str:\n"
            "    return os.environ.get('FROB_T3104_MARK', 'fallback')\n",
            encoding="utf-8",
        )
        _commit(repo, "fix: fall back to a default when the var is absent")

        # BEFORE this ticket's fix, `bug_repro_outcome_at_ref` accepts no
        # `env_absent` parameter at all -- this call raises `TypeError`
        # here, a genuine, clean test failure at the parent commit. AFTER
        # the fix, the kwarg strips FROB_T3104_MARK from the parent-commit
        # subprocess's environment before it runs, so the repro genuinely
        # observes the defect and returns FAILED_AT_PARENT.
        from frob.gates._bug_repro import _BugReproOutcome  # noqa: PLC0415

        outcome = bug_repro_outcome_at_ref(
            repo,
            "tests/test_thing.py::test_works_without_the_var",
            parent,
            env_absent=("FROB_T3104_MARK",),
        )
        assert outcome is _BugReproOutcome.FAILED_AT_PARENT
