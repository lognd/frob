"""OCP checks (T-0330's SOLID catalog, ARCH1xx family; T-0617): type-dispatch
smell and non-exhaustive enum match, the Open/Closed half of the catalog.

type-dispatch smell: an N+ arm `isinstance`/`type ==` chain on one variable
is the textbook OCP violation -- adding a new case means editing this
function instead of adding a new type. T-0332's design-pattern recommender
(`frob.arch._patterns`) already detects this EXACT shape as the `type-switch`
hallmark and recommends Strategy; per the ticket's own reuse mandate ("one
detector, two outputs"), this module does NOT re-walk the tree or
re-implement the isinstance-chain match -- it calls
`frob.arch._patterns.iter_type_switch_chains` (the shared generator T-0617
factored out of that detector) and reads the identical signal as an OCP
smell instead of a pattern recommendation.

non-exhaustive enum match: a `match`/`case` over a variable statically tied
to a locally-defined `Enum` subclass, with no wildcard/capture default arm,
that does not cover every member of that enum. PRECISION DISCIPLINE (fail
toward silence, per the ticket): this only fires when the enum class is
defined in the SAME file (a base class name matching a known Enum-family
name) and EVERY case pattern is a plain `EnumClass.MEMBER` value pattern (or
a `|`-union of same) naming that exact class -- any other pattern shape
(sequence/mapping/class pattern with args, a qualifier naming some other
class, an unresolvable subject) makes the match's exhaustiveness
unverifiable from this file alone, and the check silently skips it rather
than risk a false positive.
"""

from __future__ import annotations

from typing import cast

from tree_sitter import Node, Tree

from frob.arch._models import ArchSuggestion
from frob.arch._patterns import iter_type_switch_chains
from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text

#: Base-class names (as written in source, both bare and `enum.`-qualified)
#: that mark a class definition as a closed enum-family type whose member
#: set is knowable by reading its own class body.
_ENUM_BASE_NAMES = frozenset(
    {
        "Enum",
        "IntEnum",
        "StrEnum",
        "Flag",
        "IntFlag",
        "enum.Enum",
        "enum.IntEnum",
        "enum.StrEnum",
        "enum.Flag",
        "enum.IntFlag",
    }
)


def _enclosing_qualname(node: Node, rel: str) -> str:
    """`path::Class.method`/`path::function`/bare `path` symref for `node`'s
    innermost enclosing function/class chain, walking parents (T-0289's
    symref shape, so a future ARCH1xx gate can bind a `frob:waive` to the
    exact function the way `ARCH001` already does for long-function)."""
    parts: list[str] = []
    n: Node | None = node.parent
    while n is not None:
        if n.type in ("function_definition", "class_definition"):
            name_node = _child(n, "name")
            if name_node is not None:
                parts.append(_node_text(name_node))
        n = n.parent
    parts.reverse()
    return f"{rel}::{'.'.join(parts)}" if parts else rel


# frob:tests tests/unit/test_arch_ocp.py::TestTypeDispatchSmell.test_isinstance_chain_flags_ocp_violation  # noqa: E501
def _check_type_dispatch_smell(
    tree: object, rel: str, out: list[ArchSuggestion]
) -> None:
    """OCP: an elif chain of >=3 `isinstance(x, T)` arms on the same `x`
    means a new type requires editing this function instead of adding a
    new type -- the classic Open/Closed violation. Reuses
    `frob.arch._patterns.iter_type_switch_chains` (T-0332's `type-switch`
    hallmark detector) rather than re-walking the tree; see this module's
    docstring."""
    for if_stmt, variable, n_arms in iter_type_switch_chains(tree):
        out.append(
            ArchSuggestion(
                file=rel,
                line=if_stmt.start_point[0] + 1,
                category="type-dispatch-smell",
                severity="warning",
                message=(
                    f"{n_arms}-arm isinstance chain on `{variable}` violates OCP: "
                    "adding a new type means editing this function"
                ),
                detail=(
                    "give each type its own class implementing a shared method; "
                    "replace the isinstance chain with one polymorphic call"
                ),
                symref=_enclosing_qualname(if_stmt, rel),
                metric=n_arms,
            )
        )


