"""Cross-file abstraction-opportunity detection for python (extracted from
`frob.arch._python` by T-1195, LARGE001 residue split): signature
extraction, the false-positive-family exclusions (dispatch tables,
per-language parity, check/gate/tool-result registries), body-similarity
near-duplicate clustering, and the top-level `_check_abstraction_
opportunities` entry point `frob.arch` calls (docs/modules/arch.md's
Python abstraction-opportunity rule).
"""

# frob:waive INV006 reason="split-carried-prose (T-0585 lineage): every 'only' claim \
# in this file's docstrings/comments is design-rationale prose describing \
# already-implemented internal behavior moved verbatim from frob.arch._python by \
# T-1195, not a new cross-module contract needing its own tracked invariant"

from __future__ import annotations

import difflib
import re
from collections import defaultdict
from typing import cast

from tree_sitter import Node, Tree

from frob.arch._models import ArchSuggestion
from frob.arch._python import (
    _iter_normalized_functions,
    _iter_py_functions,
    _py_build_module,
)
from frob.dup._legacy_py import _collect_locals_py, _serialize_py_body
from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text


# frob:ticket T-0632
# frob:ticket T-1195
def _extract_signatures(
    tree: object,
    rel: str,
) -> list[tuple[str, str, tuple[str, ...], str, str]]:
    """`(rel, func_name, param_types, return_type, body_fingerprint)` for
    every python function carrying at least one annotated parameter or an
    annotated return type.

    T-0632: `func_name`/`param_types`/`return_type` are read off
    `NormalizedModule` (`_iter_normalized_functions`, the same shape
    `_check_long_functions`/`_check_deep_nesting` already consume) instead
    of a bespoke raw-tree param/return walk -- `_py_param_types` (the prior
    ad-hoc walk) is gone, folded into the shared `NormalizedParam.type`
    field every adapter already fills in identically. `body_fingerprint`
    stays on the raw AST (`_body_fingerprint`, paired to its normalized
    function by `(class_prefix, name, line)`, a stable per-file key since
    two functions cannot share a definition line): T-0370's alpha-renaming
    (`frob.dup._legacy_py`'s `_collect_locals_py`/`_serialize_py_body`)
    needs the full raw parse tree to walk/rename every local, and
    `NormalizedFunction` deliberately carries no raw-body projection for
    it -- adding one would just duplicate the dup-scanner's own
    local-collection/serialization logic onto the model instead of
    replacing a raw walk with one, so this one piece is a reasoned
    decision to stay raw, not an oversight."""
    t: Tree = cast("Tree", tree)
    module = _py_build_module(tree, rel)
    fingerprints: dict[tuple[str, str, int], str] = {
        (prefix, fname, func.start_point[0] + 1): _body_fingerprint(func)
        for func, prefix, fname in _iter_py_functions(t.root_node)
    }
    results: list[tuple[str, str, tuple[str, ...], str, str]] = []
    for func, prefix in _iter_normalized_functions(module):
        param_types = [p.type for p in func.params if p.type]
        ret = func.return_type or ""
        if param_types or ret:
            body_fp = fingerprints.get((prefix, func.name, func.line), "")
            results.append((rel, func.name, tuple(param_types), ret, body_fp))
    return results


# frob:ticket T-1195
def _body_fingerprint(func: Node) -> str:
    """Normalized token serialization of `func`'s body, or `""` if it has
    none (T-0370, reused for abstraction-opportunity body-similarity)."""
    body = _child(func, "body")
    if body is None:
        return ""
    locals_ = _collect_locals_py(func)
    return _serialize_py_body(body, locals_)


# frob:ticket T-1195
_DISPATCH_CONTAINER_TYPES = frozenset({"list", "set", "tuple"})


# frob:ticket T-1195
def _collect_dispatch_refs_from_call(call: Node, out: set[str]) -> None:
    """Collect dispatch-like identifier refs from one `call` node's own
    callee and argument list (extracted from `_collect_dispatch_refs` to
    cut nesting, T-0394; see that function's docstring for the shapes that
    count)."""
    func = _child(call, "function")
    if func is not None and func.type == "identifier":
        out.add(_node_text(func))
    args = _child(call, "arguments")
    if args is None:
        return
    for a in args.named_children:
        if a.type == "identifier":
            out.add(_node_text(a))
        elif a.type == "keyword_argument":
            val = _child(a, "value")
            if val is not None and val.type == "identifier":
                out.add(_node_text(val))


