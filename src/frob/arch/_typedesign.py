"""Type-driven design checks (ARCH1xx, T-0621, EPIC T-0330's "Logan Smith"
type-driven-design family): make-illegal-states-unrepresentable,
primitive obsession, parse-dont-validate, and boolean/flag parameter.

WHY here, not `_solid.py`/`_layering.py`: this ticket's own SOLID-adjacent
sibling cluster (T-0616-T-0620) already established one module per
principle family; type-driven design is its own family in the epic's
catalog (T-0330's body lists it as a fifth bullet alongside SRP/OCP/LSP/
ISP/DIP), so it gets its own module rather than growing `_solid.py`
further. Every check here is written once against `frob.arch._normalized.
NormalizedModule` (T-0609), same convention as `_solid.py`'s checks --
nothing here parses a `tree_sitter.Tree` directly.

T-0892 FOLD-IN NOTE: this module originally built findings against a LOCAL
`TypeDesignCategory`/`TypeDesignSuggestion` pair because at T-0621's
implementation time a sibling ticket (T-0620) held an active scope lease
on `src/frob/arch/_models.py`. That lease is now free (T-0620 closed) --
this module builds `frob.arch._models.ArchSuggestion`/`ArchCategory`
directly, the four check functions' logic unchanged.
"""

from __future__ import annotations

from frob.arch._models import ArchSuggestion
from frob.arch._normalized import NormalizedClass, NormalizedFunction, NormalizedModule


def _qualname(
    module: NormalizedModule, cls: NormalizedClass | None, func: NormalizedFunction
) -> str:
    """`path::Class.method`/`path::function` symref (T-0289's shape,
    T-0621) for `func`, optionally scoped to `cls`."""
    if cls is None:
        return f"{module.path}::{func.name}"
    return f"{module.path}::{cls.name}.{func.name}"


# ---------------------------------------------------------------------------
# make-illegal-states-unrepresentable (T-0621)
# ---------------------------------------------------------------------------


def _bool_field_names(cls: NormalizedClass) -> set[str]:
    """Names of `cls`'s fields declared with a `bool` type annotation
    (T-0621) -- the corpus `check_illegal_states_representable` looks for
    a runtime cross-field guard on."""
    return {f.name for f in cls.fields if f.type == "bool"}


# frob:doc docs/modules/arch.md#type-driven-design-checks
# frob:ticket T-0972
# frob:tests tests/unit/test_arch.py::TestIllegalStatesRepresentable.test_bool_field_cross_field_guard_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestIllegalStatesRepresentable.test_bool_field_alone_not_flagged  # noqa: E501
def check_illegal_states_representable(
    module: NormalizedModule,
) -> list[ArchSuggestion]:
    """Make-illegal-states-unrepresentable (T-0621): flag a class with a
    `bool`-typed field (`_bool_field_names`) that some method's OWN body
    guards at runtime via a branch mentioning BOTH that bool field's name
    AND another field's name, immediately followed by a raise (the same
    line-adjacency guard-clause proxy `frob.arch._solid._raise_or_assert_
    param_mentions` uses for LSP's strengthened-precondition check) -- a
    "these two fields' combination is sometimes invalid" constraint
    enforced by a runtime check is exactly the illegal-state-representable
    smell: modeling the valid combinations as an enum/newtype would make
    the invalid combination impossible to construct at all, instead of
    merely checked. Written once against `NormalizedModule`, so it fires
    for every `LanguageAdapter`."""
    out: list[ArchSuggestion] = []
    for cls in module.classes:
        bool_fields = _bool_field_names(cls)
        if not bool_fields:
            continue
        other_field_names = {f.name for f in cls.fields} - bool_fields
        if not other_field_names:
            continue
        for m in cls.methods:
            raise_lines = {r.line for r in m.raises}
            for b in m.branches:
                if not any(0 <= rl - b.line <= 2 for rl in raise_lines):
                    continue
                mentioned_bool = {n for n in bool_fields if n in b.condition_text}
                mentioned_other = {
                    n for n in other_field_names if n in b.condition_text
                }
                if not mentioned_bool or not mentioned_other:
                    continue
                out.append(
                    ArchSuggestion(
                        file=module.path,
                        line=b.line,
                        category="illegal-states-representable",
                        severity="suggestion",
                        message=(
                            f"`{cls.name}` guards `{sorted(mentioned_bool)}` against"
                            f" `{sorted(mentioned_other)}` at runtime in `{m.name}`"
                        ),
                        detail=(
                            "a bool field whose validity depends on another field"
                            " is a hidden state machine -- model the valid"
                            " combinations as an enum/newtype so the invalid"
                            " combination cannot be constructed at all"
                        ),
                        symref=_qualname(module, cls, m),
                    )
                )
    return out


