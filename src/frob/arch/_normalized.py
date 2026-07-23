"""Normalized code model: a language-agnostic view of source structure that
each `frob.lang`-supported grammar's Adapter maps its tree-sitter parse onto
(T-0609, EPIC T-0329's foundation).

WHY: `frob.arch._python`/`_cpp` today each hand-walk their own tree-sitter
grammar for every check (long-function, god-class, the T-0332 pattern
recommender's isinstance-chain/state-field/telescoping-ctor/wrap-delegate
detectors...). Adding a language today means re-deriving every detector's
walk against a new grammar's node-type names -- N copies of each check
instead of one. This module defines the SHARED shape (module, class,
function, method, param, branch, loop, call, import, override,
field-access, return, raise/throw, catch) that a check can be written
against exactly once, plus the `LanguageAdapter` protocol each per-grammar
walker implements to produce it. `frob.arch._patterns`'s detectors are the
concrete case study this shape was designed to satisfy: isinstance-chain
detection needs branch conditions + calls; state-field-chain needs field
assignments + equality branches; telescoping-ctor needs `__init__`
params; wrap-delegate needs fields + method-body call targets;
scattered-construction needs cross-file call sites. All of that is
representable here without inventing anything the existing detectors do
not already need.

SCOPE (T-0609): this ticket defines the model and the adapter protocol
only -- no existing check is migrated onto it yet (that migration is
T-0610, the epic's next child). `frob.arch._python`/`_cpp` keep parsing
and checking exactly as before; nothing here is wired into
`analyze_project` yet.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel

#: `frob.lang.raw_tree`'s language label (`"python"`, `"cpp"`, `"typescript"`,
#: `"rust"`, `"kotlin"`, ...) -- kept as a bare `str`, not a `Literal`, since
#: new adapters (T-0610-T-0625) register languages this model must not need
#: editing to accept.
Language = str


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedParam(BaseModel):
    """One function/method parameter: its name, an optional source-text type
    annotation, and whether a default value is present (never the default's
    value itself -- checks reason about SHAPE, not literal defaults)."""

    model_config = {}

    name: str
    type: str | None = None
    has_default: bool = False


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedFieldAccess(BaseModel):
    """A read or write of an object field (`self.x`, `this->x`, `obj.attr`)
    inside a function/method body, at the source line it occurs."""

    model_config = {}

    name: str
    line: int
    is_write: bool = False


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedCallArg(BaseModel):
    """One argument at a call site (T-0632): its position -- a 0-based
    `index` for a positional argument, or a `keyword` name for a keyword
    argument (exactly one of the two is set) -- and, when the argument
    itself is a bare identifier reference (`f(x)`, `f(key=x)`), that
    identifier's text in `ident`. `ident` is `None` for any other argument
    shape (a literal, a call, an attribute access, ...) -- dispatch/
    registration detectors (`frob.arch._python._collect_dispatch_refs`)
    only care about bare-identifier arguments, so non-identifier shapes are
    not otherwise represented here."""

    model_config = {}

    index: int | None = None
    keyword: str | None = None
    ident: str | None = None


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedCall(BaseModel):
    """A call site inside a function/method body: the callee name (bare
    identifier or `obj.method` dotted form), the source line it occurs at,
    and its argument list (`args`, T-0632: position/keyword + bare-
    identifier detail per argument) -- the shared unit every dispatch/
    construction/delegation detector (`frob.arch._patterns`) reasons
    about."""

    model_config = {}

    callee: str
    line: int
    args: list[NormalizedCallArg] = []


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedBranch(BaseModel):
    """One decision point (`if`/`elif`/`else`, a ternary, a boolean
    short-circuit) inside a function/method body -- the shared unit the
    cyclomatic-complexity proxy and the T-0332 isinstance-chain/state-field-
    chain detectors both walk. `condition_text` is the raw source text of
    the branch's test expression, kept as text (not a further-normalized
    sub-model) since detectors that need structure from it (an `isinstance`
    target, an equality target/literal) already do so via lightweight text
    parsing rather than a second full expression grammar."""

    model_config = {}

    line: int
    condition_text: str


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedLoop(BaseModel):
    """One `for`/`while` loop inside a function/method body -- tracked
    separately from `NormalizedBranch` since nesting-depth and cyclomatic
    checks both count loops as decision points but no detector needs a
    loop's iterable/condition text today (unlike a branch's condition)."""

    model_config = {}

    line: int
    kind: str  # "for" | "while"


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedReturn(BaseModel):
    """A `return` statement's source line (value text kept optional and
    unparsed -- no existing detector needs more than presence/line today)."""

    model_config = {}

    line: int
    value_text: str | None = None


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedRaise(BaseModel):
    """A `raise`/`throw` statement's source line and the raised type's
    name where staticaly determinable (`raise ValueError(...)` ->
    `"ValueError"`; `throw std::runtime_error(...)` -> `"runtime_error"`)."""

    model_config = {}

    line: int
    exception_type: str | None = None


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedCatch(BaseModel):
    """One `except`/`catch` clause's source line and the caught type name
    where present (a bare `except:`/`catch (...)` catch-all leaves this
    `None`)."""

    model_config = {}

    line: int
    exception_type: str | None = None


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedFunction(BaseModel):
    """One function or method: its name, parameters, return-type text,
    starting line, body length in lines, and the flattened structural
    events inside its body (branches/loops/calls/field-accesses/returns/
    raises/catches) that every existing detector needs -- see this
    module's docstring for the T-0332 detector-to-field mapping. `is_method`
    plus `overrides` (name of the base-class method this one overrides,
    when an adapter can determine it -- e.g. an explicit base-class method
    of the same name, or a language's own override keyword/annotation)
    covers the "override" entity the ticket calls out without a separate
    top-level type, since an override is always scoped to a method.

    `max_nesting_depth`/`cyclomatic` (T-0610) are adapter-computed
    structural metrics from the language's OWN full subtree (including
    through nested function/class boundaries, matching each existing
    per-language nesting/cyclomatic-proxy walk exactly) -- deliberately NOT
    derivable from the flattened `branches`/`loops`/`catches` lists below,
    which stop at a nested function/class boundary (those become their own
    `NormalizedFunction`/`NormalizedClass`) and would under-count relative
    to the original per-language walk. A check that needs the true metric
    reads these fields instead of re-deriving it from a language-specific
    tree."""

    model_config = {}

    name: str
    line: int
    body_line_count: int
    params: list[NormalizedParam] = []
    return_type: str | None = None
    is_method: bool = False
    overrides: str | None = None
    max_nesting_depth: int = 0
    cyclomatic: int = 0
    branches: list[NormalizedBranch] = []
    loops: list[NormalizedLoop] = []
    calls: list[NormalizedCall] = []
    field_accesses: list[NormalizedFieldAccess] = []
    returns: list[NormalizedReturn] = []
    raises: list[NormalizedRaise] = []
    catches: list[NormalizedCatch] = []
    nested_functions: list["NormalizedFunction"] = []


NormalizedFunction.model_rebuild()


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedField(BaseModel):
    """One class-level or instance field: its name, an optional type
    annotation, and the source line of its first assignment (a class body
    annotation, or a `self.x = ...`/`this->x = ...` inside `__init__`,
    whichever an adapter finds first)."""

    model_config = {}

    name: str
    line: int
    type: str | None = None


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedVariantPayload(BaseModel):
    """One associated-data field of an enum variant (T-0743): `name` is a
    struct-variant field's own name, or a tuple-variant field's positional
    index as a string (`"0"`, `"1"`, ...) -- the same positional-name
    convention `NormalizedField` already uses for tuple-struct fields, kept
    consistent rather than inventing a second one."""

    model_config = {}

    name: str
    type: str | None = None


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedVariant(BaseModel):
    """One enum variant (T-0743): its name, source line, associated-data
    `shape` (`"unit"` -- no payload, e.g. `Empty`; `"tuple"` -- positional
    payload, e.g. `Circle(f64)`; `"struct"` -- named payload, e.g.
    `Square { side: f64 }`), and the payload fields themselves (empty for
    `"unit"`). Exists because `NormalizedField` (what enum variants mapped
    onto before this ticket) has no way to represent a variant's OWN
    payload shape -- only a bare name -- so a tuple-vs-struct-vs-unit
    variant and its field types were indistinguishable on the model."""

    model_config = {}

    name: str
    line: int
    shape: str = "unit"  # "unit" | "tuple" | "struct"
    payload: list[NormalizedVariantPayload] = []


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedClass(BaseModel):
    """One class/struct/enum: its name, base-class names (as written in
    source -- an adapter does not resolve inheritance across files),
    starting line, and its fields/methods. `variants` (T-0743) is populated
    only for an enum-shaped type -- its associated-data payload detail,
    which `fields` alone cannot represent (see `NormalizedVariant`); an
    adapter mapping an enum still ALSO fills `fields` with one bare-name
    entry per variant (unchanged pre-T-0743 behavior, for any consumer that
    only needs variant names/counts, e.g. `_check_god_classes`-style
    checks) -- `variants` is additive detail, not a replacement."""

    model_config = {}

    name: str
    line: int
    bases: list[str] = []
    fields: list[NormalizedField] = []
    methods: list[NormalizedFunction] = []
    variants: list[NormalizedVariant] = []


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedImport(BaseModel):
    """One import/include/use statement: the raw module/path text as
    written, the source line, and the specific names imported from it, if
    any (`from mod import a, b` -> `["a", "b"]`; a bare `import mod`,
    `#include <mod>`, or `use mod::*` -> `[]`)."""

    model_config = {}

    module: str
    line: int
    names: list[str] = []


# frob:doc docs/modules/arch.md#normalized-code-model
class NormalizedModule(BaseModel):
    """The whole-file normalized view an adapter produces for one source
    file: its path (repo-relative), source language label, top-level
    imports, top-level classes, and top-level (free) functions. This is
    the root a language-agnostic check walks instead of a raw tree-sitter
    `Tree` -- everything a check needs (see this module's docstring) is
    reachable from here without touching `frob.lang`/tree-sitter at all."""

    model_config = {}

    path: str
    language: Language
    imports: list[NormalizedImport] = []
    classes: list[NormalizedClass] = []
    functions: list[NormalizedFunction] = []


# frob:doc docs/modules/arch.md#normalized-code-model
# frob:tests tests/unit/test_arch.py::TestNormalizedModel.test_language_adapter_is_a_runtime_checkable_protocol  # noqa: E501
@runtime_checkable
class LanguageAdapter(Protocol):
    """The per-grammar contract a language walker implements to produce a
    `NormalizedModule` from a parsed source file (T-0609). One adapter per
    `frob.lang` grammar label (`"python"`, `"cpp"`, and -- per EPIC T-0329's
    remaining children T-0610-T-0625 -- `"typescript"`, `"rust"`,
    `"kotlin"`); a check written once against `NormalizedModule` then fires
    identically across every adapter that exists, with no per-language
    branch in the check itself.

    No adapter is registered or implemented against this protocol yet in
    this ticket's scope -- `frob.arch._python`/`_cpp` keep parsing and
    checking directly against tree-sitter as before; T-0610 is where the
    first adapter (migrating the existing python walker) lands.
    """

    #: The `frob.lang` language label this adapter handles (e.g.
    #: `"python"`) -- lets a registry (T-0610) dispatch a parsed file's
    #: `frob.lang.raw_tree` language label to the matching adapter.
    language: Language

    # frob:doc docs/modules/arch.md#normalized-code-model
    # frob:tests tests/unit/test_arch.py::TestNormalizedModel.test_language_adapter_is_a_runtime_checkable_protocol  # noqa: E501
    def adapt(self, tree: object, source: bytes, rel: str) -> NormalizedModule:
        """Map one parsed source file's tree-sitter `Tree` (`tree`, typed
        `object` here to keep this module import-free of `tree_sitter` --
        an adapter implementation narrows it) and raw `source` bytes (needed
        for text extraction the tree-sitter node span alone cannot resolve
        efficiently, e.g. multi-node expression text) onto a
        `NormalizedModule` for the file at repo-relative path `rel`."""
        ...