# frob:ticket T-1195
def _collect_dispatch_refs(node: Node, out: set[str]) -> None:
    """Collect every identifier used in a DISPATCH-LIKE syntactic position
    under `node`, into `out` (T-0360, reviewer-required fix).

    Deliberately structural, not textual: a plain mention of a name (an
    import, a docstring, a bare `__all__` string) proves nothing about
    dispatch -- a re-export list or a test file that imports and asserts
    against three unrelated functions mentions each name too, and a purely
    textual "appears >=2 times" signal cannot tell those apart from a real
    command table. Only these tree-sitter shapes count as "this name is
    being dispatched from here":

    - the callee of a `call` (`name(...)`) -- an `elif`/`match` branch
      calling a handler, or a direct dispatch call;
    - a positional or keyword ARGUMENT of a `call` (`register(name)`,
      `table.append(name)`, `dispatch(cmd, handler=name)`) -- a
      registration call;
    - a value inside a `dictionary` literal's `pair` (`{"scan": name}`) --
      a command table;
    - an element of a `list`/`set`/`tuple` literal (`[name_a, name_b]`) --
      a dispatch table built as a sequence.

    A bare `from mod import name` or `name` sitting in an `__all__` list of
    STRING literals (not identifiers) matches none of these and is
    correctly not counted.
    """
    for c in node.children:
        if c.type == "call":
            _collect_dispatch_refs_from_call(c, out)
        elif c.type == "dictionary":
            _collect_dispatch_refs_from_dict(c, out)
        elif c.type in _DISPATCH_CONTAINER_TYPES:
            _collect_dispatch_refs_from_container(c, out)
        _collect_dispatch_refs(c, out)


# frob:ticket T-1195
def _collect_dispatch_refs_from_dict(dictionary: Node, out: set[str]) -> None:
    """Collect dispatch-like identifier refs from one `dictionary`
    literal's pair values (extracted from `_collect_dispatch_refs` to cut
    nesting, T-0394)."""
    for pair in dictionary.named_children:
        if pair.type == "pair":
            val = _child(pair, "value")
            if val is not None and val.type == "identifier":
                out.add(_node_text(val))


# frob:ticket T-1195
def _collect_dispatch_refs_from_container(container: Node, out: set[str]) -> None:
    """Collect dispatch-like identifier refs from one `list`/`set`/`tuple`
    literal's elements (extracted from `_collect_dispatch_refs` to cut
    nesting, T-0394)."""
    for el in container.named_children:
        if el.type == "identifier":
            out.add(_node_text(el))


# frob:ticket T-1195
def _collect_file_dispatch_refs(tree: object) -> set[str]:
    """Every identifier name referenced in a dispatch-like context
    (`_collect_dispatch_refs`) anywhere in a parsed python file's tree.

    Public so `frob.arch` (the caller building the cross-file corpus) can
    decide, per file, whether to include it -- callers exclude
    `__init__.py` re-export modules and test files (`is_test_file`) before
    this function ever sees them, so this function itself stays a pure
    structural extraction with no naming/path policy baked in."""
    t: Tree = cast("Tree", tree)
    refs: set[str] = set()
    _collect_dispatch_refs(t.root_node, refs)
    return refs


# frob:ticket T-1195
def _is_dispatch_family(
    members: list[tuple[str, str]],
    all_dispatch_refs: dict[str, set[str]],
) -> bool:
    """Whether a shared-signature `members` group (T-0360) is an intentional
    dispatch/validator family rather than an accidental duplication.

    A same-signature group is NOT a missing abstraction when its members are
    each reachable from a common site -- a command table, a validator
    runner, an `elif` dispatch chain -- because the shared signature IS the
    contract that lets that site call them uniformly. `all_dispatch_refs`
    (built by `frob.arch` from `_collect_file_dispatch_refs`, already
    excluding `__init__.py` and test files) maps each eligible file to the
    set of names it references in a dispatch-like structural position
    (call callee, call argument, dict value, list/set/tuple element) --
    NOT every textual mention, so a re-export list or a test's assertion
    calls cannot masquerade as a dispatch site (reviewer-flagged false
    suppression, fixed here). Two members are "linked" if some single
    eligible file's ref-set contains both their names. A large group can
    legitimately be served by more than one such site (e.g. two separate
    command tables that each dispatch a handful of same-signature
    handlers) -- so the group is treated as an intentional family when
    every member is linked to at least one sibling, i.e. no member sits
    completely outside any dispatch site. A group with a member that is
    never linked to any other member has no such site for that member and
    still flags as a real opportunity.
    """
    names = [fname for _, fname in members]
    if len(names) < 2:
        return False
    linked: set[int] = set()
    for refs in all_dispatch_refs.values():
        referenced = [i for i, name in enumerate(names) if name in refs]
        if len(referenced) >= 2:
            linked.update(referenced)
    return len(linked) == len(names)


