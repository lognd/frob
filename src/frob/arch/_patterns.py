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
- T-0617: `iter_type_switch_chains` (module-public by convention, no
  leading underscore) is the same one-detector-two-outputs move in the
  other direction -- `frob.arch._ocp`'s OCP type-dispatch-smell check
  reuses this module's isinstance-chain walk instead of re-implementing
  it; `_check_type_switch` and the OCP check are just two different
  readings of the identical structural signal.

Registry coverage (T-0332's plan enumerates 8 hallmark->pattern rows and 5
anti-pattern->escape rows; T-0332 shipped 7 of the 13 with a real,
precision-checked detector each). T-0605 (phase 2) picks up the 6 T-0332
deferred and resolves each on its own merits rather than shipping a
uniform "fuzzier signal" pass:

- `interface-translate -> Adapter`: SHIPPED (`_check_interface_translate`).
  Reuses `wrap-delegate`'s "stores one constructor-param object as
  `self.<attr>`" shape but requires the opposite call-name relationship --
  >=3 methods whose entire body is a single call to a DIFFERENTLY-named
  method on that inner object (a same-name pass-through is `wrap-delegate`
  -> Decorator; a renamed/translated call is the Adapter hallmark). The two
  detectors are disjoint PER-METHOD ONLY (a same-name delegating method can
  never also count as a translating one) -- NOT per-class. A class that
  mixes both shapes (some methods same-name pass-through, a separate >=3
  methods translating) legitimately fires BOTH `wrap-delegate` and
  `interface-translate`: each recommendation is a true, independent
  structural fact about a disjoint SUBSET of that class's methods, not a
  claim about the whole class, so two suggestions naming two different
  method groups is not a contradiction -- see
  `test_mixed_delegate_and_translate_methods_fires_both` (reviewer round 1,
  T-0605).
- `manual-callback-list -> Observer`: SHIPPED
  (`_check_manual_callback_list`). Requires THREE co-occurring structural
  facts in one class: an empty-list attribute initialized in `__init__`,
  a distinct method that appends to it, and a distinct method that
  iterates it calling each element -- the register/notify shape a hand-
  rolled Observer always has. A plain list attribute used for storage
  only (append, no notify loop) or iterated without ever being appended
  to does not fire.
- `anemic-accessors -> move behavior to data` (anti-pattern-escape):
  SHIPPED (`_check_anemic_accessors`). Requires >=3 non-`__init__`,
  non-dunder methods where EVERY one is a trivial single-statement getter
  (`return self.<attr>`, no computation) or setter (`self.<attr> =
  <param>`) -- a class that does nothing but move data in and out, the
  textbook anemic-domain-model hallmark. One real method with actual
  logic (a conditional, a loop, a computed expression) anywhere in the
  class disqualifies it.

The remaining 3 (`expensive-object-reuse -> Flyweight/pool`,
`poltergeist/lava-flow -> delete`, `sequential-coupling -> explicit
state`) are recorded as reasoned NOT-CHECKABLE, not silently dropped:

- Flyweight/pool: the hallmark is "many equivalent, expensive-to-
  construct objects created where one shared/pooled instance would do."
  There is no single-file structural signal for "expensive to construct"
  or "equivalent" without value/dataflow analysis this package does not
  have (repeated `ClassName(...)` calls in a loop are indistinguishable
  from an ordinary loop building N *different* objects without knowing
  whether the constructor arguments are load-bearing) -- any tree-sitter-
  only heuristic here would be a coin flip, which is worse than silence
  per the STRONG-HALLMARK-ONLY constraint.
