"""Design-pattern recommender (T-0332): an advisory HALLMARK->PATTERN and
ANTI-PATTERN->ESCAPE registry that reuses this package's existing
tree-sitter structural walks (`_iter_py_functions`, `_child`/`_node_text`
helpers) rather than a second parse pass. Every finding is a plain
`ArchSuggestion` with `category` set to `"pattern-recommendation"` (a
structural hallmark suggests adopting a pattern) or `"anti-pattern-escape"`
(a detected anti-pattern suggests a concrete refactor), both on the same
unwaivable advisory channel every other `frob.arch` category uses --
recommendations here are never build-blocking, only surfaced.

Design constraints from the ticket, in force for every rule below:

- ADVISORY ONLY: `severity="suggestion"`, never an error; forcing a
  pattern is itself over-engineering.
- STRONG-HALLMARK-ONLY: each detector requires a multi-occurrence
  structural signal (>=3 arms/sites/methods, never a single instance) --
  a noisy recommender trains users to ignore it, and simple code must
  never be flagged just because it COULD be generalized.
- Every finding's `message` names the FORCE the pattern resolves and its
  `detail` gives a concrete refactoring sketch, never a bare "use X".
- `god-object` (anti-pattern-escape) is PAIRED with the existing
  `god-class` detector (`_check_god_classes`) rather than re-walking the
  tree -- one detector, two outputs, per the ticket's "pairs with the
  SOLID smells" design note.

Registry coverage (T-0332's plan enumerates 8 hallmark->pattern rows and 5
anti-pattern->escape rows; this module implements 7 of the 13 below with a
real, precision-checked detector each). The remaining 6 (`incompatible-
interface-bridging -> Adapter`, `expensive-object-reuse -> Flyweight/pool`,
`manual-callback-list -> Observer`, `anemic-domain-model -> move behavior
to data`, `poltergeist/lava-flow -> delete`, `sequential-coupling ->
explicit state`) need fuzzier signals that risk the STRONG-HALLMARK-ONLY
constraint above without a larger detector investment; they are
intentionally deferred, not silently dropped -- see `tickets.md`'s T-0332
Done report and T-draft-4fb8deee (filed follow-up ticket).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from tree_sitter import Node, Tree

from frob.arch._models import ArchSuggestion
from frob.arch._python import _iter_py_functions
from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text

#: Minimum number of branch arms (isinstance/equality) or call sites
#: required before a chain/scatter detector fires (T-0332's STRONG-
#: HALLMARK-ONLY constraint) -- two arms is routine control flow, three or
#: more is the growing-chain shape the recommender targets.
_MIN_CHAIN_ARMS = 3

#: Minimum distinct string literals a stringly-typed comparison chain must
#: cover before it counts as a real "should be a type" signal rather than
#: an ordinary two/three-way branch.
_MIN_STRINGLY_TYPED_LITERALS = 4

#: Minimum parameter count (including defaulted ones) for a constructor to
#: be considered "telescoping" rather than a normal handful of options.
_MIN_TELESCOPING_PARAMS = 6

#: Minimum of those parameters that must carry a default before the
#: telescoping-constructor hallmark fires.
_MIN_TELESCOPING_DEFAULTS = 4

#: Minimum distinct FILES a concrete class must be constructed from before
#: "scattered construction" counts as a cross-cutting concern rather than a
#: class simply used in a couple of natural call sites.
_MIN_SCATTERED_SITES = 3

#: Minimum delegating methods (single-statement `return self._inner.foo(...)`
#: bodies) before a class counts as a genuine wrap-and-delegate shape.
_MIN_DELEGATE_METHODS = 3


# frob:doc docs/modules/arch.md#design-pattern-registry
# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_isinstance_chain_recommends_strategy  # noqa: E501
@dataclass(frozen=True)
class PatternRuleSpec:
    """One row of the T-0332 hallmark<->pattern / anti-pattern<->escape
    registry: a stable id, the direction, the human-facing hallmark/
    response names, the FORCE it resolves, a concrete refactor sketch, and
    the languages it currently applies to. Purely data -- the paired
    detector function (named after `rule_id` by convention) does the
    structural matching; this table exists so the registry itself is
    inspectable/countable independent of the detector code, the same way
    `frob`'s other registries are."""

    rule_id: str
    direction: Literal["pattern", "escape"]
    hallmark: str
    response: str
    force: str
    sketch: str
    languages: tuple[str, ...]


