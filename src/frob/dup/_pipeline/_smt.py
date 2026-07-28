"""R7 bounded-SMT equivalence probing via z3 (split from `dup/_pipeline.py`, T-1086).

Translates a narrow, explicitly-bounded subset of straight-line Python
(int/bool-annotated, single-`return`, `+ - * // %`, comparisons, `and/or/not`,
one `if`-expression) to Z3 expressions and checks satisfiability of the
"differ" predicate -- see docs/modules/dup.md's "R7" deviation note (now on
`frob.dup._pipeline`'s `__init__.py`). Opt-in, never called from
`find_clones`/the DUP gate path; degrades to `Err(SmtUnavailable)` without
the optional `z3-solver` dependency.
"""

from __future__ import annotations

import inspect
import textwrap
from pathlib import Path
from typing import Any

from typani import Err, Ok
from typani.result import Result

from frob.dup._models import DupError, ProbeVerdict
from frob.dup._pipeline._probe import _load_python_callable
from frob.dup._pipeline._shared import _log
from frob.graph._models import GraphSnapshot

# R7 (opt-in, bounded-SMT): the AST node types `_smt_translate` accepts.
# Deliberately tiny -- straight-line int/bool arithmetic and comparisons
# only, no loops/calls/attribute access. Anything outside this subset is
# Err(SmtUnsupported), never a silent "probably fine."
_SMT_BINOPS = {"Add", "Sub", "Mult", "FloorDiv", "Mod"}
_SMT_CMPOPS = {"Eq", "NotEq", "Lt", "LtE", "Gt", "GtE"}
_SMT_BOOLOPS = {"And", "Or"}


def _smt_translate(node: Any, z3: Any, env: dict[str, Any]) -> Any:
    """Recursively translate a bounded Python-`ast` expression subtree into
    a Z3 expression over `env` (name -> Z3 const). Raises `ValueError` for
    anything outside `_SMT_BINOPS`/`_SMT_CMPOPS`/`_SMT_BOOLOPS`/literals/
    names/`if`-expressions/`not`/unary-minus -- the caller converts that
    into `Err(SmtUnsupported)`, never silently drops the term.
    """
    import ast as _ast

    if isinstance(node, _ast.IfExp):
        # frob:invariant terminates reason="node.test/body/orelse are node's own AST fields, each a proper descendant node in the finite Python ast tree produced by ast.parse; _smt_translate_simple and its helpers (_smt_unaryop/_smt_binop/_smt_boolop/_smt_compare) mutually recurse the same way, only ever descending into a field of their argument" measure="node's ast subtree depth strictly decreases"  # noqa: E501
        return z3.If(
            _smt_translate(node.test, z3, env),
            _smt_translate(node.body, z3, env),
            _smt_translate(node.orelse, z3, env),
        )
    handled = _smt_translate_simple(node, z3, env)
    if handled is not _SMT_UNHANDLED:
        return handled
    raise ValueError(f"unsupported node {type(node).__name__}")


_SMT_UNHANDLED = object()


def _smt_translate_simple(node: Any, z3: Any, env: dict[str, Any]) -> Any:
    """The non-`IfExp` cases of `_smt_translate`: literals, names, unary/binary/bool
    ops, and comparisons. Returns the `_SMT_UNHANDLED` sentinel for anything else."""
    import ast as _ast

    if isinstance(node, _ast.Constant) and isinstance(node.value, bool):
        return z3.BoolVal(node.value)
    if isinstance(node, _ast.Constant) and isinstance(node.value, int):
        return z3.IntVal(node.value)
    if isinstance(node, _ast.Name):
        if node.id not in env:
            raise ValueError(f"unbound name {node.id!r}")
        return env[node.id]
    if isinstance(node, _ast.UnaryOp):
        return _smt_unaryop(node, z3, env)
    if isinstance(node, _ast.BinOp):
        return _smt_binop(node, z3, env)
    if isinstance(node, _ast.BoolOp):
        return _smt_boolop(node, z3, env)
    if (
        isinstance(node, _ast.Compare)
        and len(node.ops) == 1
        and len(node.comparators) == 1
    ):
        return _smt_compare(node, z3, env)
    return _SMT_UNHANDLED


def _smt_unaryop(node: Any, z3: Any, env: dict[str, Any]) -> Any:
    """Translate a unary `-`/`not` expression to Z3."""
    import ast as _ast

    operand = _smt_translate(node.operand, z3, env)
    if isinstance(node.op, _ast.USub):
        return -operand
    if isinstance(node.op, _ast.Not):
        return z3.Not(operand)
    raise ValueError(f"unsupported unary op {type(node.op).__name__}")