- Poltergeist/lava-flow: the catalog itself notes poltergeist is "dup of
  Middle Man, at extreme" (docs/design/architecture-check-catalog.md) --
  its degenerate case (a class with essentially zero methods beyond a
  pure-forwarding one or two) is not distinguishable in practice from a
  small, well-designed adapter/wrapper without knowing whether the class
  is actually load-bearing elsewhere, and "nobody dares remove it"
  (lava-flow's half of this combined registry row) requires whole-
  program reachability/usage evidence (a dead-code/call-graph analysis),
  not a per-file structural walk -- outside this module's scope.
- Sequential coupling: the catalog notes it is "dup of Connascence of
  Execution." A structural proxy exists in principle (a private boolean
  flag set by one method and checked-and-raised by another, enforcing
  call order) but is easily confused with ordinary guard-clause
  validation (`if not self._ready: raise ...` is extremely common and
  not itself evidence of a *coupling* problem versus a legitimate
  precondition check) -- distinguishing the two without tracking actual
  call-order violations across callers would require the same call-graph
  investment as lava-flow above, not a bigger detector, a DIFFERENT kind
  of analysis this package does not yet do.

`docs/design/registry/patterns.yaml`'s corresponding rows (`GOF-ADAPTER`,
`GOF-FLYWEIGHT`, `GOF-OBSERVER`, `PAT-TRAP-20-ANEMIC-DOMAIN-GOD-OBJECT-
LAVA-FLOW`) all correctly stay `out_of_scope:advisory-design-pattern-
recommendation` regardless of whether a detector exists for their
hallmark -- T-0332's own precedent (its 7 shipped detectors' rows carry
the identical disposition) establishes that this registry tracks whether
a row is subject to enforceable GATE tracking, not whether `frob.arch`
happens to implement an advisory recommender for it; a GoF/trap catalog
entry is inherently advisory-only either way. See `tickets.md`'s T-0605
Done report for the full per-pattern reasoning.