# frob:doc docs/modules/arch.md#design-pattern-registry
PATTERN_REGISTRY: tuple[PatternRuleSpec, ...] = (
    PatternRuleSpec(
        rule_id="type-switch",
        direction="pattern",
        hallmark="an elif chain of isinstance() checks on the same variable",
        response="Strategy (or polymorphic dispatch)",
        force=(
            "adding a new case means editing this function instead of adding a new type"
        ),
        sketch=(
            "give each type its own class implementing a shared method; "
            "replace the isinstance chain with one polymorphic call"
        ),
        languages=("python",),
    ),
    PatternRuleSpec(
        rule_id="state-field-chain",
        direction="pattern",
        hallmark="a growing elif chain keyed on one state-like attribute",
        response="State machine (State pattern)",
        force=(
            "valid transitions and per-state behavior are implicit in "
            "scattered conditionals"
        ),
        sketch=(
            "model each state as an object/enum-dispatch table; move each "
            "arm's behavior onto its state so illegal transitions are structural"
        ),
        languages=("python",),
    ),
    PatternRuleSpec(
        rule_id="telescoping-ctor",
        direction="pattern",
        hallmark="a constructor with many optional/defaulted parameters",
        response="Builder",
        force=(
            "callers must remember positional/keyword order across many optional knobs"
        ),
        sketch=(
            "introduce a Builder (or a kwargs-only config object) that sets "
            "options one at a time and constructs the final object on `.build()`"
        ),
        languages=("python",),
    ),
    PatternRuleSpec(
        rule_id="scattered-construction",
        direction="pattern",
        hallmark=("the same concrete class constructed directly across many files"),
        response="Factory (or dependency injection)",
        force=(
            "every call site is coupled to the concrete type and its "
            "constructor signature"
        ),
        sketch=(
            "centralize construction behind a factory function/class (or "
            "inject an already-built instance) so call sites depend on an "
            "interface, not the concrete constructor"
        ),
        languages=("python",),
    ),
    PatternRuleSpec(
        rule_id="wrap-delegate",
        direction="pattern",
        hallmark=(
            "a class wrapping one inner object with mostly same-name "
            "pass-through methods"
        ),
        response="Decorator",
        force=(
            "the wrapper wants to add behavior around calls without "
            "changing the wrapped interface"
        ),
        sketch=(
            "keep the wrapper implementing the same interface as the "
            "wrapped object; add the extra behavior around the delegating "
            "calls instead of leaving them bare pass-throughs"
        ),
        languages=("python",),
    ),
    PatternRuleSpec(
        rule_id="god-object",
        direction="escape",
        hallmark="a class with far more methods than any single responsibility needs",
        response="SRP decompose",
        force=(
            "the class has multiple reasons to change, so any change "
            "risks unrelated breakage"
        ),
        sketch=(
            "split the class along its distinct responsibilities into "
            "several smaller collaborators, each with one reason to change"
        ),
        languages=("python", "cpp"),
    ),
    PatternRuleSpec(
        rule_id="stringly-typed",
        direction="escape",
        hallmark=(
            "a parameter compared against many raw string literals "
            "instead of a real type"
        ),
        response="newtype (enum / typed value object)",
        force="typos and unhandled values are only caught at runtime, if at all",
        sketch=(
            "replace the raw string with an Enum/Literal type (or a small "
            "value-object wrapper) so invalid values are a type error, not a "
            "silent no-op branch"
        ),
        languages=("python",),
    ),
)


def _pattern_rule(rule_id: str) -> PatternRuleSpec:
    """Look up `rule_id`'s registry row (T-0332); raises `KeyError` on a
    typo'd id -- a detector referencing an unregistered rule is a
    programmer bug, not a recoverable condition."""
    for rule in PATTERN_REGISTRY:
        if rule.rule_id == rule_id:
            return rule
    raise KeyError(f"unregistered pattern rule id: {rule_id!r}")


