"""frob.mutate -- mutation testing, the honest test-quality oracle (T-0011).

Coverage and case-counts are gameable (an assert-free test passes them);
mutation testing is not. It perturbs a function's source with small
semantic mutations (flip a comparison, swap an operator, negate a boolean,
mutate a return), runs the tests bound to that function, and reports which
mutants SURVIVED -- a survivor is a behavior change no test noticed, i.e. a
real gap. The mutation score (killed / total) is the quality signal the
TEST gates' counts only approximate.

v1 mutates Python source via a small AST transformer and runs the
touched-set tests through frob.testing; other languages are recorded work.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger

_log = get_logger(__name__)

# (from-op, to-op) mutations, applied one at a time.
_COMPARE_SWAPS: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.Lt: ast.GtE,
    ast.Gt: ast.LtE,
    ast.LtE: ast.Gt,
    ast.GtE: ast.Lt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
}
_BINOP_SWAPS: dict[type[ast.operator], type[ast.operator]] = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.FloorDiv,
    ast.Div: ast.Mult,
}
_BOOLOP_SWAPS: dict[type[ast.boolop], type[ast.boolop]] = {
    ast.And: ast.Or,
    ast.Or: ast.And,
}


class MutateError(ErrorSet):
    """Fallible outcomes of mutation testing."""

    ParseFailed = "Source file could not be parsed"
    NoSource = "Target file does not exist"


class Mutant(BaseModel):
    """One applied mutation: what changed and where."""

    model_config = ConfigDict(frozen=True)

    file: str
    line: int
    description: str


class MutationResult(BaseModel):
    """The outcome of testing one function's mutants."""

    model_config = ConfigDict(frozen=True)

    total: int
    killed: int
    survivors: tuple[Mutant, ...]

    @property
    def score(self) -> float:
        """Killed / total (1.0 = every mutant caught; NaN-safe as 1.0)."""
        return 1.0 if self.total == 0 else self.killed / self.total


@dataclass
class _Mutation:
    """An in-flight mutation: the transformed source and its description."""

    source: str
    mutant: Mutant


class _Mutator(ast.NodeTransformer):
    """Applies exactly ONE mutation, identified by a running counter."""

    def __init__(self, target_index: int) -> None:
        self._target = target_index
        self._seen = 0
        self.applied: str | None = None

    def _hit(self, desc: str) -> bool:
        current = self._seen
        self._seen += 1
        if current == self._target:
            self.applied = desc
            return True
        return False

    def visit_Compare(self, node: ast.Compare):  # noqa: N802
        self.generic_visit(node)
        if len(node.ops) == 1 and type(node.ops[0]) in _COMPARE_SWAPS:
            if self._hit(f"compare {type(node.ops[0]).__name__} swapped"):
                node.ops = [_COMPARE_SWAPS[type(node.ops[0])]()]
        return node

    def visit_BinOp(self, node: ast.BinOp):  # noqa: N802
        self.generic_visit(node)
        if type(node.op) in _BINOP_SWAPS and self._hit(
            f"binop {type(node.op).__name__} swapped"
        ):
            node.op = _BINOP_SWAPS[type(node.op)]()
        return node

    def visit_BoolOp(self, node: ast.BoolOp):  # noqa: N802
        self.generic_visit(node)
        if type(node.op) in _BOOLOP_SWAPS and self._hit(
            f"boolop {type(node.op).__name__} swapped"
        ):
            node.op = _BOOLOP_SWAPS[type(node.op)]()
        return node

    def visit_Constant(self, node: ast.Constant):  # noqa: N802
        if isinstance(node.value, bool) and self._hit(f"bool {node.value} negated"):
            return ast.copy_location(ast.Constant(value=not node.value), node)
        return node


def _count_mutations(tree: ast.AST) -> int:
    """How many single-point mutations the source admits."""
    counter = _Mutator(-1)  # never hits; just counts via _seen
    counter.visit(tree)
    return counter._seen


def generate_mutants(
    source: str, file: str
) -> Result[tuple[_Mutation, ...], MutateError]:
    """Every single-point mutation of `source` as (mutated_source, Mutant)."""
    try:
        base = ast.parse(source)
    except SyntaxError:
        return Err(MutateError.ParseFailed)
    total = _count_mutations(base)
    mutations: list[_Mutation] = []
    for i in range(total):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return Err(MutateError.ParseFailed)
        mutator = _Mutator(i)
        mutator.visit(tree)
        applied = mutator.applied
        if applied is None:
            continue
        ast.fix_missing_locations(tree)
        line = 0
        for node in ast.walk(tree):
            node_line = getattr(node, "lineno", None)
            if isinstance(node_line, int):
                line = node_line
                break
        mutations.append(
            _Mutation(
                source=ast.unparse(tree),
                mutant=Mutant(file=file, line=line, description=str(applied)),
            )
        )
    return Ok(tuple(mutations))


def run_mutations(
    root: Path, file: Path, test_argv: tuple[str, ...], timeout_s: float = 300.0
) -> Result[MutationResult, MutateError]:
    """Mutate `file` one point at a time; a mutant is KILLED if `test_argv`
    fails against it, SURVIVED if the tests still pass.

    The file is restored after every mutant (and on any error), so a crashed
    run never leaves a mutated source behind.
    """
    import subprocess

    target = root / file if not file.is_absolute() else file
    if not target.exists():
        return Err(MutateError.NoSource)
    original = target.read_text(encoding="utf-8")
    generated = generate_mutants(original, str(file))
    if generated.is_err:
        return Err(generated.danger_err)
    mutants = generated.danger_ok
    killed = 0
    survivors: list[Mutant] = []
    try:
        for mutation in mutants:
            target.write_text(mutation.source, encoding="utf-8")
            try:
                proc = subprocess.run(
                    list(test_argv),
                    cwd=root,
                    capture_output=True,
                    timeout=timeout_s,
                )
            except subprocess.TimeoutExpired:
                killed += 1  # a mutant that hangs the tests is caught
                continue
            if proc.returncode != 0:
                killed += 1
            else:
                _log.info("mutate: SURVIVOR %s", mutation.mutant.description)
                survivors.append(mutation.mutant)
    finally:
        target.write_text(original, encoding="utf-8")
    _log.info(
        "mutate: %d mutant(s), %d killed, %d survived",
        len(mutants),
        killed,
        len(survivors),
    )
    return Ok(
        MutationResult(total=len(mutants), killed=killed, survivors=tuple(survivors))
    )


__all__ = [
    "Mutant",
    "MutateError",
    "MutationResult",
    "generate_mutants",
    "run_mutations",
]