T-0849 (phase 3) worked or dispositioned the 41 `patterns.yaml` rows
re-pointed to it when T-0605 closed (`DDD-II-*`, `RELEASEIT-*`,
`PYIDIOM-*`): 2 new detectors shipped (`dataclass-boilerplate`,
`manual-decorator-wrap`, both `PYIDIOM-*` rows), the rest recorded
`out_of_scope` for reasons ranging from "domain-semantic judgment, not a
structural signal" (`DDD-II-*`) to "runtime/distributed property, no
single-file signal" (`RELEASEIT-*`) to "the honest structural proxy
requires an investment (body-similarity comparison, cross-file type
inference, call-graph reachability) this package does not have anywhere
yet" (the remaining `PYIDIOM-*` rows). See docs/modules/arch.md's
"T-0849 phase 3" section and `tickets.md`'s T-0849 Done report for the
full per-pattern reasoning.
"""
# frob:waive INV006 reason="T-1023 INV006 burn-down: this file's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim, same \
# INV006 first-turn-on-pool disposition this repo already applies elsewhere (T-0585)"

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

#: Minimum translating methods (single-statement calls to a DIFFERENTLY
#: named method on the stored inner object) before a class counts as the
#: Adapter hallmark (T-0605) -- mirrors `_MIN_DELEGATE_METHODS`'s floor for
#: the same-name `wrap-delegate` shape.
_MIN_TRANSLATE_METHODS = 3

#: Minimum non-`__init__`, non-dunder methods a class must have before the
#: "every method is a trivial getter/setter" anemic-domain-model hallmark
#: fires (T-0605) -- a one- or two-method value holder is not yet the
#: "moved all behavior elsewhere" smell the escape targets.
_MIN_ANEMIC_ACCESSORS = 3

#: Minimum `__init__` parameters a hand-written value-holder class must
#: have before the "boilerplate `__init__`" hallmark fires (T-0849) -- a
#: one- or two-field holder is not worth a `@dataclass` recommendation;
#: mirrors `_MIN_ANEMIC_ACCESSORS`'s floor for the same "not worth
#: flagging yet" reasoning.
_MIN_DATACLASS_FIELDS = 3

#: Minimum module-level `def f(...): ...` / `f = wrapper(f)` reassignment
#: pairs required in one file before the manual-decorator-wrap hallmark
#: fires (T-0849) -- STRONG-HALLMARK-ONLY per this module's doctrine, same
#: multi-occurrence floor as every chain/scatter detector above.
_MIN_MANUAL_DECORATOR_WRAPS = 3


# frob:doc docs/modules/arch.md#design-pattern-registry
# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_isinstance_chain_recommends_strategy  # noqa: E501
@dataclass(frozen=True)
# frob:waive COV007 reason="T-0871: same -- see COV005 waiver above"
class _PatternRuleSpec:
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
PATTERN_REGISTRY: tuple[_PatternRuleSpec, ...] = (
    _PatternRuleSpec(
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
    _PatternRuleSpec(
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
    _PatternRuleSpec(
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
    _PatternRuleSpec(
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
    _PatternRuleSpec(
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
    _PatternRuleSpec(
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
    _PatternRuleSpec(
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
    _PatternRuleSpec(
        rule_id="interface-translate",
        direction="pattern",
        hallmark=(
            "a class wraps one inner object with mostly DIFFERENTLY-named "
            "translating methods"
        ),
        response="Adapter",
        force=(
            "callers need this object's interface but the only available "
            "implementation speaks a different, incompatible one"
        ),
        sketch=(
            "keep the wrapper implementing the CALLER's expected interface "
            "and translate each call into the inner object's own method "
            "names, isolating the incompatibility at one seam"
        ),
        languages=("python",),
    ),
    _PatternRuleSpec(
        rule_id="manual-callback-list",
        direction="pattern",
        hallmark=(
            "a class hand-manages a list of callbacks: appended in one "
            "method, iterated and invoked in another"
        ),
        response="Observer",
        force=(
            "subscribe/notify bookkeeping is ad hoc instead of a named, "
            "reusable subject/listener contract"
        ),
        sketch=(
            "formalize the list as a Subject with add_observer/notify (or "
            "an explicit Listener protocol) so the register/notify contract "
            "is named and reusable instead of an anonymous list"
        ),
        languages=("python",),
    ),
    _PatternRuleSpec(
        rule_id="anemic-accessors",
        direction="escape",
        hallmark=(
            "every method on the class is a trivial getter or setter, "
            "with no real behavior anywhere"
        ),
        response="move behavior to data (rich domain model)",
        force=(
            "logic that belongs with this data lives scattered in whatever "
            "callers happen to read/write these fields instead"
        ),
        sketch=(
            "move the operations callers perform on this data onto the "
            "class itself as real methods, so the object enforces its own "
            "invariants instead of exposing raw field access"
        ),
        languages=("python",),
    ),
    _PatternRuleSpec(
        rule_id="dataclass-boilerplate",
        direction="pattern",
        hallmark=(
            "a plain class whose only member is an `__init__` that does "
            "nothing but assign every parameter to a same-named `self.<attr>`"
        ),
        response="@dataclass",
        force=(
            "the class hand-writes constructor boilerplate a `@dataclass` "
            "generates for free, and gets none of `__repr__`/`__eq__` either"
        ),
        sketch=(
            "replace the hand-written `__init__` with `@dataclass` and a "
            "plain field per attribute; add `frozen=True` if the value "
            "should be immutable"
        ),
        languages=("python",),
    ),
    _PatternRuleSpec(
        rule_id="manual-decorator-wrap",
        direction="pattern",
        hallmark=(
            "a function reassigned to the result of calling a wrapper on "
            "itself (`f = wrapper(f)`) instead of `@wrapper` syntax"
        ),
        response="decorator syntax (`@wrapper`)",
        force=(
            "the manual reassignment separates the wrapping from the "
            "definition it modifies, and is easy to miss or reorder"
        ),
        sketch=(
            "move the wrapper call onto the definition as `@wrapper` "
            "directly above `def f(...):`, removing the separate "
            "reassignment statement"
        ),
        languages=("python",),
    ),
)


def _pattern_rule(rule_id: str) -> _PatternRuleSpec:
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


# frob:doc docs/modules/arch.md#ocp-checks
# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_isinstance_chain_recommends_strategy  # noqa: E501
# frob:tests tests/unit/test_arch_ocp.py::TestTypeDispatchSmell.test_isinstance_chain_flags_ocp_violation  # noqa: E501
def iter_type_switch_chains(tree: object) -> list[tuple[Node, str, int]]:
    """ONE detector, TWO outputs (T-0332's own design note, reused for
    T-0617's OCP check): every `(if_stmt, variable, arm_count)` triple for
    an elif chain of >=`_MIN_CHAIN_ARMS` bare `isinstance(x, T)` arms all
    on the SAME `x`, in source order. `_check_type_switch` below reads this
    as "consider Strategy" (`pattern-recommendation`); `frob.arch._ocp`'s
    `_check_type_dispatch_smell` reads the identical structural signal as
    an OCP violation (`type-dispatch-smell`) -- neither re-walks the tree
    or re-derives the isinstance-chain shape, both just call this."""
    t: Tree = cast("Tree", tree)
    found: list[tuple[Node, str, int]] = []
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
        found.append((if_stmt, variable, len(conditions)))
    return found


def _check_type_switch(tree: object, rel: str, out: list[ArchSuggestion]) -> None:
    """HALLMARK->PATTERN: an elif chain of >=3 `isinstance(x, T)` arms on
    the SAME `x` recommends Strategy/polymorphic dispatch (T-0332)."""
    for if_stmt, variable, n_arms in iter_type_switch_chains(tree):
        _emit(
            "type-switch",
            "pattern-recommendation",
            rel,
            if_stmt.start_point[0] + 1,
            f"`{n_arms}`-arm isinstance chain on `{variable}`",
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


# frob:ticket T-0972
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
        # frob:waive PERF004 reason="files is this loop's own per-name distinct set, not a shared re-sort"  # noqa: E501
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


def _translation_target(func_node: Node, inner_attr: str, own_name: str) -> bool:
    """Whether `func_node`'s ENTIRE body is a single call (bare, or wrapped
    in a `return`) to `self.<inner_attr>.<other_name>(...)` where
    `other_name != own_name` -- the Adapter hallmark's per-method signal
    (T-0605), the mirror image of `_delegation_target`'s same-name check.
    Reuses `_delegation_target`'s statement-unwrapping shape so the two
    detectors read identically except for the name comparison."""
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
    attr_node = _child(func, "attribute")
    called_name = _node_text(attr_node) if attr_node is not None else ""
    return bool(called_name) and called_name != own_name


# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_translating_wrapper_recommends_adapter  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_mixed_delegate_and_translate_methods_fires_both  # noqa: E501
def _check_interface_translate(
    tree: object, rel: str, out: list[ArchSuggestion]
) -> None:
    """HALLMARK->PATTERN (T-0605): a class that stores one constructor-
    parameter object as `self.<attr>` and has >=3 methods whose entire
    body is a single call to a DIFFERENTLY-named method on that attribute
    recommends Adapter -- the renamed-call shape that distinguishes
    "bridging an incompatible interface" from `wrap-delegate`'s same-name
    pass-through (-> Decorator). A method that same-name delegates never
    also counts as translating -- the two hallmarks are disjoint PER-
    METHOD, never per-class: a class with a same-name-delegating subset
    AND a separate >=3-method translating subset legitimately fires BOTH
    `wrap-delegate` and `interface-translate` (two independent findings
    about two disjoint method groups, not a contradictory claim about the
    whole class) -- see
    `test_mixed_delegate_and_translate_methods_fires_both` (reviewer round
    1, T-0605)."""
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
        n_translating = 0
        for m in methods:
            name_node = _child(m, "name")
            mname = _node_text(name_node) if name_node else ""
            if mname in ("__init__", ""):
                continue
            if _translation_target(m, inner_attr, mname):
                n_translating += 1
        if n_translating < _MIN_TRANSLATE_METHODS:
            continue
        name_node = _child(c, "name")
        cname = _node_text(name_node) if name_node else "?"
        subject = (
            f"class `{cname}` wraps `self.{inner_attr}`"
            f" with {n_translating} renamed translating methods"
        )
        _emit(
            "interface-translate",
            "pattern-recommendation",
            rel,
            c.start_point[0] + 1,
            subject,
            out,
        )


def _empty_list_attrs(init_func: Node) -> set[str]:
    """Every `self.<attr> = []` (bare empty-list-literal) assignment target
    inside `init_func`'s body -- the manual-callback-list hallmark's
    "backing store" signal (T-0605)."""
    attrs: set[str] = set()
    for stmt in _method_body_stmts(init_func):
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
        if target.type != "attribute" or value.type != "list" or value.named_children:
            continue
        obj = _child(target, "object")
        if obj is None or _node_text(obj) != "self":
            continue
        attr_node = _child(target, "attribute")
        if attr_node is not None:
            attrs.add(_node_text(attr_node))
    return attrs


def _method_appends_to(func_node: Node, attr: str) -> bool:
    """Whether any `call` node under `func_node`'s body is a bare
    `self.<attr>.append(...)` -- the manual-callback-list hallmark's
    "register" signal (T-0605), searched anywhere in the method (not just
    a single top-level statement, unlike the delegate/translate checks)."""

    def _walk(n: Node) -> bool:
        if n.type == "call":
            func = _child(n, "function")
            if (
                func is not None
                and func.type == "attribute"
                and _node_text(func) == f"self.{attr}.append"
            ):
                return True
        return any(_walk(c) for c in n.children)

    body = _child(func_node, "body")
    return body is not None and _walk(body)


def _method_notifies_from(func_node: Node, attr: str) -> bool:
    """Whether `func_node`'s body contains a `for <var> in self.<attr>:`
    loop whose body calls `<var>` itself or a method on `<var>` -- the
    manual-callback-list hallmark's "notify" signal (T-0605)."""

    def _walk(n: Node) -> bool:
        if n.type == "for_statement":
            right = _child(n, "right")
            if right is not None and _node_text(right) == f"self.{attr}":
                left = _child(n, "left")
                loop_var = _node_text(left) if left is not None else None
                loop_body = _child(n, "body")
                if (
                    loop_var
                    and loop_body is not None
                    and _calls_var(loop_body, loop_var)
                ):
                    return True
        return any(_walk(c) for c in n.children)

    body = _child(func_node, "body")
    return body is not None and _walk(body)