def _smt_binop(node: Any, z3: Any, env: dict[str, Any]) -> Any:
    """Translate a bounded arithmetic binary op (`+ - * // %`) to Z3."""
    op_name = type(node.op).__name__
    if op_name not in _SMT_BINOPS:
        raise ValueError(f"unsupported binop {op_name}")
    left = _smt_translate(node.left, z3, env)
    right = _smt_translate(node.right, z3, env)
    return {
        "Add": lambda: left + right,
        "Sub": lambda: left - right,
        "Mult": lambda: left * right,
        "FloorDiv": lambda: left / right,
        "Mod": lambda: left % right,
    }[op_name]()


def _smt_boolop(node: Any, z3: Any, env: dict[str, Any]) -> Any:
    """Translate an `and`/`or` expression to Z3."""
    op_name = type(node.op).__name__
    if op_name not in _SMT_BOOLOPS:
        raise ValueError(f"unsupported boolop {op_name}")
    values = [_smt_translate(v, z3, env) for v in node.values]
    return z3.And(*values) if op_name == "And" else z3.Or(*values)


def _smt_compare(node: Any, z3: Any, env: dict[str, Any]) -> Any:
    """Translate a single-operator comparison to Z3."""
    op_name = type(node.ops[0]).__name__
    if op_name not in _SMT_CMPOPS:
        raise ValueError(f"unsupported compare op {op_name}")
    left = _smt_translate(node.left, z3, env)
    right = _smt_translate(node.comparators[0], z3, env)
    return {
        "Eq": lambda: left == right,
        "NotEq": lambda: left != right,
        "Lt": lambda: left < right,
        "LtE": lambda: left <= right,
        "Gt": lambda: left > right,
        "GtE": lambda: left >= right,
    }[op_name]()


def _smt_function_expr(source: str, z3: Any) -> tuple[Any, list[Any]] | None:
    """Parse `source` (one `def f(...): return <expr>` function) into a Z3
    expression plus its ordered parameter consts, or `None` if it is not a
    single-return, int/bool-annotated, bounded-subset function."""
    import ast as _ast

    tree = _ast.parse(source)
    if len(tree.body) != 1 or not isinstance(tree.body[0], _ast.FunctionDef):
        return None
    fn = tree.body[0]
    if len(fn.body) != 1 or not isinstance(fn.body[0], _ast.Return):
        return None
    if fn.body[0].value is None:
        return None

    bound = _smt_bind_params(fn.args.args, z3)
    if bound is None:
        return None
    env, params = bound

    try:
        expr = _smt_translate(fn.body[0].value, z3, env)
    except ValueError as exc:
        _log.debug("_probe_smt_equivalence: unsupported subset (%s)", exc)
        return None
    return expr, params


def _smt_bind_params(
    args: list[Any], z3: Any
) -> tuple[dict[str, Any], list[Any]] | None:
    """Z3 int/bool consts for each `int`/`bool`-annotated argument, `None` if
    any argument's annotation is outside that bounded subset."""
    env: dict[str, Any] = {}
    params: list[Any] = []
    for arg in args:
        ann = getattr(arg.annotation, "id", None)
        if ann == "int":
            const = z3.Int(arg.arg)
        elif ann == "bool":
            const = z3.Bool(arg.arg)
        else:
            return None
        env[arg.arg] = const
        params.append(const)
    return env, params


# frob:doc docs/modules/dup.md#rung-r7
# frob:waive COV007 reason="docs/modules/dup.md's Rung R7 section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
def _probe_smt_equivalence(
    a: str, b: str, snapshot: GraphSnapshot
) -> Result[ProbeVerdict, DupError]:
    """R7 (opt-in, research-frontier per docs/modules/dup.md): bounded-SMT formal
    equivalence for tiny pure int/bool functions, via z3-solver.

    Degrades to `Err(SmtUnavailable)` when `z3-solver` is not installed
    (an optional dependency -- `uv pip install frob[smt]`), and to
    `Err(SmtUnsupported)` for anything outside the bounded subset
    `_smt_translate` accepts (straight-line int/bool arithmetic,
    comparisons, `and`/`or`/`not`, one `if`-expression return -- no loops,
    calls, or attribute access). Unlike R6's observational probing, an
    UNSAT result here is a formal proof of equivalence over the whole
    input domain, not evidence from sampled cases.
    """
    try:
        import z3  # ty: ignore[unresolved-import]  # optional dep, frob[smt]
    except ImportError:
        _log.warning("_probe_smt_equivalence: z3-solver not installed")
        return Err(DupError.SmtUnavailable)

    parsed = _smt_parse_pair(a, b, snapshot, z3)
    if parsed.is_err:
        return Err(parsed.danger_err)
    (expr_a, params_a), (expr_b, params_b) = parsed.danger_ok
    return _smt_solve(a, b, expr_a, params_a, expr_b, params_b, z3)


