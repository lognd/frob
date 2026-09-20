"""T-4676 (SF-23): COV002 over `.strata` declarations, verified against
the archived T-0164 fix ("COV002 demands per-declaration frob:ticket
edges inside .strata files -- boilerplate").

T-0164 (done) already settled this: a `frob:ticket` directive on the
owning `module` covers every nested declaration, so COV002 does not
demand a boilerplate per-declaration edge. This file's job is a standing
regression for that decision at whatever scale a real design file
reaches (several declarations, not just one), not a re-litigation of
it -- per memory/verify-premise-before-filing.md, the premise ("COV002
still demands per-declaration edges") was re-checked against HEAD before
writing this: `tests/gates_suite/test_coverage.py::
TestCov002StrataModuleCoverage` already covers exactly this and passes,
so no change to `_tickets_gate.py` was needed or made.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.gates import GateConfig, run_gates
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)


def _init_repo(tmp_path: Path) -> None:
    """Shared git scaffolding for a throwaway `.strata` fixture repo."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)


def _write(tmp_path: Path, rel: str, text: str) -> None:
    """Write `text` to `rel` under `tmp_path`, creating parent dirs."""
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class TestCov002StrataDeclarationsStandingRegression:
    """Positive control (acceptance [1]): several `.strata` declarations,
    one module-level `frob:ticket` edge, no per-declaration edges ->
    zero COV002 findings, at a scale (node + flow + assert) closer to a
    real design file than T-0164's own single-node regression test."""

    # frob:tests \
    # tests/unit/gates/test_cov002_strata_declarations.py::TestCov002StrataDeclarationsStandingRegression.test_module_edge_covers_several_declarations_no_per_decl_edges  # noqa: E501
    def test_module_edge_covers_several_declarations_no_per_decl_edges(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        base = (
            "// frob:ticket T-9001\n"
            "module m\n"
            "node client : foreign { clearance Public; }\n"
            "node api : trusted { clearance Internal; }\n"
            "flow f1 client -> api;\n"
        )
        _write(tmp_path, "design/m.strata", base)
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=tmp_path, check=True)

        t = new_ticket(
            tmp_path,
            TicketSpec(
                title="strata module coverage at scale",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
            ),
        ).danger_ok
        # Rewrite T-9001 to the real ticket id, and change THREE nested
        # declarations (both nodes' clearance, the flow's id) -- no edge
        # anywhere but the one module-level directive.
        changed = (
            base.replace("T-9001", t.id)
            .replace(
                "node client : foreign { clearance Public; }",
                "node client : foreign { clearance Internal; }",
            )
            .replace(
                "node api : trusted { clearance Internal; }",
                "node api : trusted { clearance Public; }",
            )
            .replace("flow f1 client -> api;", "flow f1_renamed client -> api;")
        )
        _write(tmp_path, "design/m.strata", changed)
        transition(tmp_path, t.id, TicketState.PLANNED)
        transition(tmp_path, t.id, TicketState.IN_PROGRESS)

        report = run_gates(
            GateConfig(root=str(tmp_path), base="main", gates=frozenset({"coverage"}))
        ).danger_ok
        assert not [v for v in report.violations if v.rule == "COV002"]


class TestCov002StrataDeclarationsStillFiresWithNoEdgeAtAll:
    """Negative control, mirroring T-0164's own: the escape hatch is a
    module-level edge, not a blanket `.strata` exemption -- a file with
    NO `frob:ticket` anywhere still fires COV002 on a changed
    declaration."""

    # frob:tests \
    # tests/unit/gates/test_cov002_strata_declarations.py::TestCov002StrataDeclarationsStillFiresWithNoEdgeAtAll.test_no_ticket_edge_anywhere_still_fires  # noqa: E501
    def test_no_ticket_edge_anywhere_still_fires(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "design/m.strata",
            "module m\nnode client : foreign { clearance Public; }\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=tmp_path, check=True)
        _write(
            tmp_path,
            "design/m.strata",
            "module m\nnode client : foreign { clearance Internal; }\n",
        )

        report = run_gates(
            GateConfig(root=str(tmp_path), base="main", gates=frozenset({"coverage"}))
        ).danger_ok
        assert any(v.rule == "COV002" for v in report.violations)