# ---------------------------------------------------------------------------
# primitive obsession (T-0621)
# ---------------------------------------------------------------------------

#: Raw type-annotation text (T-0621) counted as "primitive" for the
#: primitive-obsession heuristic -- python's built-in scalar types, as
#: written in a signature (no attempt to resolve an alias/newtype).
_PRIMITIVE_TYPE_NAMES = frozenset({"str", "int", "float"})

#: Minimum count (T-0621) of same-function primitive-typed params before
#: the shape counts as primitive obsession -- 1-2 raw params is ordinary;
#: 3+ together is the "these clearly belong to one domain concept" smell
#: the ticket calls out.
# frob:doc docs/modules/arch.md#type-driven-design-checks
PRIMITIVE_OBSESSION_MIN_PARAMS = 3


def _primitive_param_names(func: NormalizedFunction) -> list[str]:
    """Names of `func`'s params annotated with a raw primitive type
    (`_PRIMITIVE_TYPE_NAMES`, T-0621), receiver params excluded."""
    return [
        p.name
        for p in func.params
        if p.type in _PRIMITIVE_TYPE_NAMES and p.name not in ("self", "this", "cls")
    ]


# frob:doc docs/modules/arch.md#type-driven-design-checks
# frob:tests tests/unit/test_arch.py::TestPrimitiveObsession.test_three_plus_raw_params_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestPrimitiveObsession.test_two_raw_params_not_flagged  # noqa: E501
def check_primitive_obsession(module: NormalizedModule) -> list[ArchSuggestion]:
    """Primitive obsession (T-0621): flag a function/method whose
    signature carries at least `PRIMITIVE_OBSESSION_MIN_PARAMS` (3) raw
    `str`/`int`/`float`-typed parameters (`_primitive_param_names`) --
    a same-file, single-signature proxy for "this cluster of primitives
    is really one domain concept begging for its own type" (the ticket's
    fuller "repeated co-occurrence across call sites" framing would need
    a project-wide call-site scan; this check stays a per-signature proxy,
    disclosed here rather than silently narrowed). Written once against
    `NormalizedModule`, so it fires for every `LanguageAdapter`."""
    out: list[ArchSuggestion] = []

    def _scan(func: NormalizedFunction, qualname: str) -> None:
        names = _primitive_param_names(func)
        if len(names) < PRIMITIVE_OBSESSION_MIN_PARAMS:
            return
        out.append(
            ArchSuggestion(
                file=module.path,
                line=func.line,
                category="primitive-obsession",
                severity="suggestion",
                message=(
                    f"`{qualname}` takes {len(names)} raw primitive params: {names}"
                ),
                detail=(
                    "a cluster of raw str/int params passed together is"
                    " usually one domain concept -- give it its own type"
                    " (a dataclass/NamedTuple/newtype) instead of passing"
                    " the fields separately"
                ),
                symref=qualname,
                metric=len(names),
            )
        )

    for f in module.functions:
        _scan(f, f.name)
    for c in module.classes:
        for m in c.methods:
            _scan(m, f"{c.name}.{m.name}")
    return out


# ---------------------------------------------------------------------------
# parse-dont-validate (T-0621)
# ---------------------------------------------------------------------------


