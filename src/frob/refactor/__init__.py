"""frob.refactor -- the reference-rewrite engine behind `frob refactor`
(docs/design/refactor-verb.md, T-1135; this package is T-1197's shared
substrate).

Owns the resolve/plan/apply/verify transaction pipeline and the Python
import/call-site reference kind. The directive/waiver carrier (T-1199),
registry/evidence repointer (T-1200), and prose/doc-anchor carrier
(T-1267) extend `RefactorPlan.reference_ops` with their own scan passes
against the same `build_plan`/`apply_plan`/`run_refactor` machinery -- they
do not reimplement transaction mechanics (docs/design/refactor-verb.md's
"Children filed" section).

Public surface: `run_refactor` for the one-call pipeline, `build_plan` for
a caller that wants to extend the plan before applying it, and the
pydantic models describing every intermediate shape.
"""
# frob:waive TEST003 reason="unit-tested exhaustively via tests/test_refactor.py's fixture-repo tests; no CLI/subprocess integration entrypoint exists yet -- frob refactor is not wired into frob.__main__'s subcommand tree (T-1197's declared scope excludes src/frob/_cli_parsers/** and src/frob/__main__.py, see docs/commands/refactor.md's CLI wiring status section); a real integration test belongs to the follow-up wiring ticket"  # noqa: E501

from __future__ import annotations

from frob.refactor._alias_policy import resolve_rename_dest_collision
from frob.refactor._apply import apply_plan
from frob.refactor._directives import (
    carry_lock_acks,
    extend_span_for_attached_directives,
    scan_directive_carriers,
)
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
from frob.refactor._prose import (
    scan_doc_anchor_carriers,
    scan_docs_prose_mentions,
    scan_python_prose_mentions,
)
from frob.refactor._repointer import (
    scan_evidence_citations,
    scan_pii_allowlist_carrier,
    scan_registry_citations,
)
from frob.refactor._resolve import module_to_path, resolve_symbol
from frob.refactor._scan import find_python_files, scan_references
from frob.refactor._split import (
    ChunkReport,
    SplitReport,
    build_reexport_shim_op,
    chunk_symbols,
    run_split,
)
from frob.refactor._transaction import build_plan, run_refactor
from frob.refactor._verify import (
    verify_check_delta,
    verify_import_resolution,
    verify_pytest_collect,
)

__all__ = [
    "AliasRecord",
    "ChunkReport",
    "RefactorError",
    "RefactorKind",
    "RefactorPlan",
    "RefactorReport",
    "ResolvedSymbol",
    "RewriteOp",
    "SplitReport",
    "SymbolRef",
    "VerifyOutcome",
    "apply_plan",
    "build_plan",
    "build_reexport_shim_op",
    "carry_lock_acks",
    "chunk_symbols",
    "extend_span_for_attached_directives",
    "find_python_files",
    "module_to_path",
    "resolve_rename_dest_collision",
    "resolve_symbol",
    "run_refactor",
    "run_split",
    "scan_directive_carriers",
    "scan_doc_anchor_carriers",
    "scan_docs_prose_mentions",
    "scan_evidence_citations",
    "scan_pii_allowlist_carrier",
    "scan_python_prose_mentions",
    "scan_references",
    "scan_registry_citations",
    "verify_check_delta",
    "verify_import_resolution",
    "verify_pytest_collect",
]