def _smt_parse_pair(
    a: str, b: str, snapshot: GraphSnapshot, z3: Any
) -> Result[tuple[tuple[Any, list[Any]], tuple[Any, list[Any]]], DupError]:
    """Load `a`/`b`, parse each into a bounded Z3 expression + param consts.

    `Err(NotPure)` if either symbol is missing; `Err(SmtUnsupported)` if
    either is unloadable, unreadable, outside the bounded subset, or the two
    differ in arity.
    """
    root = Path(snapshot.root)
    a_rec = snapshot.symbols.get(a)
    b_rec = snapshot.symbols.get(b)
    if a_rec is None or b_rec is None:
        return Err(DupError.NotPure)

    fn_a = _load_python_callable(root, a_rec.id.path, a_rec.id.qualname)
    fn_b = _load_python_callable(root, b_rec.id.path, b_rec.id.qualname)
    if fn_a is None or fn_b is None:
        return Err(DupError.SmtUnsupported)

    sources = _smt_dedented_sources(fn_a, fn_b)
    if sources is None:
        return Err(DupError.SmtUnsupported)
    src_a, src_b = sources

    parsed_a = _smt_function_expr(src_a, z3)
    parsed_b = _smt_function_expr(src_b, z3)
    if parsed_a is None or parsed_b is None:
        return Err(DupError.SmtUnsupported)
    if len(parsed_a[1]) != len(parsed_b[1]):
        return Err(DupError.SmtUnsupported)
    return Ok((parsed_a, parsed_b))


def _smt_dedented_sources(fn_a: Any, fn_b: Any) -> tuple[str, str] | None:
    """Dedented `inspect.getsource` for both callables, or `None` if either
    is unreadable (builtin, C extension, source file gone, ...)."""

    try:
        return (
            textwrap.dedent(inspect.getsource(fn_a)),
            textwrap.dedent(inspect.getsource(fn_b)),
        )
    except (OSError, TypeError):
        return None


def _smt_solve(
    a: str,
    b: str,
    expr_a: Any,
    params_a: list[Any],
    expr_b: Any,
    params_b: list[Any],
    z3: Any,
) -> Result[ProbeVerdict, DupError]:
    """Check `expr_a != expr_b` for satisfiability: UNSAT proves equivalence,
    SAT yields a counterexample, UNKNOWN is `Err(SmtUnsupported)`."""
    # Share params_a's consts as both functions' free variables (b's own
    # params were already substituted in when translated with its own
    # env -- rebuild b's expr over a's consts by positional identity).
    solver = z3.Solver()
    subst = list(zip(params_b, params_a, strict=True))
    expr_b_over_a = z3.substitute(expr_b, *subst) if subst else expr_b
    solver.add(expr_a != expr_b_over_a)
    return _smt_verdict_for_check(a, b, solver, solver.check(), params_a, z3)


def _smt_verdict_for_check(
    a: str, b: str, solver: Any, verdict: Any, params_a: list[Any], z3: Any
) -> Result[ProbeVerdict, DupError]:
    """Turn a `solver.check()` result into the `_probe_smt_equivalence` verdict."""
    if verdict == z3.unsat:
        _log.info("_probe_smt_equivalence: %s vs %s -- proved equivalent", a, b)
        return Ok(ProbeVerdict(left=a, right=b, equivalent=True, cases_run=0))
    if verdict == z3.sat:
        model = solver.model()
        counterexample = {
            str(p): str(model.eval(p, model_completion=True)) for p in params_a
        }
        _log.info("_probe_smt_equivalence: %s vs %s -- counterexample found", a, b)
        return Ok(
            ProbeVerdict(
                left=a,
                right=b,
                equivalent=False,
                cases_run=1,
                counterexample=counterexample,
            )
        )
    _log.warning("_probe_smt_equivalence: %s vs %s -- solver returned unknown", a, b)
    return Err(DupError.SmtUnsupported)