# T-1068: the fixed, small set of per-language-adapter name tags a same-
# signature abstraction-opportunity group's members can carry -- mirrors
# frob.arch's own per-language walker convention (`_py_*`/`_rust_*`/
# `_kt_*`/`_ts_*`/`_cpp_*`, e.g. `arch/_rust.py`'s `_rust_build_module`/
# `_kt_build_module`/`_ts_build_module` trio) rather than any project-wide
# naming scheme, so this stays a narrow, reviewable allowlist, not a
# guess at what "looks like a language tag".
# frob:ticket T-1195
_LANGUAGE_TAGS = ("py", "rust", "kt", "ts", "cpp")

#: T-1181 (refiled from the T-1083 disposition, w20-arch a8085d7f): a
#: same-signature parity family sometimes spells its per-language segment
#: out in FULL (`python`/`typescript`/`kotlin`/`cplusplus`) rather than
#: `_LANGUAGE_TAGS`' short form (`collect_python_tests`/
#: `collect_typescript_tests`/... in `frob.testing._collect*`) -- the short
#: form alone never matches `python` as a whole underscore-delimited
#: segment (it is not a substring of any short tag), so these genuinely-
#: parity families fell through uncaught and polluted the abstraction-
#: opportunity count as false positives. This maps each long form to its
#: canonical short tag so `_language_tag` normalizes both spellings to the
#: SAME identity before the distinctness check in
#: `_is_language_parity_family` runs -- `rust`/`cpp` have no separate long
#: form in this codebase's own naming convention, so they are omitted
#: rather than guessed at.
# frob:ticket T-1195
_LANGUAGE_TAG_SYNONYMS = {
    "python": "py",
    "typescript": "ts",
    "kotlin": "kt",
    "cplusplus": "cpp",
}

#: Matches a language tag (short OR long form, `_LANGUAGE_TAG_SYNONYMS`) as
#: an underscore-delimited token anywhere in a function name
#: (`_LANGUAGE_TAG_RE.search("_kt_this_field_name")` -> `"kt"`) --
#: underscore-delimited on BOTH sides so `_ts_...`/`..._ts_...` match but
#: an incidental substring like `results_summary` (no underscore before
#: `ts`) does not. This is the STRUCTURAL rigor T-0360's own
#: `_is_dispatch_family` docstring calls out (no raw text proximity): the
#: tag must occupy a real name-segment boundary, not just appear somewhere
#: in the string. Long forms are listed before short forms in the
#: alternation so a longer match (e.g. `python`) is preferred where both
#: could otherwise apply.
# frob:ticket T-1195
_LANGUAGE_TAG_RE = re.compile(
    r"(?:^|_)(?P<tag>"
    + "|".join((*_LANGUAGE_TAG_SYNONYMS, *_LANGUAGE_TAGS))
    + r")(?:_|$)"
)


# frob:ticket T-1195
def _language_tag(fname: str) -> str | None:
    """The single language tag (T-1068 `_LANGUAGE_TAGS`, T-1181
    `_LANGUAGE_TAG_SYNONYMS`) `fname` carries as an underscore-delimited
    prefix/infix segment, normalized to its canonical short form (`python`
    and `py` both return `"py"`), or `None` when it carries none.
    `_LANGUAGE_TAG_RE.search` finds the FIRST such segment only -- good
    enough here since every real per-language walker/collector name in
    this codebase carries exactly one tag, never a name combining two."""
    m = _LANGUAGE_TAG_RE.search(fname)
    if not m:
        return None
    tag = m.group("tag")
    return _LANGUAGE_TAG_SYNONYMS.get(tag, tag)


