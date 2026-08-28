"""DOCARCH001 (T-2988) fixtures: must-fire and must-stay-quiet, mirroring
`frob.gates._waive`'s WAIVE009/010 provenance-vs-deferred-work shape
applied to docstrings instead of `frob:waive` reasons -- a bare ticket
citation is legitimate provenance and must stay quiet; only citation PLUS
change-narrative wording is the archaeology shape T-2988 measured.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates import GateConfig, run_gates
from frob.gates._docstring_archaeology import (
    _doc_cites_ticket,
    _doc_reads_as_narrative,
    _is_archaeology,
    docarch001_violations,
)


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _git_init(root: Path) -> None:
    """Minimal git init so `run_gates`'s diff/scope machinery has a base
    to work against -- matching `tests/test_waive_gate.py`'s `_git_init`."""
    import subprocess

    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "base", "--allow-empty"], cwd=root, check=True
    )


class TestDocarch001Violations:
    """`docarch001_violations` -- the assembled repo-scan entrypoint."""

    def test_ticket_plus_narrative_wording_warns(self, tmp_path: Path) -> None:
        """MUST-FIRE: a public function's docstring cites a ticket AND
        narrates a change -- the T-2988 worked example's own shape."""
        _write(
            tmp_path,
            "src/a.py",
            (
                "def walk(node):\n"
                '    """Walk the AST and return field projections.\n\n'
                "    This used to walk the raw AST directly until T-0632 "
                "folded the projection into a shared field; T-0370's "
                "prior attempt kept it on the raw AST instead.\n"
                '    """\n'
                "    return node\n"
            ),
        )
        violations = docarch001_violations(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "DOCARCH001"
        from frob.gates._models import Severity

        assert violations[0].severity == Severity.WARN
        assert violations[0].symref == "src/a.py::walk"

    def test_bare_ticket_reference_stays_quiet(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET: a bare ticket reference for provenance, no
        change-narrative wording -- the legitimate 'see T-#### for the
        design rationale' shape a docstring is explicitly allowed to
        carry."""
        _write(
            tmp_path,
            "src/a.py",
            (
                "def walk(node):\n"
                '    """Walk the AST and return field projections; see '
                'T-0632 for the design rationale."""\n'
                "    return node\n"
            ),
        )
        assert docarch001_violations(tmp_path) == ()

    def test_long_utility_docstring_stays_quiet(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET: a genuinely long docstring that is entirely
        utility prose (explains behavior, contract, edge cases) with no
        ticket citation at all -- length alone is never the signal."""
        _write(
            tmp_path,
            "src/a.py",
            (
                "def walk(node):\n"
                '    """Walk the AST and return field projections.\n\n'
                "    Returns a tuple of (rel, func_name, param_types, "
                "return_type, body_fingerprint) for every function "
                "definition reachable from `node`, in source order. "
                "Nested functions are included with a dotted qualname; "
                "decorated functions are unwrapped to the underlying "
                "def before extraction so a decorator never changes the "
                "reported signature. Raises nothing -- a malformed node "
                "yields an empty tuple rather than an exception, since "
                "callers already treat 'no functions found' as a normal "
                'outcome for a non-code file."""\n'
                "    return node\n"
            ),
        )
        assert docarch001_violations(tmp_path) == ()

    def test_narrative_wording_without_ticket_stays_quiet(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET: narrative-shaped wording with no ticket cited
        at all -- ordinary prose describing present behavior can
        legitimately use a word like 'replaced' with nothing to flag."""
        _write(
            tmp_path,
            "src/a.py",
            (
                "def walk(node):\n"
                '    """Walk the AST; a missing node is replaced by an '
                'empty placeholder before recursion continues."""\n'
                "    return node\n"
            ),
        )
        assert docarch001_violations(tmp_path) == ()

    def test_private_symbol_exempt_even_with_archaeology(self, tmp_path: Path) -> None:
        """Private (leading-underscore) symbols are exempt outright --
        tier 3's bar is deliberately lower."""
        _write(
            tmp_path,
            "src/a.py",
            (
                "def _walk(node):\n"
                '    """This used to walk the raw AST until T-0632 '
                'folded the projection in."""\n'
                "    return node\n"
            ),
        )
        assert docarch001_violations(tmp_path) == ()

    def test_no_docstring_stays_quiet(self, tmp_path: Path) -> None:
        """A symbol with no docstring at all is not a DOCARCH001 finding
        -- absence is this standard's own valid, intentional state."""
        _write(tmp_path, "src/a.py", "def walk(node):\n    return node\n")
        assert docarch001_violations(tmp_path) == ()


class TestDocReadsAsNarrative:
    """`_doc_reads_as_narrative`/`_doc_cites_ticket` -- the pure wording
    predicates `_is_archaeology` combines."""

    def test_used_to_matches(self) -> None:
        assert _doc_reads_as_narrative("this used to return a list")

    def test_superseded_matches(self) -> None:
        assert _doc_reads_as_narrative("the old approach was superseded")

    def test_plain_utility_does_not_match(self) -> None:
        assert not _doc_reads_as_narrative("returns the parsed field list")

    def test_cites_ticket_matches_plain_id(self) -> None:
        assert _doc_cites_ticket("see T-0632 for context")

    def test_cites_ticket_matches_draft_id(self) -> None:
        assert _doc_cites_ticket("see T-draft-abc123 for context")

    def test_cites_ticket_false_without_id(self) -> None:
        assert not _doc_cites_ticket("no ticket mentioned here")

    def test_is_archaeology_requires_both(self) -> None:
        assert _is_archaeology("T-0632: this used to walk the raw AST")
        assert not _is_archaeology("T-0632: this walks the AST")
        assert not _is_archaeology("this used to walk the raw AST")


class TestDocarch001Wiring:
    """T-2988 acceptance criterion (T-0756 new-gate-rule proof): DOCARCH001
    must fire through a real `run_gates` pass, not just via a direct call
    to `docarch001_violations` -- proves the rule is actually wired into
    `frob check`'s production invocation, mirroring
    `tests/test_waive_gate.py::TestWaive009Wiring`'s own end-to-end shape."""

    def test_fires_through_run_gates(self, tmp_path: Path) -> None:
        """BEFORE this ticket, DOCARCH001 did not exist; AFTER, a public
        docstring reading as ticket archaeology must surface as a
        DOCARCH001 warning through a real `frob check` (`run_gates`)
        pass."""
        _write(
            tmp_path,
            "src/a.py",
            (
                "def walk(node):\n"
                '    """Walk the AST.\n\n'
                "    This used to walk the raw AST directly until T-0632 "
                "folded the projection into a shared field.\n"
                '    """\n'
                "    return node\n"
            ),
        )
        _git_init(tmp_path)
        report = run_gates(GateConfig(root=str(tmp_path))).danger_ok
        assert any(v.rule == "DOCARCH001" for v in report.violations), (
            "DOCARCH001 did not fire through run_gates -- wiring regression"
        )

    def test_utility_only_does_not_fire_through_run_gates(self, tmp_path: Path) -> None:
        """A public docstring with no ticket-archaeology shape must stay
        quiet through the same real `run_gates` pass."""
        _write(
            tmp_path,
            "src/a.py",
            (
                "def walk(node):\n"
                '    """Walk the AST and return field projections."""\n'
                "    return node\n"
            ),
        )
        _git_init(tmp_path)
        report = run_gates(GateConfig(root=str(tmp_path))).danger_ok
        assert not any(v.rule == "DOCARCH001" for v in report.violations)
