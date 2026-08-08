"""Data shapes for `frob.refactor`'s resolve/plan/apply/verify pipeline
(docs/design/refactor-verb.md, T-1135/T-1197).

Every model is a frozen pydantic `BaseModel`, matching `frob.graph._models`'
and `frob.dup._models`' posture: a `RefactorPlan`/`RefactorReport` must
compare and cache by identity-of-value, not identity-of-object, and must be
computed once (the Plan phase) and never silently re-derived mid-apply --
see the design doc's Transaction model section.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import ErrorSet

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
]


# frob:doc docs/commands/refactor.md#refactor-error
class RefactorError(ErrorSet):
    """Failure values the resolve/plan/apply/verify pipeline can return.

    Every value corresponds to a phase named in
    docs/design/refactor-verb.md's Transaction model section; a caller can
    branch on which phase refused without parsing prose.
    """

    DirtyWorkingTree = (
        "working tree has uncommitted changes; refusing to start a transaction"
    )
    NotAGitRepo = "repo_root is not inside a git working tree"
    TargetNotFound = "the move/rename target does not resolve to exactly one symbol"
    TargetAmbiguous = "the move/rename target resolves to more than one symbol"
    DestinationCollision = (
        "the destination module already defines a symbol with the destination name"
    )
    GitError = "a git operation the transaction depends on failed"
    ApplyFailed = "the apply phase could not complete every planned rewrite"
    OverlappingRewrites = (
        "two or more planned rewrites target overlapping or duplicate line "
        "ranges in the same file; applying either would silently clobber the "
        "other"
    )


# frob:doc docs/commands/refactor.md#refactor-kind
class RefactorKind(StrEnum):
    """The two v1 verbs this engine drives; `split` (T-1135 child 4) is a
    higher-level verb built on top of repeated `MOVE` transactions, not a
    third member here."""

    MOVE = "move"
    RENAME = "rename"


# frob:doc docs/commands/refactor.md#symbolref
class SymbolRef(BaseModel):
    """A fully-qualified Python symbol: its module's dotted import path
    plus its qualname within that module (`Class.method` for a nested
    symbol, a bare name for a top-level one)."""

    model_config = ConfigDict(frozen=True)

    module: str
    qualname: str

    # frob:doc docs/commands/refactor.md#symbolref
    @property
    def dotted(self) -> str:
        """The `module.qualname` form used in disclosed reports and
        `--delta` diffing."""
        return f"{self.module}.{self.qualname}"


# frob:doc docs/commands/refactor.md#resolvedsymbol
class ResolvedSymbol(BaseModel):
    """The Resolve phase's output: a `SymbolRef` pinned to a real file and
    an exact source span, so Plan/Apply never re-parse to relocate it."""

    model_config = ConfigDict(frozen=True)

    ref: SymbolRef
    file_path: str
    start_line: int
    end_line: int
    is_class: bool


# frob:doc docs/commands/refactor.md#rewriteop
class RewriteOp(BaseModel):
    """One exact text-span substitution the Apply phase performs verbatim.

    Spans are 1-indexed lines matching `ast`'s own `lineno`/`end_lineno`,
    so multiple ops against the same file can be applied in a single pass
    by sorting descending and splicing -- this is what lets Apply preserve
    formatting outside each touched span instead of reformatting the whole
    file (design doc's Apply phase requirement).
    """

    model_config = ConfigDict(frozen=True)

    file_path: str
    start_line: int
    end_line: int
    old_text: str
    new_text: str
    reason: str


# frob:doc docs/commands/refactor.md#aliasrecord
class AliasRecord(BaseModel):
    """One auto-generated import alias, named in the disclosed report per
    the epic's acceptance [1] so a human reviews every alias rather than
    discovering it later in a confusing diff."""

    model_config = ConfigDict(frozen=True)

    file_path: str
    original_name: str
    alias_name: str
    reason: str


# frob:doc docs/commands/refactor.md#refactorplan
class RefactorPlan(BaseModel):
    """The full rewrite plan, computed once before any file write (Plan
    phase). `move_ops` relocates the symbol's own source; `reference_ops`
    rewrites every import/call site; `aliases` records every auto-alias;
    `unresolved` names anything the plan could not resolve (never silently
    dropped)."""

    model_config = ConfigDict(frozen=True)

    kind: RefactorKind
    source: ResolvedSymbol
    destination: SymbolRef
    move_ops: tuple[RewriteOp, ...]
    reference_ops: tuple[RewriteOp, ...]
    aliases: tuple[AliasRecord, ...]
    unresolved: tuple[str, ...] = ()

    # frob:doc docs/commands/refactor.md#refactorplan
    # frob:tests tests/test_refactor.py::TestPlanProperties.test_plan_and_report_touched_files_dedupe  # noqa: E501
    @property
    def all_ops(self) -> tuple[RewriteOp, ...]:
        """Every rewrite op the Apply phase must perform, move ops first."""
        return self.move_ops + self.reference_ops

    # frob:doc docs/commands/refactor.md#refactorplan
    # frob:tests tests/test_refactor.py::TestPlanProperties.test_plan_and_report_touched_files_dedupe  # noqa: E501
    @property
    def touched_files(self) -> tuple[Path, ...]:
        """Every file path any op in this plan writes to, deduplicated --
        the Verify phase's own scoping input (import resolution check,
        `--full-repo-collect`'s narrower default)."""
        seen: dict[str, None] = {}
        for op in self.all_ops:
            seen.setdefault(op.file_path, None)
        return tuple(Path(p) for p in seen)


# frob:doc docs/commands/refactor.md#verifyoutcome
class VerifyOutcome(BaseModel):
    """One Verify-phase post-condition's result: a named check (import
    resolution / pytest collection / `frob check --delta`) plus whether it
    passed and the detail a disclosed report shows for it.

    T-1885: `skipped` names every touched path this check did NOT analyse
    because it is outside the check's own domain (e.g. a `tickets/<id>/
    ticket.md` evidence carrier or a `docs/design/registry/*.yaml` cross-
    ref handed to `verify_import_resolution`, which only ever verifies
    Python source) -- distinct from `passed=True`, which means "every
    file this check DID look at was fine." Before this field existed, a
    check that silently skipped an input it could not analyse and a check
    that genuinely analysed everything and found no problem were both
    reported as `passed=True` with no way to tell them apart from the
    outcome alone -- the exact conflation a companion incident (a stale
    mypy cache returning zero diagnostics for a file that had one; a
    capability scanner with no language table reporting "no capabilities
    observed") already burned this repo on, tracked at the check-gate
    layer by T-1664. `skipped` is additive and never affects `passed`
    itself -- it is a disclosure field, not a verdict."""

    model_config = ConfigDict(frozen=True)

    name: str
    passed: bool
    detail: str
    skipped: tuple[str, ...] = ()


# frob:doc docs/commands/refactor.md#refactorreport
class RefactorReport(BaseModel):
    """The disclosed report the design doc's Commit-or-rollback step
    requires: the plan, every verify outcome, and whether the transaction
    committed or rolled back -- printed the same shape either way."""

    model_config = ConfigDict(frozen=True)

    plan: RefactorPlan
    verify_outcomes: tuple[VerifyOutcome, ...]
    pre_sha: str
    commit_sha: str | None
    success: bool
    rolled_back: bool

    # frob:doc docs/commands/refactor.md#refactorreport
    # frob:tests tests/test_refactor.py::TestPlanProperties.test_plan_and_report_touched_files_dedupe  # noqa: E501
    @property
    def touched_files(self) -> tuple[Path, ...]:
        """Every file path any op in the plan wrote to, deduplicated,
        exposed for a caller (e.g. T-1199's directive pass) that wants to
        scope its own follow-up work to just what this transaction moved."""
        return self.plan.touched_files