# frob:ticket T-1195
def _is_language_parity_family(members: list[tuple[str, str]]) -> bool:
    """Whether a shared-signature `members` group (T-1068, filed from
    T-0393) is an intentional per-language-parity family rather than an
    accidental duplication: every member's name carries a language tag
    (`_language_tag`) AND every member carries a DIFFERENT tag from the
    fixed `_LANGUAGE_TAGS` set -- e.g. `_rust_build_module`/
    `_kt_build_module`/`_ts_build_module` each independently walking one
    language's own tree-sitter grammar to build the same
    `NormalizedModule` shape. This is NOT the T-0360 dispatch-table shape
    (`_is_dispatch_family`, no common call site is required here) but the
    same false-positive class: the shared signature is the point --
    `frob.lang.LanguageAdapter`'s per-language contract -- not a missing
    abstraction to extract.

    Distinctness is the load-bearing check: a group of 3 all-`_py_`-tagged
    helpers sharing a signature is NOT parity (three python functions
    happen to collide, exactly the accidental-duplication case this
    detector exists to catch) -- only genuine one-member-per-language
    spread is excluded. A group with even one untagged member (no
    recognized language segment at all) is never excluded either: with no
    tag to compare, "parity" cannot be established structurally, so the
    group falls through to the normal signature/body-similarity checks."""
    if len(members) < 2:
        return False
    tags = [_language_tag(fname) for _, fname in members]
    if any(tag is None for tag in tags):
        return False
    return len(set(tags)) == len(tags)


#: `frob.arch`'s own detector-registry naming convention (T-1112, filed
#: from T-1084): every `check_*` function across the package (`_python.py`,
#: `_rust.py`, `_typescript.py`, `_async_hazards.py`, and siblings) is a
#: detector plugged into the SAME `(NormalizedModule) -> list[ArchSuggestion]`
#: registry contract -- the arity mismatch is why a signature-shape check
#: alone cannot tell these apart from a real duplication (a handful of
#: `check_*` detectors take an extra param), so this is name-based, like
#: `_is_dispatch_family`/`_is_language_parity_family`'s own checks, never
#: raw text proximity. Measured empirically (T-1112) to also need each
#: family's own top-level `run_*_checks` aggregator (e.g. `_smells.py`'s
#: `run_smell_checks`, `_srp.py`'s `run_srp_checks`) alongside the bare
#: `check_*` detectors themselves -- an aggregator has the exact same
#: `(NormalizedModule) -> list[ArchSuggestion]` shape as the detectors it
#: calls (it just concatenates their results), so the same 27-member group
#: this ticket was filed to exclude is ~20 `check_*` detectors plus 7
#: `run_*_checks` aggregators, not `check_*` alone.
# frob:ticket T-1195
_CHECK_REGISTRY_NAME_RE = re.compile(r"^(check_[a-z_]+|run_[a-z_]+_checks)$")


# frob:ticket T-1195
def _is_check_registry_family(members: list[tuple[str, str]]) -> bool:
    """Whether a shared-signature `members` group (T-1112) is `frob.arch`'s
    own check-function registry rather than an accidental duplication:
    every member's bare name matches the package's `check_*` detector (or
    `run_*_checks` family-aggregator) convention (`_CHECK_REGISTRY_NAME_RE`).
    Structurally identical to `_is_dispatch_family`/`_is_language_parity_family`
    -- name/structure only, no raw text proximity -- but the discriminator
    here is a fixed project-wide naming convention rather than a
    dispatch-site lookup or a per-language tag set: `frob.arch`'s 27-member
    `(NormalizedModule) -> list[ArchSuggestion]` group (T-1084's triage) IS
    literally every `check_*` detector in the package plus each family's
    `run_*_checks` aggregator, the intentional common interface every
    detector module registers through, not duplicate logic to extract."""
    if len(members) < 2:
        return False
    return all(_CHECK_REGISTRY_NAME_RE.match(fname) for _, fname in members)


#: `frob.gates`'s own gate/rule-builder return-type convention (T-1141,
#: filed from T-1114 as the mirror of T-1112's `check_*` registry
#: exclusion): every gate function (`*_gate`) and every rule-builder
#: helper it dispatches to (`_tick001_duplicate_ids`, `_cov001`,
#: `_test006`, `_inv005`, and dozens of siblings across gates/__init__.py
#: and its `_*.py` split modules) returns one of these three shapes --
#: `Violation`, `list[Violation]`, or `tuple[Violation, ...]` -- because
#: `Violation` is `frob.gates`'s own domain type: nothing outside the
#: gates package constructs one. A shared return type built entirely from
#: `Violation`/collections of it is therefore the intentional common gate/
#: rule-builder contract this package registers every check through, the
#: same shape `_is_check_registry_family` already carves out for
#: `frob.arch`'s own `check_*`/`run_*_checks` convention -- not duplicate
#: logic, regardless of how many members happen to share it or what they
#: are individually named (a structural discriminator, mirroring
#: `_is_language_parity_family`'s per-language tag check, rather than a
#: name-pattern one like `_is_check_registry_family`'s, since gate/rule-
#: builder names do not share one fixed prefix/suffix convention the way
#: `check_*`/`run_*_checks` do).
# frob:ticket T-1195
_GATE_RULE_BUILDER_RETURN_TYPES = frozenset(
    {"Violation", "list[Violation]", "tuple[Violation, ...]"}
)


