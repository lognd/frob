"""Pydantic schema classes (and the `_op` terse-constructor helper) shared
across every `frob.vet._capability_registry` table submodule -- split out
(T-1420) so the tables that consume these types do not each need their own
copy of the model definitions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _DangerousOperation(BaseModel):
    """One structured dangerous-operation entry (T-0158 addendum 1):
    a single builtin/stdlib/library function or literal pattern that
    grants `capability_kind`, with enough metadata (`cwe_links`,
    `rationale`, `safer_alternative`, `severity`) that an audit finding
    can name WHY it fired and what to do instead, not just a bare kind
    label."""

    model_config = ConfigDict(frozen=True)

    language: str
    library: str
    function_or_pattern: str
    capability_kind: str
    cwe_links: tuple[str, ...] = ()
    rationale: str
    safer_alternative: str
    severity: str  # "low" | "medium" | "high" | "critical"
    #: literal substring needle(s) `frob.vet._capability` matches against
    #: raw source text -- kept separate from `function_or_pattern` (the
    #: human-facing name) so a needle can differ cosmetically (e.g. a
    #: trailing `(` to avoid partial-identifier false positives).
    needles: tuple[str, ...] = ()


# T-0524: frob:doc removed -- CAPABILITY_MATRIX_EXCUSES (public, below)
# already carries the same docs/modules/vet.md#public-api anchor (COV007).
class _MatrixExcuse(BaseModel):
    """A written, specific reason a (kind, language) cell has NO
    `_DangerousOperation` entries -- T-0158 retires the old blanket C/C++
    exemption; every excused cell names its own missing idiom, never a
    boilerplate 'not applicable'."""

    model_config = ConfigDict(frozen=True)

    capability_kind: str
    language: str
    reason: str


def _op(
    language: str,
    library: str,
    function_or_pattern: str,
    capability_kind: str,
    rationale: str,
    safer_alternative: str,
    severity: str,
    needles: tuple[str, ...],
    cwe_links: tuple[str, ...] = (),
) -> _DangerousOperation:
    """Terse constructor so the table below reads as data, not boilerplate."""
    return _DangerousOperation(
        language=language,
        library=library,
        function_or_pattern=function_or_pattern,
        capability_kind=capability_kind,
        cwe_links=cwe_links,
        rationale=rationale,
        safer_alternative=safer_alternative,
        severity=severity,
        needles=needles,
    )


class _OpaqueConstruct(BaseModel):
    """One `docs/design/capability-evasion-taxonomy.md` "runtime-opaque"
    row that IS syntactically visible at the source-text level (T-0665,
    coordinator-signed category 1: "evasion-indicative dynamic lookup"):
    a call form whose determining argument is a NON-LITERAL expression --
    `eval`/`exec` (no literal split possible, always opaque), `getattr`/
    `setattr`/`__import__`/`importlib.import_module` with a non-literal
    name argument, `dlsym` with a non-literal symbol argument, JS/TS
    dynamic `import(expr)` with a non-literal specifier, and every
    reflection-API entry (`Class.forName`, `Method.invoke`,
    `KCallable.call`) which is opaque unconditionally -- reflection
    resolves through runtime metadata even when the class/method NAME
    literal is visible in source, unlike a plain import/attribute name.
    `literal_arg_index` is `None` for constructs that are always opaque
    regardless of any literal argument (`eval`, reflection); otherwise the
    0-based argument position `frob.vet._capability`'s heuristic checks for
    a literal (a string/byte-string literal there downgrades the site to
    the ordinary resolver path, per the coordinator's T-0665 sign-off:
    "literal-key lookups that resolve statically belong to the ordinary
    resolver path, not this gate")."""

    model_config = ConfigDict(frozen=True)

    language: str
    construct_name: str
    needle: str
    literal_arg_index: int | None
    rationale: str
    taxonomy_row: str


class _OpaqueStructuralConstruct(BaseModel):
    """One T-1051 "needle-architecture-blocked" taxonomy row that the
    fixed-needle-plus-literal-arg shape `_OpaqueConstruct` implements
    cannot express without an unacceptable false-positive rate: a
    SHAPE (subscript-then-call, or cast-then-call) rather than a fixed
    substring. `kind` selects which structural scanner in
    `frob.vet._capability` (`_structural_opaque_findings`) applies:
    `"subscript_call"` for `container[non_literal_key](...)` (python/
    typescript container-dynamic-key and computed-member rows, C/C++
    array-index function-pointer dispatch), `"explicit_fnptr_cast_call"`
    for `((RET(*)(ARGS))expr)(...)` (C/C++ integer-cast-to-function-
    pointer), and `"named_type_cast_call"` for `((TypeName)expr)(...)`
    (C/C++ void*-backcast-to-function-pointer through a typedef'd
    function-pointer type). Same disclosed-over-approximation posture as
    `_OpaqueConstruct`'s needles -- these scanners cannot confirm the
    subscript index or cast target TYPE without full type inference, so
    they fire on the STRUCTURAL SHAPE alone; false positives are
    waivable (category-1 doctrine, T-0665), consistent with the
    `libloading`/`.call(` entries' own precedent."""

    model_config = ConfigDict(frozen=True)

    language: str
    construct_name: str
    kind: str
    rationale: str
    taxonomy_row: str
