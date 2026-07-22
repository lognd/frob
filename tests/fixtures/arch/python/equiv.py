"""T-0615 N:1 equivalence fixture (python side).

Deliberately identical STRUCTURAL shape to `equiv.ts` / `equiv.rs` /
`equiv.kt` in this directory: one base class, one derived class with a
field, an overridden method, and a "dispatch" free function using
whatever construct is idiomatic per language. Python's own idiomatic
dispatch construct is an if/elif/else chain -- but `tree-sitter-python`'s
grammar folds an ENTIRE if/elif/else chain into ONE `if_statement` node
with `elif_clause` children (`frob.arch._python`'s own `_BRANCH_NODE_TYPES`/
`_BRANCH_EVENT_TYPES` comment), so this dispatch function scores as
exactly ONE `NormalizedBranch`, not three -- a genuine, DOCUMENTED
divergence from rust's `match` and kotlin's `when` (each arm its own
branch, T-0612/T-0614) and from TypeScript's `switch` (walked for nesting
depth but produces ZERO branches, `frob.arch._typescript`'s own
`_TS_NESTING_TYPES`/branch-producing-types split). The four-way
equivalence meta-test pins all three shapes (1 branch / 0 branches / N
branches for the SAME three-way dispatch) side by side as EXPECTED, not
a bug in any one adapter.
"""

from __future__ import annotations


class Creature:
    """Base class every language's fixture's derived class extends."""

    def speak(self) -> str:
        """Base greeting; overridden by every language's derived class."""
        return "..."


class Animal(Creature):
    """Derived class carrying one field and one overriding method.

    `name`/`age` are declared as class-level annotated fields (the shape
    `PythonAdapter._py_class_fields` is DOCUMENTED to walk), on top of the
    usual `self.name = ...` constructor assignment. WAIVER (filed as
    T-draft-d49c456f, out of T-0615's scope -- `src/frob/arch/_python.py`
    is not in this ticket's `scope`): `_py_class_fields` never actually
    matches these today -- it gates on `c.type == "expression_statement"`
    wrapping the assignment, but `tree-sitter-python`'s grammar hands back
    the `assignment` node directly as the class block's own named child,
    with no `expression_statement` wrapper -- so `PythonAdapter().adapt(
    ...).classes[0].fields` comes back EMPTY for this fixture (and for
    every class-level annotated field, verified directly against
    `PythonAdapter`). The four-way equivalence meta-test documents this as
    an observed WAIVER for python's field-count comparison rather than
    silently expecting parity with TS/rust/kotlin (which all do capture
    this shape)."""

    name: str
    age: int

    def __init__(self, name: str, age: int = 1) -> None:
        """Store the animal's name and age."""
        self.name = name
        self.age = age

    def speak(self) -> str:
        """Override of `Creature.speak` -- python has no static `override`
        keyword, so `NormalizedFunction.overrides` stays `None` here even
        though this genuinely overrides the base method (a documented
        WAIVER, not a missed mapping -- see the equivalence meta-test)."""
        return self.name


def configure_pipeline(a: bool, b: bool, c: bool, d: int) -> bool:
    """Long/complex function: nested if/for/while plus a boolean branch,
    identical control-flow shape to `configurePipeline` in every other
    language's fixture (same nesting depth, same cyclomatic contributors)."""
    if a:
        if b:
            if c:
                for i in range(d):
                    if i:
                        while i:
                            if a and b:
                                pass
                            i -= 1
    return a


def dispatch_kind(kind: str) -> int:
    """Dispatch over three cases via if/elif -- python's idiomatic
    equivalent of rust's `match`/kotlin's `when`/TS's `switch`. Each
    if/elif arm IS counted as its own `NormalizedBranch` (python's
    `_iter_py_functions` walk treats `if`/`elif` uniformly), unlike TS's
    `switch_statement` which is walked but NOT turned into branches
    (`frob.arch._typescript`'s own documented exclusion) -- the four-way
    test pins both divergences side by side."""
    if kind == "happy":
        return 0
    elif kind == "sad":
        return 1
    else:
        return 2