# frob:ticket T-1195
def _is_gate_rule_builder_family(ret: str) -> bool:
    """Whether a shared-signature group's return type `ret` (T-1141) is
    `frob.gates`'s own gate/rule-builder convention rather than an
    accidental duplication: `ret` is one of `_GATE_RULE_BUILDER_RETURN_
    TYPES`. Structural, not name-based -- see `_GATE_RULE_BUILDER_RETURN_
    TYPES`'s docstring for why a return-type check is the right
    discriminator for this family specifically."""
    return ret in _GATE_RULE_BUILDER_RETURN_TYPES


#: `frob.process`/`frob.check`'s own check-stage-runner return-type
#: convention (T-1144, filed from T-1124 as the mirror of T-1112's
#: `check_*` registry exclusion and T-1141's gate/rule-builder
#: exclusion): every check-stage runner/tool-result builder across
#: `src/frob/check/**`, `src/frob/process/parsers/**`, and the
#: individual arch/cycle/dup CLI runners returns `ToolResult` or
#: `ToolResult | None`, because `ToolResult` is `frob.process`'s own
#: domain type -- nothing outside the check/process stack constructs
#: one. T-1144's own investigation confirmed the genuine body-level
#: duplication in this area (`_opt_in_deploy_stage_result`,
#: `_missing_tool_result` forwarding to `tool_unavailable_result`) was
#: already extracted by T-1124; what remained across all 4 ToolResult-
#: shaped groups (24 members measured) was purely this same
#: convention-shape false positive, not a further extraction
#: opportunity -- a lone unrelated member like `parse_junit_xml`
#: (real XML-parsing logic that happens to share `(str, str) ->
#: ToolResult` with three trivial synthetic-result builders purely
#: because its `tool` parameter has a default) makes that especially
#: clear: there is no one coherent family to extract here, only the
#: shared return type.
# frob:ticket T-1195
_TOOL_RESULT_BUILDER_RETURN_TYPES = frozenset({"ToolResult", "ToolResult | None"})


# frob:ticket T-1195
def _is_tool_result_builder_family(ret: str) -> bool:
    """Whether a shared-signature group's return type `ret` (T-1144) is
    `frob.process`/`frob.check`'s own check-stage-runner convention
    rather than an accidental duplication: `ret` is one of `_TOOL_RESULT_
    BUILDER_RETURN_TYPES`. Structural, not name-based -- see
    `_TOOL_RESULT_BUILDER_RETURN_TYPES`'s docstring for why a return-type
    check is the right discriminator for this family specifically,
    mirroring `_is_gate_rule_builder_family`'s identical shape for
    `frob.gates`'s own `Violation` convention."""
    return ret in _TOOL_RESULT_BUILDER_RETURN_TYPES


# T-0370: types so ubiquitous that sharing one carries no abstraction
# signal on its own -- `(str) -> str`, `(AppConfig) -> None`, and similar
# shapes collide across dozens of semantically-unrelated functions purely
# because the type system only has so many primitives to offer, OR because
# one project-wide "contract" type is threaded through every subcommand
# entrypoint on purpose (`AppConfig`, the App/AppConfig pattern's uniform
# `run(config) -> None` shape every runner module implements). A signature
# built ENTIRELY from names in this set is "generic"; a signature with at
# least one name outside it (a real domain type like `TicketStore` or
# `CloneReport`, which does NOT appear here) is specific.
# frob:ticket T-1195
_GENERIC_TYPE_NAMES = frozenset(
    {
        "str",
        "int",
        "bool",
        "float",
        "bytes",
        "None",
        "Path",
        "object",
        "Any",
        "list",
        "dict",
        "set",
        "tuple",
        "frozenset",
        "Sequence",
        "Iterable",
        "Iterator",
        "Mapping",
        "Optional",
        "Union",
        "Callable",
        "self",
        "cls",
        # App/AppConfig pattern (~/.claude/refs/python-app.md): every
        # runner module's `run(config: AppConfig) -> None` entrypoint
        # shares this signature by DESIGN, not by coincidence -- it is
        # the uniform CLI-dispatch contract, not an extractable family.
        "AppConfig",
    }
)

# frob:ticket T-1195
_TYPE_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