# frob:doc docs/modules/arch.md#type-driven-design-checks
# frob:tests tests/unit/test_arch.py::TestParseDontValidate.test_validates_then_returns_same_type_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestParseDontValidate.test_validates_then_returns_refined_type_not_flagged  # noqa: E501
def check_parse_dont_validate(module: NormalizedModule) -> list[ArchSuggestion]:
    """Parse-dont-validate (T-0621): flag a function/method with EXACTLY
    one non-receiver parameter whose body guards it (a branch mentioning
    the param's name immediately followed by a raise -- the same
    line-adjacency guard-clause proxy used above) AND whose declared
    `return_type` is IDENTICAL to that same parameter's declared `type`
    text -- the textbook parse-dont-validate anti-pattern: the function
    proves an invariant about its input (the validation) but hands the
    caller back the exact same unrefined type instead of a type that
    encodes "this has already been validated". A function with a
    DIFFERENT (or absent) return type is not flagged -- that is the
    refined-type shape this check is pointing callers toward. Written
    once against `NormalizedModule`, so it fires for every
    `LanguageAdapter`."""
    out: list[ArchSuggestion] = []

    def _scan(func: NormalizedFunction, qualname: str) -> None:
        params = [p for p in func.params if p.name not in ("self", "this", "cls")]
        if len(params) != 1:
            return
        (param,) = params
        if param.type is None or func.return_type != param.type:
            return
        raise_lines = {r.line for r in func.raises}
        guarded = any(
            0 <= rl - b.line <= 2 and param.name in b.condition_text
            for b in func.branches
            for rl in raise_lines
        )
        if not guarded:
            return
        out.append(
            ArchSuggestion(
                file=module.path,
                line=func.line,
                category="parse-dont-validate",
                severity="suggestion",
                message=(
                    f"`{qualname}` validates `{param.name}` but returns the"
                    f" same unrefined `{param.type}` type"
                ),
                detail=(
                    "a function that proves an invariant about its input"
                    " should hand back a type that encodes that proof (a"
                    " newtype/refined type), not the original unrefined"
                    " type -- callers get no static evidence the check ran"
                ),
                symref=qualname,
            )
        )

    for f in module.functions:
        _scan(f, f.name)
    for c in module.classes:
        for m in c.methods:
            _scan(m, f"{c.name}.{m.name}")
    return out


# ---------------------------------------------------------------------------
# boolean/flag parameter (T-0621)
# ---------------------------------------------------------------------------


# frob:doc docs/modules/arch.md#type-driven-design-checks
# frob:tests tests/unit/test_arch.py::TestBooleanFlagParam.test_public_function_branching_on_bool_param_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestBooleanFlagParam.test_private_function_not_flagged  # noqa: E501
def check_boolean_flag_param(module: NormalizedModule) -> list[ArchSuggestion]:
    """Boolean/flag parameter (T-0621): flag a PUBLIC (name not starting
    with `_`) function/method with a `bool`-typed parameter that its OWN
    body branches on (a `NormalizedBranch.condition_text` mentioning the
    param's name) -- a caller-visible flag that switches internal
    behavior is a split-function candidate: two callers passing `True`/
    `False` almost never want the "same function", they want two
    different functions the flag is faking. Written once against
    `NormalizedModule`, so it fires for every `LanguageAdapter`."""
    out: list[ArchSuggestion] = []

    def _scan(func: NormalizedFunction, qualname: str, bare_name: str) -> None:
        if bare_name.startswith("_"):
            return
        bool_params = [
            p.name
            for p in func.params
            if p.type == "bool" and p.name not in ("self", "this", "cls")
        ]
        if not bool_params:
            return
        for pname in bool_params:
            if any(pname in b.condition_text for b in func.branches):
                out.append(
                    ArchSuggestion(
                        file=module.path,
                        line=func.line,
                        category="boolean-flag-param",
                        severity="suggestion",
                        message=(
                            f"`{qualname}` branches internally on bool param `{pname}`"
                        ),
                        detail=(
                            "a public function whose behavior forks on a bool"
                            " flag is usually two functions wearing one name"
                            " -- split it so each caller states its intent by"
                            " which function it calls, not which literal it"
                            " passes"
                        ),
                        symref=qualname,
                        metric=sum(
                            1 for b in func.branches if pname in b.condition_text
                        ),
                    )
                )

    for f in module.functions:
        _scan(f, f.name, f.name)
    for c in module.classes:
        for m in c.methods:
            _scan(m, f"{c.name}.{m.name}", m.name)
    return out


# frob:doc docs/modules/arch.md#type-driven-design-checks
# frob:tests tests/unit/test_arch.py::TestRunTypeDesignChecks.test_combines_all_four_checks  # noqa: E501
def run_typedesign_checks(module: NormalizedModule) -> list[ArchSuggestion]:
    """Run every ARCH1xx type-driven-design check (T-0621:
    `check_illegal_states_representable`, `check_primitive_obsession`,
    `check_parse_dont_validate`, `check_boolean_flag_param`) against one
    `NormalizedModule` and return the combined suggestions, mirroring
    `frob.arch._srp.run_srp_checks`'s convention."""
    out: list[ArchSuggestion] = []
    out.extend(check_illegal_states_representable(module))
    out.extend(check_primitive_obsession(module))
    out.extend(check_parse_dont_validate(module))
    out.extend(check_boolean_flag_param(module))
    return out