def _calls_var(node: Node, var: str) -> bool:
    """Whether `node`'s subtree contains a `call` whose callee is the bare
    identifier `var` (`var(...)`) or an attribute access rooted at `var`
    (`var.notify(...)`) -- either shape counts as "invoking" the loop
    variable for `_method_notifies_from`'s purposes (T-0605)."""
    for c in node.children:
        if c.type == "call":
            func = _child(c, "function")
            if func is not None:
                text = _node_text(func)
                if text == var or text.startswith(f"{var}."):
                    return True
        if _calls_var(c, var):
            return True
    return False


# frob:ticket T-0972
# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_manual_callback_list_recommends_observer  # noqa: E501
def _check_manual_callback_list(
    tree: object, rel: str, out: list[ArchSuggestion]
) -> None:
    """HALLMARK->PATTERN (T-0605): a class that initializes `self.<attr> =
    []` in `__init__`, has a DISTINCT method that appends to it, and a
    DISTINCT method that iterates it calling each element recommends
    Observer -- the register/notify shape a hand-rolled callback list
    always has. Any one or two of the three facts alone (a plain list
    attribute with only appends, or an iterate-and-call loop over a list
    nothing ever appends to) is ordinary list usage and must not fire."""
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
        # frob:waive PERF004 reason="_empty_list_attrs(init) is this loop's own per-class distinct set, not a shared re-sort"  # noqa: E501
        for attr in sorted(_empty_list_attrs(init)):
            appenders = [
                m for m in methods if m is not init and _method_appends_to(m, attr)
            ]
            notifiers = [
                m for m in methods if m is not init and _method_notifies_from(m, attr)
            ]
            if not appenders or not notifiers:
                continue
            name_node = _child(c, "name")
            cname = _node_text(name_node) if name_node else "?"
            subject = f"class `{cname}` manages `self.{attr}` via append+notify-loop"
            _emit(
                "manual-callback-list",
                "pattern-recommendation",
                rel,
                c.start_point[0] + 1,
                subject,
                out,
            )