# frob:ticket T-1195
def _type_is_generic(annotation: str) -> bool:
    """Whether every identifier token in `annotation` is one of the
    ubiquitous names in `_GENERIC_TYPE_NAMES` (T-0370) -- e.g. `str`,
    `list[str]`, `Path | None` are generic; `AppConfig`, `CloneReport` are
    not. An annotation with no identifier tokens (empty) counts as
    generic: it carries no specificity signal."""
    tokens = _TYPE_TOKEN_RE.findall(annotation)
    if not tokens:
        return True
    return all(tok in _GENERIC_TYPE_NAMES for tok in tokens)


# frob:ticket T-1195
def _signature_is_specific(ptypes: tuple[str, ...], ret: str) -> bool:
    """Whether a shared signature has at least one non-generic type
    (T-0370) -- the SIGNATURE-SPECIFICITY discriminator. A group sharing
    only ubiquitous types (`(str) -> str`, `(AppConfig) -> None`) needs
    body-similarity evidence instead; one carrying a domain type
    (`(TicketStore, str) -> Result[...]`) is specific enough on its own."""
    return any(not _type_is_generic(t) for t in (*ptypes, ret) if t)


# T-0370: two normalized bodies are near-duplicate when their token
# sequences (locals alpha-renamed, literals collapsed to `_S_`/`_N_` by
# `_serialize_py_body`) match at or above this ratio -- high enough that a
# body reshaped only by renamed variables still matches, low enough to
# tolerate a stray extra statement between otherwise-identical bodies.
# frob:ticket T-1195
_BODY_SIMILARITY_THRESHOLD = 0.9

# T-0370: bodies shorter than this many normalized tokens are excluded from
# body-similarity clustering entirely. `difflib.SequenceMatcher.ratio()` on
# very short strings is dominated by shared PUNCTUATION/keyword tokens
# (`_S_ return _v0 . x`-shaped one-liners) rather than shared LOGIC, so tiny
# unrelated one-line predicates/getters collide at >=0.9 by coincidence --
# exactly the false-positive noise the ticket calls out. A real extractable
# family has an actual body to share, not just a `return` statement.
# frob:ticket T-1195
_BODY_MIN_TOKENS = 8


# frob:ticket T-1195
def _near_duplicate_cluster_native(
    bodies: list[str],
) -> list[int] | None:
    """`frob_core.near_duplicate_indices` over `bodies`, or `None` when the
    native extension is not importable (T-0953). ONE marshal per
    same-signature group -- the whole eligible-body list crosses the FFI
    boundary once, not once per pairwise comparison (the batching shape
    T-0930's reverted `resolve_call_edges` prototype lacked, and the reason
    that prototype measured net slower where this kernel measures net
    faster: this repo's real same-signature groups run up to several dozen
    members, large enough for the O(n^2) comparison work to amortize the
    fixed PyO3 marshaling tax, unlike T-0930's per-symbol/per-package call
    sites)."""
    from frob.dup._core import core_available

    if not core_available():
        return None
    import frob_core

    return list(frob_core.near_duplicate_indices(bodies, _BODY_SIMILARITY_THRESHOLD))