def _enum_member_names(class_node: Node) -> set[str] | None:
    """The set of member names a `class_node` enum defines (top-level
    `NAME = ...` assignments in its body), or `None` if `class_node` is not
    a locally-defined Enum-family class (T-0617's fail-toward-silence
    gate)."""
    superclasses = _child(class_node, "superclasses")
    if superclasses is None:
        return None
    bases = [_node_text(a) for a in superclasses.named_children]
    if not any(b in _ENUM_BASE_NAMES for b in bases):
        return None
    body = _child(class_node, "body")
    if body is None:
        return set()
    members: set[str] = set()
    for c in body.named_children:
        if c.type != "assignment":
            continue
        left = _child(c, "left")
        if left is not None and left.type == "identifier":
            name = _node_text(left)
            if not name.startswith("_"):
                members.add(name)
    return members


def _collect_enum_classes(root: Node) -> dict[str, set[str]]:
    """Every locally-defined Enum-family class in `root`'s subtree, mapped
    to its member-name set (T-0617's resolvability corpus for non-
    exhaustive enum match)."""
    found: dict[str, set[str]] = {}
    for c in root.children:
        if c.type == "class_definition":
            name_node = _child(c, "name")
            if name_node is not None:
                members = _enum_member_names(c)
                if members is not None:
                    found[_node_text(name_node)] = members
        found.update(_collect_enum_classes(c))
    return found


def _find_match_statements(node: Node) -> list[Node]:
    """Every `match_statement` anywhere under `node`'s subtree."""
    found: list[Node] = []
    for c in node.children:
        if c.type == "match_statement":
            found.append(c)
        found.extend(_find_match_statements(c))
    return found


def _case_clauses(match_stmt: Node) -> list[Node]:
    """The `case_clause` children of a `match_statement`'s block."""
    block = _child(match_stmt, "body")
    if block is None:
        return []
    return [c for c in block.children if c.type == "case_clause"]


def _clause_pattern(clause: Node) -> Node | None:
    """The actual pattern node (`dotted_name`/`_`/`union_pattern`) inside a
    `case_clause` -- tree-sitter-python wraps it as an unnamed
    `case_pattern` child rather than a directly-named field, so `_child`
    cannot reach it directly; this unwraps one level."""
    for c in clause.children:
        if c.type == "case_pattern":
            named = c.named_children
            return named[0] if named else None
    return None


def _flatten_value_pattern_members(pattern: Node, enum_class: str) -> set[str] | None:
    """Flatten one `case_pattern` (a plain `EnumClass.MEMBER` value pattern,
    or a `|`-union of same) into the set of `enum_class` member names it
    covers, or `None` if any leaf is not a bare-dotted value pattern
    naming EXACTLY `enum_class` (a sequence/mapping/class-with-args
    pattern, or a qualifier naming some other class) -- T-0617's
    fail-toward-silence: one unrecognized leaf makes the whole match
    statement's exhaustiveness unverifiable, not partially verifiable."""
    if pattern.type == "union_pattern":
        members: set[str] = set()
        for child in pattern.named_children:
            leaf = _flatten_value_pattern_members(child, enum_class)
            if leaf is None:
                return None
            members |= leaf
        return members
    if pattern.type == "dotted_name":
        idents = [c for c in pattern.children if c.type == "identifier"]
        if len(idents) != 2:
            # A bare single-identifier "dotted_name" is a capture pattern
            # (matches anything), handled by `_has_catchall_arm`, not here.
            return None
        qualifier, member = _node_text(idents[0]), _node_text(idents[1])
        if qualifier != enum_class:
            return None
        return {member}
    return None