def _is_trivial_getter(func_node: Node) -> bool:
    """Whether `func_node` is a bare `def f(self): return self.<attr>`
    (exactly one parameter, `self`, and a single-statement body that
    returns an attribute of `self` with no computation) -- the anemic-
    domain-model hallmark's "getter" half (T-0605)."""
    if _init_params(func_node):
        return False
    stmts = _method_body_stmts(func_node)
    if len(stmts) != 1 or stmts[0].type != "return_statement":
        return False
    val = stmts[0].named_children[0] if stmts[0].named_children else None
    if val is None or val.type != "attribute":
        return False
    obj = _child(val, "object")
    return obj is not None and _node_text(obj) == "self"


def _is_trivial_setter(func_node: Node) -> bool:
    """Whether `func_node` is a bare `def f(self, x): self.<attr> = x`
    (exactly one non-`self` parameter, single-statement body that assigns
    that exact parameter straight onto a `self.<attr>` with no
    computation) -- the anemic-domain-model hallmark's "setter" half
    (T-0605)."""
    params = _init_params(func_node)
    if len(params) != 1 or params[0].type != "identifier":
        return False
    param_name = _node_text(params[0])
    stmts = _method_body_stmts(func_node)
    if len(stmts) != 1:
        return False
    stmt = stmts[0]
    if stmt.type == "expression_statement":
        stmt = stmt.named_children[0] if stmt.named_children else stmt
    if stmt is None or stmt.type != "assignment":
        return False
    target = _child(stmt, "left")
    value = _child(stmt, "right")
    if target is None or value is None:
        return False
    if target.type != "attribute" or value.type != "identifier":
        return False
    obj = _child(target, "object")
    return (
        obj is not None
        and _node_text(obj) == "self"
        and _node_text(value) == param_name
    )


# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_anemic_accessors_recommends_move_behavior  # noqa: E501
def _check_anemic_accessors(tree: object, rel: str, out: list[ArchSuggestion]) -> None:
    """ANTI-PATTERN->ESCAPE (T-0605): a class with >=3 non-`__init__`,
    non-dunder methods where EVERY one is a trivial getter or setter (no
    real computation anywhere) recommends moving behavior onto the class
    (the anemic-domain-model escape). A single method with any real logic
    (a conditional, a loop, a computed expression, multiple statements)
    disqualifies the whole class -- this must never fire on a class that
    does real work alongside a few accessors."""
    t: Tree = cast("Tree", tree)
    for c in t.root_node.children:
        if c.type != "class_definition":
            continue
        body = _child(c, "body")
        if body is None:
            continue
        methods = [m for m in body.named_children if m.type == "function_definition"]
        candidates = []
        for m in methods:
            name_node = _child(m, "name")
            mname = _node_text(name_node) if name_node else ""
            if mname == "__init__" or mname.startswith("__"):
                continue
            candidates.append(m)
        if len(candidates) < _MIN_ANEMIC_ACCESSORS:
            continue
        if not all(_is_trivial_getter(m) or _is_trivial_setter(m) for m in candidates):
            continue
        name_node = _child(c, "name")
        cname = _node_text(name_node) if name_node else "?"
        subject = f"class `{cname}` ({len(candidates)} trivial accessor methods)"
        _emit(
            "anemic-accessors",
            "anti-pattern-escape",
            rel,
            c.start_point[0] + 1,
            subject,
            out,
        )


# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_dataclass_boilerplate_recommends_dataclass  # noqa: E501
def _check_dataclass_boilerplate(
    tree: object, rel: str, out: list[ArchSuggestion]
) -> None:
    """HALLMARK->PATTERN (T-0849): a plain, undecorated class whose ONLY
    method is `__init__`, itself doing nothing but `self.<attr> = <param>`
    assignments (attr name identical to the matching parameter, no
    computation) for >=3 parameters, recommends `@dataclass` -- the
    "hand-written value holder" hallmark, distinct from `anemic-accessors`
    (which requires >=3 *other* trivial getter/setter methods; a class
    with ONLY `__init__` and no accessors never satisfies that detector's
    floor, so the two never double-fire on the same class). A decorated
    class (already `@dataclass`, `@attr.s`, etc.) is a `decorated_
    definition` node, not a bare `class_definition`, so it is structurally
    excluded before any body inspection is even attempted -- the same
    filter every other module-level detector in this file relies on. Any
    extra method beyond `__init__`, a `*args`/`**kwargs` parameter, a
    docstring (an extra body statement breaking the 1:1 stmt<->param
    count), or an init statement that is not a bare `self.<name> = <name>`
    assignment disqualifies the whole class -- silence over a guessed
    match. A `@property`/`@staticmethod`/`@classmethod`/`@cached_property`
    (or any other decorated) method is a `decorated_definition` node, NOT
    a `function_definition` -- the class-body member scan below counts
    BOTH node types so a decorated extra method still disqualifies the
    class instead of silently vanishing from the count (reviewer round 1,
    T-0849: an `__init__`-only-looking class with an extra `@property`
    method was wrongly firing before this fix)."""
    t: Tree = cast("Tree", tree)
    for c in t.root_node.children:
        if c.type != "class_definition":
            continue
        param_names = _dataclass_boilerplate_init_params(c)
        if param_names is None:
            continue
        name_node = _child(c, "name")
        cname = _node_text(name_node) if name_node else "?"
        subject = f"class `{cname}` ({len(param_names)}-field value holder)"
        _emit(
            "dataclass-boilerplate",
            "pattern-recommendation",
            rel,
            c.start_point[0] + 1,
            subject,
            out,
        )


# frob:ticket T-0976
def _dataclass_boilerplate_init_params(c: Node) -> list[str] | None:
    """`class_definition` node `c`'s field names if it matches the
    dataclass-boilerplate hallmark (an `__init__`-only body doing nothing
    but 1:1 `self.<attr> = <param>` assignments for >=3 params), else
    `None` -- any disqualifying shape (extra members, non-bare-assignment
    statements, a splat param, an attr/param name mismatch) fails closed
    to `None` rather than a guessed match, per `_check_dataclass_
    boilerplate`'s docstring."""
    init, param_names = _sole_init_with_min_params(c)
    if init is None or param_names is None:
        return None
    stmts = _method_body_stmts(init)
    if len(stmts) != len(param_names):
        return None
    if not _stmts_are_1to1_self_assignments(stmts, param_names):
        return None
    return param_names


# frob:ticket T-0976
def _sole_init_with_min_params(c: Node) -> tuple[Node | None, list[str] | None]:
    """`(init_node, param_names)` if `class_definition` `c`'s ONLY member
    is a bare (undecorated) `__init__` with `>= _MIN_DATACLASS_FIELDS`
    plain (non-splat) parameters, else `(None, None)` -- the shape-check
    half of `_dataclass_boilerplate_init_params`, split out from the
    body-statement validation half."""
    body = _child(c, "body")
    if body is None:
        return None, None
    members = [
        m
        for m in body.named_children
        if m.type in ("function_definition", "decorated_definition")
    ]
    if len(members) != 1:
        return None, None
    init = members[0]
    if init.type != "function_definition":
        return None, None
    name_node = _child(init, "name")
    if name_node is None or _node_text(name_node) != "__init__":
        return None, None
    params = _init_params(init)
    if len(params) < _MIN_DATACLASS_FIELDS:
        return None, None
    param_names: list[str] = []
    for p in params:
        if p.type in ("list_splat_pattern", "dictionary_splat_pattern"):
            return None, None
        param_names.append(_node_text(p).split("=")[0].split(":")[0].strip())
    if not param_names:
        return None, None
    return init, param_names


