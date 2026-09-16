"""Mechanical proof (T-4415) that `.github/workflows/ci.yml`'s self-gate
job is the declared, unscoped, full-sweep source of truth for the repo,
and that a red self-gate on an unscoped rule files a ticket attributed to
the batch of commits since the last green run. Parses the REAL `ci.yml`
in this repo, not a fixture copy, matching
`tests/unit/test_release_workflow_gate.py`/`test_dev_branch_workflow.py`'s
own pattern -- a regression here means the live workflow drifted."""

from __future__ import annotations

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CI_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci.yml"

# PyYAML reads the workflow's `on:` key as the boolean True (YAML 1.1 alias).
_ON_KEY = True


def _load_ci() -> dict:
    """The real `ci.yml`, parsed -- fails loudly (not a skip) if the file
    is missing or unparseable, since that is itself the kind of drift
    this module exists to catch."""
    assert _CI_WORKFLOW.exists(), f"expected workflow file missing: {_CI_WORKFLOW}"
    with _CI_WORKFLOW.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    assert isinstance(doc, dict)
    return doc


def _find_step_by_name_prefix(job: dict, name_prefix: str) -> dict:
    """Return the first step in `job` whose `name` starts with
    `name_prefix`, raising loudly if none matches -- same lookup shape
    `test_release_workflow_gate.py`'s own helper uses (frob:doc DUP001)."""
    for step in job["steps"]:
        if step.get("name", "").startswith(name_prefix):
            return step
    raise AssertionError(f"no step named {name_prefix!r} found")


class TestSelfGateIsUnscoped:
    """AC1: the self-gate step runs the full, untruncated `frob check` --
    no `--ticket`/`--delta`/`--budget` flag narrows what it checks."""

    def test_self_gate_step_exists_and_is_named(self) -> None:
        """MUST-FIRE: the step is named so a reader can find it without
        already knowing which line runs `frob check`."""
        doc = _load_ci()
        step = _find_step_by_name_prefix(doc["jobs"]["build"], "frob check (self-gate)")
        assert step["run"], step

    def test_self_gate_step_passes_no_scoping_flags(self) -> None:
        """MUST-FIRE: none of the truncating flags land's own scoped
        check uses (T-4413) appear on this step's `frob check` line --
        a truncated self-gate would silently stop being the repo's
        full-sweep source of truth."""
        doc = _load_ci()
        step = _find_step_by_name_prefix(doc["jobs"]["build"], "frob check (self-gate)")
        run = step["run"]
        assert "frob check" in run
        for forbidden in ("--ticket", "--delta", "--budget"):
            assert forbidden not in run, (
                f"self-gate step's frob check line carries {forbidden!r} -- "
                f"this would truncate the declared unscoped full sweep"
            )

    def test_self_gate_failure_fails_the_step(self) -> None:
        """MUST-FIRE: `set -o pipefail` precedes the `tee` pipe, so a red
        `frob check` exit code (not `tee`'s always-0) is what the step
        reports -- a missing pipefail would let a red self-gate report
        green."""
        doc = _load_ci()
        step = _find_step_by_name_prefix(doc["jobs"]["build"], "frob check (self-gate)")
        run = step["run"]
        assert "set -o pipefail" in run
        assert "| tee" in run

    def test_self_gate_documented_as_unscoped_authority(self) -> None:
        """AC1's documentation half: the step (or the job/workflow
        comments immediately around it) states in plain text that it is
        the declared unscoped full-sweep authority, distinct from land's
        scoped check."""
        text = _CI_WORKFLOW.read_text(encoding="utf-8")
        assert "unscoped" in text.lower()
        assert "full-sweep" in text.lower() or "full sweep" in text.lower()


class TestSelfGateRegressionFiling:
    """AC2: a red self-gate on an unscoped rule files a ticket attributed
    to the batch of commits since the last green run, reusing the T-1690
    attribution engine's filing path."""

    def test_filing_step_exists(self) -> None:
        doc = _load_ci()
        step = _find_step_by_name_prefix(
            doc["jobs"]["build"], "File ticket for self-gate regression"
        )
        assert step["run"]

    def test_filing_step_runs_only_on_failure_of_a_single_leg(self) -> None:
        """One filed ticket per red batch, not one per matrix leg: gated
        to a single OS and to `failure()`, matching the T-3747 single-leg
        precedent already used elsewhere in this job for the analogous
        coverage step."""
        doc = _load_ci()
        step = _find_step_by_name_prefix(
            doc["jobs"]["build"], "File ticket for self-gate regression"
        )
        condition = step.get("if", "")
        assert "failure()" in condition
        assert "ubuntu-latest" in condition

    def test_filing_step_gated_to_push_events_only(self) -> None:
        """A fork PR's GITHUB_TOKEN cannot push regardless, but the step
        must not even attempt the batch-filing/push dance on a
        `pull_request` run."""
        doc = _load_ci()
        step = _find_step_by_name_prefix(
            doc["jobs"]["build"], "File ticket for self-gate regression"
        )
        assert "event_name == 'push'" in step.get("if", "")

    def test_filing_step_reuses_finding_filing_path_not_a_new_implementation(
        self,
    ) -> None:
        """Reuses `frob ticket new --finding RULE:FILE` (T-1690's own
        attribution-engine filing surface, T-2760's duplicate-pair
        refusal) rather than a second, parallel ticket-filing
        implementation living in the workflow file."""
        doc = _load_ci()
        step = _find_step_by_name_prefix(
            doc["jobs"]["build"], "File ticket for self-gate regression"
        )
        run = step["run"]
        assert "frob ticket new" in run
        assert "--finding" in run
        assert "--origin auditor" in run

    def test_filing_step_attributes_to_a_commit_range(self) -> None:
        """The filed ticket is attributed to a batch (a commit range
        since the last green run), not a bare "something is red" note --
        the step must compute a since/until pair."""
        doc = _load_ci()
        step = _find_step_by_name_prefix(
            doc["jobs"]["build"], "File ticket for self-gate regression"
        )
        run = step["run"]
        assert "SINCE_SHA" in run
        assert "HEAD_SHA" in run

    def test_workflow_declares_contents_write_for_the_filing_push(self) -> None:
        """`permissions: contents: write` at the workflow level is what
        lets the filing step push the ticket commit back to the branch;
        losing it would make every filing attempt fail silently at push
        time."""
        doc = _load_ci()
        assert doc.get("permissions", {}).get("contents") == "write"


def test_ci_runs_on_dev_and_main_still_holds() -> None:
    """Sanity companion to `test_dev_branch_workflow.py`'s own check --
    the self-gate (and its filing step) run on both branches the T-4415
    design decision covers."""
    doc = _load_ci()
    branches = doc[_ON_KEY]["push"]["branches"]
    assert set(branches) >= {"main", "dev"}, branches


class TestLandVsCiDocumentedSplit:
    """AC3: a developer reading docs/ finds an explicit statement that
    land proves the diff, CI proves the repo -- not merely implied by
    the workflow file's own comments."""

    _DOCS = (
        _REPO_ROOT / "docs" / "modules" / "tickets-landing.md",
        _REPO_ROOT / "docs" / "guides" / "release.md",
    )

    def test_both_doc_homes_state_the_split(self) -> None:
        """MUST-FIRE: both natural doc homes carry the exact phrase, so a
        reader arriving from either the landing docs or the release
        guide finds the same statement, not a phrase unique to one."""
        for path in self._DOCS:
            assert path.exists(), f"expected doc missing: {path}"
            text = path.read_text(encoding="utf-8").lower()
            assert "land proves the diff" in text, path
            assert "ci proves the repo" in text, path