def _has_catchall_arm(case_clauses: list[Node]) -> bool:
    """True if any `case_clause` is an unconditional wildcard (`case _:`) or
    bare-name capture pattern (`case other:`) -- either acts as a default
    arm, so the match is exhaustive by construction regardless of which
    enum members are named explicitly. A guarded arm (`case _ if cond:`)
    is NOT unconditional and does not count (T-0617 precision)."""
    for clause in case_clauses:
        if _child(clause, "guard") is not None:
            continue
        pattern = _clause_pattern(clause)
        if pattern is None:
            continue
        if pattern.type == "_":
            return True
        if pattern.type == "dotted_name":
            idents = [c for c in pattern.children if c.type == "identifier"]
            if len(idents) == 1:
                return True
    return False


def _resolve_matched_enum(
    case_clauses: list[Node], enum_classes: dict[str, set[str]]
) -> str | None:
    """The single known Enum-family class every non-wildcard `case_clause`
    pattern's qualifier names, or `None` if the case patterns disagree, name
    an unknown class, or aren't all bare-dotted value patterns -- T-0617's
    resolvability gate for `non-exhaustive-enum-match`."""
    qualifiers: set[str] = set()
    for clause in case_clauses:
        pattern = _clause_pattern(clause)
        if pattern is None:
            return None
        for leaf in _iter_pattern_leaves(pattern):
            if leaf.type == "_":
                continue
            if leaf.type != "dotted_name":
                return None
            idents = [c for c in leaf.children if c.type == "identifier"]
            if len(idents) == 1:
                continue  # capture/wildcard arm, not a value pattern
            if len(idents) != 2:
                return None
            qualifiers.add(_node_text(idents[0]))
    if len(qualifiers) != 1:
        return None
    (enum_class,) = qualifiers
    if enum_class not in enum_classes:
        return None
    return enum_class


def _iter_pattern_leaves(pattern: Node) -> list[Node]:
    """`pattern` itself, or each side of a `union_pattern`, flattened one
    level (case patterns here are never nested unions of unions)."""
    if pattern.type == "union_pattern":
        return list(pattern.named_children)
    return [pattern]


# frob:tests tests/unit/test_arch_ocp.py::TestNonExhaustiveEnumMatch.test_missing_member_flagged  # noqa: E501
def _check_non_exhaustive_enum_match(
    tree: object, rel: str, out: list[ArchSuggestion]
) -> None:
    """OCP: a `match`/`case` over a variable statically tied to a locally-
    defined Enum-family class, with no wildcard/capture default, that omits
    at least one of that enum's members. Fails toward silence (T-0617):
    skips whenever the matched type or any case pattern is not resolvable
    from this file alone (see module docstring)."""
    t: Tree = cast("Tree", tree)
    enum_classes = _collect_enum_classes(t.root_node)
    if not enum_classes:
        return
    for match_stmt in _find_match_statements(t.root_node):
        clauses = _case_clauses(match_stmt)
        if not clauses:
            continue
        if _has_catchall_arm(clauses):
            continue
        enum_class = _resolve_matched_enum(clauses, enum_classes)
        if enum_class is None:
            continue
        covered: set[str] = set()
        skip = False
        for clause in clauses:
            pattern = _clause_pattern(clause)
            if pattern is None:
                skip = True
                break
            members = _flatten_value_pattern_members(pattern, enum_class)
            if members is None:
                skip = True
                break
            covered |= members
        if skip:
            continue
        missing = enum_classes[enum_class] - covered
        if not missing:
            continue
        out.append(
            ArchSuggestion(
                file=rel,
                line=match_stmt.start_point[0] + 1,
                category="non-exhaustive-enum-match",
                severity="warning",
                message=(
                    f"match on `{enum_class}` is missing "
                    f"{sorted(missing)} and has no wildcard/default arm"
                ),
                detail=(
                    "add a `case` for every remaining member, or an explicit "
                    "`case _:` if falling through is genuinely intended"
                ),
                symref=_enclosing_qualname(match_stmt, rel),
                metric=len(missing),
            )
        )