# frob:ticket T-0976
def _stmts_are_1to1_self_assignments(stmts: list[Node], param_names: list[str]) -> bool:
    """`True` if every statement in `stmts` is a bare `self.<attr> =
    <param>` assignment (attr name identical to a name in `param_names`)
    and every name in `param_names` is assigned exactly once -- the body-
    statement validation half of `_dataclass_boilerplate_init_params`."""
    # frob:ticket T-0972
    # PERF001: build the membership set once, outside the per-statement
    # loop below, instead of testing `in` against the `param_names` list
    # on every iteration.
    param_name_set = set(param_names)
    assigned: set[str] = set()
    for stmt in stmts:
        if stmt.type == "assignment":
            assign: Node | None = stmt
        elif stmt.type == "expression_statement":
            assign = stmt.named_children[0] if stmt.named_children else None
        else:
            return False
        if assign is None or assign.type != "assignment":
            return False
        target = _child(assign, "left")
        value = _child(assign, "right")
        if target is None or value is None:
            return False
        if target.type != "attribute" or value.type != "identifier":
            return False
        obj = _child(target, "object")
        if obj is None or _node_text(obj) != "self":
            return False
        attr_node = _child(target, "attribute")
        attr_name = _node_text(attr_node) if attr_node is not None else None
        value_name = _node_text(value)
        if (
            attr_name is None
            or attr_name != value_name
            or value_name not in param_name_set
        ):
            return False
        assigned.add(attr_name)
    return len(assigned) == len(param_names)


# frob:ticket T-0976
def _is_manual_decorator_wrap(c: Node, nxt: Node | None) -> bool:
    """`True` if module-level `function_definition` `c` is immediately
    followed by `nxt`, a bare `f = wrapper(f)` reassignment whose wrapper
    call's argument list contains a bare identifier matching `c`'s own
    name -- the manual-decorator-wrap hallmark `_check_manual_decorator_
    wrap` counts occurrences of."""
    name_node = _child(c, "name")
    fname = _node_text(name_node) if name_node else ""
    if not fname or nxt is None:
        return False
    if nxt.type == "assignment":
        assign: Node | None = nxt
    elif nxt.type == "expression_statement":
        assign = nxt.named_children[0] if nxt.named_children else None
    else:
        return False
    if assign is None or assign.type != "assignment":
        return False
    target = _child(assign, "left")
    value = _child(assign, "right")
    if target is None or value is None:
        return False
    if target.type != "identifier" or _node_text(target) != fname:
        return False
    if value.type != "call":
        return False
    args = _child(value, "arguments")
    if args is None:
        return False
    return any(
        a.type == "identifier" and _node_text(a) == fname for a in args.named_children
    )


# frob:tests tests/unit/test_arch.py::TestPatternRecommender.test_manual_decorator_wrap_recommends_decorator_syntax  # noqa: E501
def _check_manual_decorator_wrap(
    tree: object, rel: str, out: list[ArchSuggestion]
) -> None:
    """HALLMARK->PATTERN (T-0849): 3+ module-level `def f(...): ...`
    definitions each immediately followed by a bare `f = wrapper(f)`
    reassignment (the wrapper call's argument list contains a bare
    identifier matching `f`'s own name somewhere) recommend `@wrapper`
    decorator syntax instead of the manual reassignment. Module-level
    statement adjacency only, mirroring `scattered-construction`'s scope
    choice of a simple, high-precision structural walk over a fuller
    dataflow trace; a class-method equivalent is left for a future ticket
    if the same shape is observed inside class bodies. A function that is
    already `@decorated` is a `decorated_definition` node, not a bare
    `function_definition`, so it never enters this walk to begin with --
    the reassignment shape and decorator syntax are structurally
    mutually exclusive here, never double-counted."""
    t: Tree = cast("Tree", tree)
    children = list(t.root_node.children)
    hits: list[Node] = [
        c
        for i, c in enumerate(children)
        if c.type == "function_definition"
        and _is_manual_decorator_wrap(
            c, children[i + 1] if i + 1 < len(children) else None
        )
    ]
    if len(hits) < _MIN_MANUAL_DECORATOR_WRAPS:
        return
    subject = f"{len(hits)} functions manually re-wrapped via reassignment"
    _emit(
        "manual-decorator-wrap",
        "pattern-recommendation",
        rel,
        hits[0].start_point[0] + 1,
        subject,
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
