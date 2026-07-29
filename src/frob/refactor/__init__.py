"""frob.refactor -- the reference-rewrite engine behind `frob refactor`
(docs/design/refactor-verb.md, T-1135; this package is T-1197's shared
substrate).

Owns the resolve/plan/apply/verify transaction pipeline and the Python
import/call-site reference kind. The directive/waiver carrier (T-1199),
registry/evidence repointer (T-1200), and prose/doc-anchor carrier
(T-1203) extend `RefactorPlan.reference_ops` with their own scan passes
against the same `build_plan`/`apply_plan`/`run_refactor` machinery -- they
do not reimplement transaction mechanics (docs/design/refactor-verb.md's
"Children filed" section).

Public surface: `run_refactor` for the one-call pipeline, `build_plan` for
a caller that wants to extend the plan before applying it, and the
pydantic models describing every intermediate shape.
"""
# frob:waive INV006 preset="split-carried-prose"
# frob:waive TEST003 reason="unit-tested exhaustively via tests/test_refactor.py's fixture-repo tests; no CLI/subprocess integration entrypoint exists yet -- frob refactor is not wired into frob.__main__'s subcommand tree (T-1197's declared scope excludes src/frob/_cli_parsers/** and src/frob/__main__.py, see docs/commands/refactor.md's CLI wiring status section); a real integration test belongs to the follow-up wiring ticket"  # noqa: E501

from __future__ import annotations

from frob.refactor._apply import apply_plan
from frob.refactor._models import (
    AliasRecord,
    RefactorError,
    RefactorKind,
    RefactorPlan,
    RefactorReport,
    ResolvedSymbol,
    RewriteOp,
    SymbolRef,
    VerifyOutcome,
)
from frob.refactor._resolve import module_to_path, resolve_symbol
from frob.refactor._scan import find_python_files, scan_references
from frob.refactor._transaction import build_plan, run_refactor
from frob.refactor._verify import (
    verify_check_delta,
    verify_import_resolution,
    verify_pytest_collect,
)

__all__ = [
    "AliasRecord",
    "RefactorError",
    "RefactorKind",
    "RefactorPlan",
    "RefactorReport",
    "ResolvedSymbol",
    "RewriteOp",
    "SymbolRef",
    "VerifyOutcome",
    "apply_plan",
    "build_plan",
    "find_python_files",
    "module_to_path",
    "resolve_symbol",
    "run_refactor",
    "scan_references",
    "verify_check_delta",
    "verify_import_resolution",
    "verify_pytest_collect",
]