# frob:waive DUP001 reason="pre-existing duplication surfaced by the T-1195 move, not \
# introduced by it: 95% similar to strata/_report.py::_assumption_ledger_lines and \
# app/test_runner.py::_print_fuzz_results -- three independent per-domain \
# accumulate-then-format loops (body-similarity clusters, assumption-ledger rows, \
# fuzz-falsification results) that coincidentally share a filter-then-collect shape; a \
# shared helper would couple three unrelated domains for a coincidental structural \
# resemblance, not a real abstraction"
# frob:ticket T-1195
def _near_duplicate_cluster(
    members: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """The subset of `members` (`(rel, fname, body_fingerprint)`) that has
    at least one near-duplicate partner within the group (T-0370) -- the
    BODY-SIMILARITY discriminator, the strongest signal that a same-
    signature group is a genuine extractable abstraction rather than a
    coincidental collision. Bodies under `_BODY_MIN_TOKENS` tokens (empty
    stubs, trivial one-liners) never participate -- too short for
    similarity to mean anything. Returns the near-duplicate members only,
    NOT the whole input group: a group of 30 unrelated functions with one
    genuinely duplicated pair should be reported as that pair, not
    misrepresented as 30 functions all sharing logic.

    T-0953: dispatches to the `frob_core` kernel
    (`_near_duplicate_cluster_native`) when available -- measured ~2.6x
    faster than the pure-Python loop below at this repo's real
    same-signature-group sizes (median 2.49s -> 0.97s thread_time across
    this repo's own 67 real groups, 0 parity mismatches against
    `difflib.SequenceMatcher.ratio()`) -- and falls back to the original
    pairwise `difflib` loop, BYTE-IDENTICAL in result, when it is not."""
    eligible = [m for m in members if len(m[2].split()) >= _BODY_MIN_TOKENS]
    native_idx = _near_duplicate_cluster_native([m[2] for m in eligible])
    if native_idx is not None:
        return [eligible[i] for i in native_idx]
    cluster_idx: set[int] = set()
    for i in range(len(eligible)):
        for j in range(i + 1, len(eligible)):
            ratio = difflib.SequenceMatcher(
                None, eligible[i][2], eligible[j][2]
            ).ratio()
            if ratio >= _BODY_SIMILARITY_THRESHOLD:
                cluster_idx.add(i)
                cluster_idx.add(j)
    return [eligible[i] for i in sorted(cluster_idx)]


# frob:ticket T-1195
def _emit_abstraction_suggestion(
    ptypes: tuple[str, ...],
    ret: str,
    flagged: list[tuple[str, str, str]],
    out: list[ArchSuggestion],
) -> None:
    """Append one `abstraction-opportunity` `ArchSuggestion` for `flagged`
    (T-0370, factored out of `_check_abstraction_opportunities` to keep
    the per-group decision logic and the message formatting each
    independently short)."""
    params_str = ", ".join(ptypes)
    sig_str = f"({params_str}) -> {ret}" if ret else f"({params_str})"
    fn_names = ", ".join(fname for _, fname, _ in flagged)
    out.append(
        ArchSuggestion(
            file=flagged[0][0],
            category="abstraction-opportunity",
            severity="suggestion",
            message=f"{len(flagged)} functions share signature `{sig_str}`: {fn_names}",
            detail="Consider a shared protocol or base class",
        )
    )


# frob:ticket T-1195
def _abstraction_group_evidence(
    ptypes: tuple[str, ...],
    ret: str,
    members_with_body: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """The subset of `members_with_body` that constitutes genuine
    abstraction-opportunity evidence for this `(ptypes, ret)` group
    (T-0370): the whole group when the signature is SPECIFIC
    (`_signature_is_specific`), or the near-duplicate-body subset
    (`_near_duplicate_cluster`) when it is generic. Empty means no
    evidence -- the caller should not flag."""
    if _signature_is_specific(ptypes, ret):
        return members_with_body
    return _near_duplicate_cluster(members_with_body)


#: T-1182 (refiled from the T-1083 disposition, w20-arch a8085d7f): the
#: token budget a call-through forwarder's serialized body
#: (`_body_fingerprint`/`_serialize_py_body`) may spend before it no
#: longer reads as "single statement". `RenderWriter.heading`'s body --
#: `self . _emit ( heading ( _v0 , color = self . color ) )` -- is 14
#: tokens; this is a generous but still narrow ceiling meant to admit
#: exactly that shape (one attribute-chain call wrapping one delegated
#: call, at most a couple of keyword arguments), not an arbitrary
#: multi-statement body that merely happens to mention its own name.
# frob:waive PII012 reason="'token' here means a normalized body-fingerprint lexical \
# token (_serialize_py_body's output), not a credential/auth token -- a name-signature \
# false positive, same class as frob.outline's existing PII012 waiver for its own \
# unrelated lexical-token vocabulary"
# frob:ticket T-1195
_FORWARDER_BODY_TOKEN_LIMIT = 20


# frob:ticket T-1195
def _is_self_named_forwarder(fname: str, body_fp: str) -> bool:
    """Whether one member's serialized body `body_fp` (`_body_fingerprint`)
    is a short, single-statement call-through to a symbol sharing its OWN
    bare name `fname` (T-1182) -- e.g. `RenderWriter.heading`'s body
    `self . _emit ( heading ( _v0 , color = self . color ) )` delegates to
    the module-level `frob.render._elements.heading` it shadows
    (T-0448/T-0460's vocabulary-namespace convention). Short
    (`_FORWARDER_BODY_TOKEN_LIMIT`) AND self-referential are both
    required: a long body that happens to mention its own name somewhere
    is not a pure forwarder, and a short body that never mentions its own
    name is not delegating to its own lineage at all."""
    if not body_fp:
        return False
    tokens = body_fp.split(" ")
    return len(tokens) <= _FORWARDER_BODY_TOKEN_LIMIT and fname in tokens


# frob:ticket T-1195
def _is_call_through_forwarder_family(
    members_with_body: list[tuple[str, str, str]],
) -> bool:
    """Whether a shared-signature `members_with_body` group (T-1182,
    refiled from the T-1083 disposition) consists ENTIRELY of call-through
    forwarders rather than an accidental duplication: every member
    independently satisfies `_is_self_named_forwarder` -- its own body is a
    short, single-statement delegation to an identically-named symbol it
    shadows. Unlike `_is_language_parity_family`/`_is_check_registry_family`,
    this is NOT a same-name-across-the-group check: `RenderWriter`'s
    `heading`/`subhead`/`good`/`warn`/`muted` group shares a signature
    under FIVE DIFFERENT names, each independently forwarding to its own
    identically-named module-level counterpart (its own lineage) --
    the point is that every member is a thin shadow of SOME same-named
    symbol, not that the group shares one common name. A group with even
    one member whose body is not itself a short self-named forwarder is
    never excluded here -- that member is unexplained real duplication,
    exactly what this detector exists to catch."""
    if len(members_with_body) < 2:
        return False
    return all(
        _is_self_named_forwarder(fname, body_fp)
        for _, fname, body_fp in members_with_body
    )


# frob:ticket T-1195
def _check_abstraction_opportunities(
    all_sigs: list[tuple[str, str, tuple[str, ...], str, str]],
    all_dispatch_refs: dict[str, set[str]],
    out: list[ArchSuggestion],
) -> None:
    """Flag signatures shared by 3+ functions with no common dispatch site
    AND genuine evidence of an extractable abstraction (T-0370): either the
    shared signature is SPECIFIC (`_signature_is_specific`, at least one
    non-generic type -- the whole group is reported, the signature itself
    is the evidence) or a subset of the members has near-duplicate BODIES
    (`_near_duplicate_cluster`, reusing the dup-scanner's normalizer --
    only that near-duplicate subset is reported, since the rest of a
    generic-signature group proved nothing). A group sharing only an
    over-generic signature (`(str) -> str`, `(AppConfig) -> None`) with no
    such duplicated subset is NOT flagged at all -- you cannot factor N
    unrelated functions into one helper just because they happen to take
    the same primitive types. Groups whose members are all reachable from
    one common caller/registry (`_is_dispatch_family`, T-0360) are
    intentional dispatch families and are still skipped first, as are
    groups whose members are each a distinctly-tagged per-language walker
    (`_is_language_parity_family`, T-1068) -- the same false-positive
    class filed from T-0393 (arch's own `_py_*`/`_rust_*`/`_kt_*`/`_ts_*`/
    `_cpp_*` walker families sharing a signature by design, not by
    accident) -- and groups whose members are all `frob.arch`'s own
    `check_*` detector-registry functions (`_is_check_registry_family`,
    T-1112, filed from T-1084), all `frob.gates`'s own gate/rule-
    builder return-type convention (`_is_gate_rule_builder_family`,
    T-1141, filed from T-1114), or all `frob.process`/`frob.check`'s own
    check-stage-runner return-type convention
    (`_is_tool_result_builder_family`, T-1144, filed from T-1124). The
    evidence subset (`flagged`, post body-similarity clustering) is also
    checked against `_is_call_through_forwarder_family` (T-1182, refiled
    from the T-1083 disposition) -- see that function's own docstring."""
    groups: dict[tuple[tuple[str, ...], str], list[tuple[str, str, str]]] = defaultdict(
        list
    )
    for rel, fname, ptypes, ret, body_fp in all_sigs:
        if not ptypes:
            continue
        groups[(ptypes, ret)].append((rel, fname, body_fp))

    for (ptypes, ret), members_with_body in groups.items():
        if len(members_with_body) < 3:
            continue
        members = [(rel, fname) for rel, fname, _ in members_with_body]
        if _is_dispatch_family(members, all_dispatch_refs):
            continue
        if _is_language_parity_family(members):
            continue
        if _is_check_registry_family(members):
            continue
        if _is_gate_rule_builder_family(ret):
            continue
        if _is_tool_result_builder_family(ret):
            continue
        flagged = _abstraction_group_evidence(ptypes, ret, members_with_body)
        if len(flagged) < 2:
            continue
        # T-1182: checked against `flagged` (the evidence subset), not
        # the raw group -- see `_is_call_through_forwarder_family`.
        if _is_call_through_forwarder_family(flagged):
            continue
        _emit_abstraction_suggestion(ptypes, ret, flagged, out)