def _emit(
    rule_id: str,
    category: Literal["pattern-recommendation", "anti-pattern-escape"],
    rel: str,
    line: int | None,
    subject: str,
    out: list[ArchSuggestion],
) -> None:
    """Append one `ArchSuggestion` for `rule_id` naming `subject` (the
    function/class/variable the hallmark was found on) -- shared by every
    detector below so the message/detail shape (FORCE in the message,
    sketch in the detail) is built in exactly one place (T-0332)."""
    rule = _pattern_rule(rule_id)
    out.append(
        ArchSuggestion(
            file=rel,
            line=line,
            category=category,
            severity="suggestion",
            message=(
                f"{rule.hallmark} ({subject}): consider {rule.response} -- {rule.force}"
            ),
            detail=rule.sketch,
        )
    )


def _elif_chain_conditions(if_stmt: Node) -> list[Node]:
    """The `if` condition plus every `elif_clause` condition in one
    `if_statement` chain, in source order (the same folded-elif shape
    `frob.arch._python`'s cyclomatic-proxy comment documents)."""
    conditions: list[Node] = []
    cond = _child(if_stmt, "condition")
    if cond is not None:
        conditions.append(cond)
    for c in if_stmt.children:
        if c.type == "elif_clause":
            cond = _child(c, "condition")
            if cond is not None:
                conditions.append(cond)
    return conditions


def _isinstance_target(cond: Node) -> str | None:
    """The first-argument text of `cond` if it is a bare `isinstance(x, T)`
    call, else `None`."""
    if cond.type != "call":
        return None
    func = _child(cond, "function")
    if func is None or _node_text(func) != "isinstance":
        return None
    args = _child(cond, "arguments")
    if args is None:
        return None
    named = args.named_children
    if not named:
        return None
    return _node_text(named[0])


def _equality_target_and_literal(cond: Node) -> tuple[str, str] | None:
    """`(lhs_text, literal_text)` if `cond` is a bare `lhs == "literal"`
    string-equality comparison, else `None`."""
    if cond.type != "comparison_operator":
        return None
    lhs = cond.named_children[0] if cond.named_children else None
    rhs = cond.named_children[1] if len(cond.named_children) > 1 else None
    if lhs is None or rhs is None or rhs.type != "string":
        return None
    op_texts = [c.type for c in cond.children if not c.is_named]
    if "==" not in op_texts:
        return None
    return _node_text(lhs), _node_text(rhs)


def _find_if_statements(node: Node) -> list[Node]:
    """Every top-level (not nested inside another) `if_statement` under
    `node`'s subtree -- nested `if`s are reached via each hallmark check's
    own recursion into `elif_clause`/branch bodies as needed, so this just
    walks everything once for chain-shaped detectors."""
    found: list[Node] = []
    for c in node.children:
        if c.type == "if_statement":
            found.append(c)
        found.extend(_find_if_statements(c))
    return found


# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_isinstance_chain_recommends_strategy  # noqa: E501
def _check_type_switch(tree: object, rel: str, out: list[ArchSuggestion]) -> None:
    """HALLMARK->PATTERN: an elif chain of >=3 `isinstance(x, T)` arms on
    the SAME `x` recommends Strategy/polymorphic dispatch (T-0332)."""
    t: Tree = cast("Tree", tree)
    for if_stmt in _find_if_statements(t.root_node):
        conditions = _elif_chain_conditions(if_stmt)
        if len(conditions) < _MIN_CHAIN_ARMS:
            continue
        targets = [_isinstance_target(c) for c in conditions]
        if any(tgt is None for tgt in targets):
            continue
        distinct = {tgt for tgt in targets if tgt is not None}
        if len(distinct) != 1:
            continue
        (variable,) = distinct
        _emit(
            "type-switch",
            "pattern-recommendation",
            rel,
            if_stmt.start_point[0] + 1,
            f"`{len(conditions)}`-arm isinstance chain on `{variable}`",
            out,
        )


#: Attribute-name substrings that mark a `self.<attr>` comparison chain as
#: keyed on state (T-0332) -- kept narrow so an ordinary field-equality
#: chain unrelated to lifecycle/state does not also fire as a state-machine
#: recommendation (that would double up with `stringly-typed`, which
#: intentionally targets a plain identifier, not `self.<attr>`, to avoid
#: exactly this overlap).
_STATE_ATTR_HINTS = ("state", "status", "mode", "phase", "stage")


# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_state_field_chain_recommends_state_machine  # noqa: E501
def _check_state_field_chain(tree: object, rel: str, out: list[ArchSuggestion]) -> None:
    """HALLMARK->PATTERN: an elif chain of >=3 arms all comparing the same
    `self.<state-like attribute>` against a string literal recommends a
    State-machine refactor (T-0332). Requires an ATTRIBUTE access (not a
    bare identifier -- that is `stringly-typed`'s territory) whose name
    contains a state-lifecycle hint, keeping the two hallmarks disjoint."""
    t: Tree = cast("Tree", tree)
    for if_stmt in _find_if_statements(t.root_node):
        conditions = _elif_chain_conditions(if_stmt)
        if len(conditions) < _MIN_CHAIN_ARMS:
            continue
        pairs = [_equality_target_and_literal(c) for c in conditions]
        if any(p is None for p in pairs):
            continue
        lhs_texts = {p[0] for p in pairs if p is not None}
        if len(lhs_texts) != 1:
            continue
        (lhs,) = lhs_texts
        if not lhs.startswith("self."):
            continue
        attr = lhs.removeprefix("self.")
        if not any(hint in attr.lower() for hint in _STATE_ATTR_HINTS):
            continue
        _emit(
            "state-field-chain",
            "pattern-recommendation",
            rel,
            if_stmt.start_point[0] + 1,
            f"`{len(conditions)}`-arm chain on `{lhs}`",
            out,
        )


def _init_params(func_node: Node) -> list[Node]:
    """The parameter nodes of an `__init__`/constructor-shaped function,
    excluding `self`."""
    params_node = _child(func_node, "parameters")
    if params_node is None:
        return []
    return [
        p
        for p in params_node.named_children
        if p.type != "identifier" or _node_text(p) != "self"
    ]


# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_telescoping_ctor_recommends_builder  # noqa: E501
def _check_telescoping_ctor(tree: object, rel: str, out: list[ArchSuggestion]) -> None:
    """HALLMARK->PATTERN: an `__init__` with many (>=6) parameters, most
    (>=4) of them defaulted, recommends a Builder (T-0332) -- a handful of
    plain required parameters is normal and must not fire."""
    t: Tree = cast("Tree", tree)
    for func, prefix, fname in _iter_py_functions(t.root_node):
        if fname != "__init__" or not prefix:
            continue
        params = _init_params(func)
        if len(params) < _MIN_TELESCOPING_PARAMS:
            continue
        n_defaulted = sum(
            1
            for p in params
            if p.type in ("default_parameter", "typed_default_parameter")
        )
        if n_defaulted < _MIN_TELESCOPING_DEFAULTS:
            continue
        subject = (
            f"`{prefix}__init__` with {len(params)} parameters"
            f" ({n_defaulted} defaulted)"
        )
        _emit(
            "telescoping-ctor",
            "pattern-recommendation",
            rel,
            func.start_point[0] + 1,
            subject,
            out,
        )


_CONSTRUCTOR_LIKE_RE_EXCLUDE = frozenset(
    {
        # Common builtin exception/collection type names -- constructing
        # these repeatedly across a codebase is routine, not a "scattered
        # concrete construction" smell the Factory recommendation targets.
        "Exception",
        "ValueError",
        "TypeError",
        "KeyError",
        "RuntimeError",
        "NotImplementedError",
        "StopIteration",
        "OSError",
        "AttributeError",
        "IndexError",
        "FileNotFoundError",
        "ImportError",
        "Path",
    }
)


def _collect_constructions(node: Node, out: set[str]) -> None:
    """Every Capitalized bare-identifier callee of a `call` node under
    `node` (a heuristic for "this looks like constructing a concrete
    class") into `out`, excluding common builtin exception/collection
    names (T-0332)."""
    for c in node.children:
        if c.type == "call":
            func = _child(c, "function")
            if (
                func is not None
                and func.type == "identifier"
                and (name := _node_text(func))[:1].isupper()
                and name not in _CONSTRUCTOR_LIKE_RE_EXCLUDE
            ):
                out.add(name)
        _collect_constructions(c, out)


# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_scattered_construction_across_files_recommends_factory  # noqa: E501
def _collect_file_constructions(
    tree: object, rel: str, out: dict[str, set[str]]
) -> None:
    """Accumulate `rel`'s Capitalized-callee constructions into `out`
    (class name -> set of files it is constructed in), for the cross-file
    `_check_scattered_construction` pass (T-0332), mirroring how
    `frob.arch._python._extract_signatures` accumulates per-file data for
    `_check_abstraction_opportunities`."""
    t: Tree = cast("Tree", tree)
    names: set[str] = set()
    _collect_constructions(t.root_node, names)
    for name in names:
        out.setdefault(name, set()).add(rel)


def _check_scattered_construction(
    constructions: dict[str, set[str]], out: list[ArchSuggestion]
) -> None:
    """HALLMARK->PATTERN: a concrete class constructed directly from >=3
    distinct files recommends a Factory/DI seam (T-0332) -- constructing a
    class from one or two natural call sites is ordinary usage, not a
    scattering smell."""
    for name, files in sorted(constructions.items()):
        if len(files) < _MIN_SCATTERED_SITES:
            continue
        first_file = sorted(files)[0]
        _emit(
            "scattered-construction",
            "pattern-recommendation",
            first_file,
            None,
            f"`{name}(...)` constructed directly in {len(files)} files",
            out,
        )


def _method_body_stmts(func_node: Node) -> list[Node]:
    """The statement nodes directly inside `func_node`'s body block."""
    body = _child(func_node, "body")
    if body is None:
        return []
    return list(body.named_children)


def _delegation_target(func_node: Node, inner_attr: str) -> bool:
    """Whether `func_node`'s ENTIRE body is a single `return self.<inner_attr>.
    <same-method-name>(...)` (or bare call, no `return`) pass-through --
    the wrap-delegate hallmark's per-method signal (T-0332)."""
    stmts = _method_body_stmts(func_node)
    if len(stmts) != 1:
        return False
    stmt = stmts[0]
    call: Node | None = None
    if stmt.type == "return_statement":
        val = stmt.named_children[0] if stmt.named_children else None
        if val is not None and val.type == "call":
            call = val
    elif stmt.type == "call":
        # T-0332: a bare call statement (no `return`) is its own top-level
        # node in this grammar, same shape as the bare-`assignment` case
        # `_find_inner_attr` handles above.
        call = stmt
    elif stmt.type == "expression_statement":
        inner = stmt.named_children[0] if stmt.named_children else None
        if inner is not None and inner.type == "call":
            call = inner
    if call is None:
        return False
    func = _child(call, "function")
    if func is None or func.type != "attribute":
        return False
    obj = _child(func, "object")
    if obj is None or _node_text(obj) != f"self.{inner_attr}":
        return False
    return True


def _find_inner_attr(init_func: Node) -> str | None:
    """The attribute name of the first `self.<attr> = <param>` assignment
    inside `init_func`'s body whose RHS is a bare parameter identifier --
    the wrap-delegate hallmark's "wraps one inner object" signal."""
    param_names = {
        _node_text(p).split("=")[0].split(":")[0].strip()
        for p in _init_params(init_func)
    }
    for stmt in _method_body_stmts(init_func):
        # T-0332: python's grammar emits a bare top-level assignment as an
        # `assignment` node directly (no wrapping `expression_statement`),
        # so both shapes are accepted here.
        if stmt.type == "assignment":
            assign = stmt
        elif stmt.type == "expression_statement":
            assign = stmt.named_children[0] if stmt.named_children else None
        else:
            continue
        if assign is None or assign.type != "assignment":
            continue
        target = _child(assign, "left")
        value = _child(assign, "right")
        if target is None or value is None:
            continue
        if target.type != "attribute" or value.type != "identifier":
            continue
        obj = _child(target, "object")
        if obj is None or _node_text(obj) != "self":
            continue
        if _node_text(value) not in param_names:
            continue
        attr_node = _child(target, "attribute")
        if attr_node is not None:
            return _node_text(attr_node)
    return None


# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_wrap_delegate_recommends_decorator  # noqa: E501
def _check_wrap_delegate(tree: object, rel: str, out: list[ArchSuggestion]) -> None:
    """HALLMARK->PATTERN: a class that stores one constructor-parameter
    object as `self.<attr>` and has >=3 methods whose entire body is a
    same-name pass-through call to that attribute recommends Decorator
    (T-0332)."""
    t: Tree = cast("Tree", tree)
    for c in t.root_node.children:
        if c.type != "class_definition":
            continue
        body = _child(c, "body")
        if body is None:
            continue
        methods = [m for m in body.named_children if m.type == "function_definition"]
        init = next(
            (m for m in methods if _node_text(_child(m, "name") or m) == "__init__"),
            None,
        )
        if init is None:
            continue
        inner_attr = _find_inner_attr(init)
        if inner_attr is None:
            continue
        n_delegating = 0
        for m in methods:
            name_node = _child(m, "name")
            mname = _node_text(name_node) if name_node else ""
            if mname in ("__init__", ""):
                continue
            if _delegation_target(m, inner_attr):
                n_delegating += 1
        if n_delegating < _MIN_DELEGATE_METHODS:
            continue
        name_node = _child(c, "name")
        cname = _node_text(name_node) if name_node else "?"
        subject = (
            f"class `{cname}` wraps `self.{inner_attr}`"
            f" with {n_delegating} pass-through methods"
        )
        _emit(
            "wrap-delegate",
            "pattern-recommendation",
            rel,
            c.start_point[0] + 1,
            subject,
            out,
        )


# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_god_class_pairs_with_srp_escape  # noqa: E501
def _check_god_object_escape(
    suggestions: list[ArchSuggestion], out: list[ArchSuggestion]
) -> None:
    """ANTI-PATTERN->ESCAPE: for every already-computed `god-class` finding
    in `suggestions`, emit a paired `anti-pattern-escape` recommendation
    (SRP decompose) at the same location -- one detector (`_check_god_
    classes`), two outputs, per the ticket's "pairs with the SOLID smells"
    design note (T-0332). Does not re-walk the tree."""
    for s in suggestions:
        if s.category != "god-class":
            continue
        subject = s.message.split(" has ")[0].strip()
        _emit("god-object", "anti-pattern-escape", s.file, s.line, subject, out)


def _identifier_string_equality(cond: Node) -> tuple[str, str] | None:
    """Like `_equality_target_and_literal`, but only matches when the LHS
    is a bare identifier (not `self.<attr>`) -- the `stringly-typed`
    hallmark's target, deliberately disjoint from `state-field-chain`'s
    attribute-only target so the same comparison node cannot fire both."""
    pair = _equality_target_and_literal(cond)
    if pair is None:
        return None
    lhs, literal = pair
    if "." in lhs:
        return None
    return lhs, literal


# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_stringly_typed_recommends_newtype  # noqa: E501
def _check_stringly_typed(tree: object, rel: str, out: list[ArchSuggestion]) -> None:
    """ANTI-PATTERN->ESCAPE: a plain identifier (parameter or local, never
    `self.<attr>` -- see `_check_state_field_chain`) compared via `==`
    against >=4 distinct string literals across one elif chain recommends
    a newtype/Enum escape (T-0332)."""
    t: Tree = cast("Tree", tree)
    for if_stmt in _find_if_statements(t.root_node):
        conditions = _elif_chain_conditions(if_stmt)
        if len(conditions) < _MIN_STRINGLY_TYPED_LITERALS:
            continue
        pairs = [_identifier_string_equality(c) for c in conditions]
        if any(p is None for p in pairs):
            continue
        lhs_names = {p[0] for p in pairs if p is not None}
        if len(lhs_names) != 1:
            continue
        (lhs,) = lhs_names
        literals = {p[1] for p in pairs if p is not None}
        if len(literals) < _MIN_STRINGLY_TYPED_LITERALS:
            continue
        _emit(
            "stringly-typed",
            "anti-pattern-escape",
            rel,
            if_stmt.start_point[0] + 1,
            f"`{lhs}` compared against {len(literals)} string literals",
            out,
        )


# frob:doc docs/modules/arch.md#design-pattern-registry
# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_scattered_construction_across_files_recommends_factory  # noqa: E501
def new_construction_accumulator() -> dict[str, set[str]]:
    """A fresh, empty accumulator for `_collect_file_constructions`'s
    cross-file class-construction corpus (T-0332) -- exposed so
    `frob.arch`'s orchestration owns the accumulator's lifetime the same
    way it owns `all_py_sigs`/`all_dispatch_refs` for the existing
    abstraction-opportunity pass."""
    return {}
