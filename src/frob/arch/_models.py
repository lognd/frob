"""Result models for the architectural analysis (docs/modules/arch.md's data shapes)."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel

# frob:doc docs/modules/arch.md#checks
ArchCategory = Literal[
    "long-function",
    "god-class",
    "high-coupling",
    "deep-nesting",
    "abstraction-opportunity",
    "large-file",
    # T-0332: advisory design-pattern recommender categories -- a detected
    # structural HALLMARK maps to a recommended GoF/modern PATTERN, or a
    # detected ANTI-PATTERN maps to a concrete ESCAPE route. Both stay on
    # the unwaivable advisory channel like every other category here
    # (`frob.gates._unwaivable_channel_rules`) -- see docs/modules/arch.md's
    # "design-pattern recommender" section for the registry.
    "pattern-recommendation",
    "anti-pattern-escape",
    # T-0616: SRP/cohesion family (ARCH1xx), written once against the T-0609
    # normalized model (`frob.arch._srp`) so each fires identically across
    # every `LanguageAdapter` -- see docs/modules/arch.md's "SRP/cohesion
    # checks" section for the per-category proxy definition.
    "low-cohesion-class",
    "god-module",
    "mixed-concern-function",
    # T-0617: OCP checks (ARCH1xx family, T-0330's SOLID catalog). Both stay
    # on the unwaivable advisory channel like every other category here
    # (`frob.gates._unwaivable_channel_rules`) until a future ticket wires a
    # real ARCH1xx gate (the T-0289 pattern ARCH001 already established);
    # `symref`/`metric` are populated on every finding so that wiring is a
    # gate-side addition, not a re-instrumentation of these checks.
    "type-dispatch-smell",
    "non-exhaustive-enum-match",
    # T-0618: LSP (Liskov) checks (ARCH1xx family, T-0330's SOLID catalog),
    # written once against the T-0609 normalized model (`frob.arch._solid`)
    # so each fires identically across every `LanguageAdapter` -- see
    # docs/modules/arch.md's "LSP checks" section for the base<->override
    # resolution rule and per-category proxy definition. Same unwaivable
    # advisory channel as every other category here.
    "lsp-not-implemented-override",
    "lsp-signature-variance",
    "lsp-strengthened-precondition",
    "lsp-weakened-postcondition",
    "lsp-noop-override",
    # T-0619: ISP (Interface Segregation) checks (ARCH1xx family, T-0330's
    # SOLID catalog), written once against the T-0609 normalized model
    # (`frob.arch._solid`) so each fires identically across every
    # `LanguageAdapter` -- see docs/modules/arch.md's "ISP checks" section
    # for the resolved-implementer/wide-interface resolution rules. Same
    # unwaivable advisory channel as every other category here.
    "fat-interface",
    "narrow-client-usage",
    # T-0620: DIP (Dependency Inversion) checks (ARCH1xx family, T-0330's
    # SOLID catalog) -- `frob.arch._layering`. `dip-layering-violation` is
    # project-wide (a `frob.toml`-declared allowed-module-dependency graph,
    # resolved against actual imports, not a per-file `NormalizedModule`
    # check); `no-di-construction` IS written once against the T-0609
    # normalized model. See docs/modules/arch.md's "DIP layering contract"
    # and "no-DI construction smell" sections. Same unwaivable advisory
    # channel as every other category here.
    "dip-layering-violation",
    "no-di-construction",
    # T-0695: structural fork/pool hazard family (call-graph reachability,
    # not runtime tracing) -- `frob.arch._concurrency`. Every member stays
    # on the same unwaivable advisory channel as the categories above
    # (`frob.gates._unwaivable_channel_rules` picks up any new
    # `ArchCategory` value automatically); see docs/modules/arch.md's
    # "fork/pool hazards" section for the per-category detection shape.
    "pool-inside-pool",
    "fork-after-threads",
    "pipe-wait-deadlock",
    "self-join-deadlock",
    # T-0622: logging-discipline checks (ARCH1xx family, T-0330's
    # observability family) -- `frob.arch._logging_checks`, written once
    # against the T-0609 normalized model so each fires identically across
    # every `LanguageAdapter`. Same unwaivable advisory channel as every
    # other category here; see docs/modules/arch.md's "logging discipline
    # checks" section for the per-category detection shape and the
    # strata/arch observability boundary note.
    "unlogged-error-path",
    "unlogged-boundary",
    "print-as-diagnostic",
    # T-0623: fallibility-discipline checks (ARCH1xx family, T-0330's
    # error-handling family) -- `frob.arch._fallibility`, written once
    # against the T-0609 normalized model so each fires identically across
    # every `LanguageAdapter`. Same unwaivable advisory channel as every
    # other category here; see docs/modules/arch.md's "fallibility checks"
    # section for the per-category detection shape and the model-limit
    # disclosure for `unhandled-result`.
    "unhandled-result",
    "swallowed-exception",
    "recoverable-error-wrong-signature",
    "over-broad-except",
    # T-0624: misc design-smell checks (ARCH1xx family, T-0330's
    # catch-all family) -- `frob.arch._smells`, written once against the
    # T-0609 normalized model so each fires identically across every
    # `LanguageAdapter`. Same unwaivable advisory channel as every other
    # category here; see docs/modules/arch.md's "misc design smells"
    # section for the per-category detection shape and disclosed
    # per-module (not project-wide) scoping limits.
    "mutable-default-arg",
    "feature-envy",
    "data-clumps",
    "magic-literal",
    "dead-private-code",
    "deep-inheritance",
    "temporal-coupling",
    # T-0625: module dependency cycle detection (ARCH1xx family, T-0330's
    # catch-all family) -- `frob.arch._smells.check_module_dependency_
    # cycles`, reusing `frob.cycle.graph.DependencyGraph`/`find_cycles`
    # (Tarjan's algorithm, no second graph builder forked). Same
    # unwaivable advisory channel as every other category here; see
    # docs/modules/arch.md's "module dependency cycles" section.
    "module-dependency-cycle",
    # T-0696: async event-loop hazard family (call-graph reachability,
    # syntactic co-occurrence -- not runtime tracing) -- child 3 of the
    # T-0693 concurrency-hazard umbrella, `frob.arch._async_hazards`. Every
    # member stays on the same unwaivable advisory channel as the
    # categories above (`frob.gates._unwaivable_channel_rules` picks up any
    # new `ArchCategory` value automatically); see
    # `frob.arch._async_hazards`'s module docstring for the per-category
    # detection shape (docs/modules/arch.md coverage tracked as a follow-up,
    # T-0914, out of T-0696's declared scope).
    "blocking-call-in-async",
    "nested-event-loop",
    "unawaited-coroutine",
    "async-zero-awaits",
    # T-0621/T-0892: type-driven-design checks (ARCH1xx family, T-0330's
    # fifth "Logan Smith" family alongside SRP/OCP/LSP/ISP/DIP) --
    # `frob.arch._typedesign`, written once against the T-0609 normalized
    # model so each fires identically across every `LanguageAdapter`.
    # Folded in from a local `TypeDesignCategory` literal (T-0892) once
    # `_models.py`'s scope lease freed up; see docs/modules/arch.md's
    # "type-driven design checks" section for the per-category detection
    # shape. Same unwaivable advisory channel as every other category here.
    "illegal-states-representable",
    "primitive-obsession",
    "parse-dont-validate",
    "boolean-flag-param",
    # T-0694: lock-ordering hazard family (interprocedural call-graph
    # reachability over statically-identifiable lock objects -- not runtime
    # tracing), child 2 of the T-0693 concurrency-hazard umbrella,
    # `frob.arch._lock_ordering`. Same unwaivable advisory channel as every
    # other category above (`frob.gates._unwaivable_channel_rules` picks up
    # any new `ArchCategory` value automatically); see
    # `frob.arch._lock_ordering`'s module docstring for the per-category
    # detection shape.
    "lock-order-cycle",
    "lock-identity-unresolved",
    # T-0697: shared-mutable-state race approximation (interprocedural
    # thread/task-dispatch reachability over statically-identifiable
    # module/class-level mutable state -- not runtime tracing), child 4 of
    # the T-0693 concurrency-hazard umbrella, `frob.arch._shared_state_
    # race`. Same unwaivable advisory channel as every other category above
    # (`frob.gates._unwaivable_channel_rules` picks up any new
    # `ArchCategory` value automatically); see
    # `frob.arch._shared_state_race`'s module docstring for the detection
    # shape.
    "unguarded-shared-write",
    # T-0698: concurrency model-mismatch advisory (IO-bound/CPU-bound
    # classification vs chosen dispatch executor), child 5 of the T-0693
    # concurrency-hazard umbrella, `frob.arch._concurrency_model`. Same
    # unwaivable advisory channel as every other category above
    # (`frob.gates._unwaivable_channel_rules` picks up any new
    # `ArchCategory` value automatically); see
    # `frob.arch._concurrency_model`'s module docstring for the detection
    # shape.
    "gil-bound-in-threadpool",
    "ipc-overhead-in-processpool",
    # T-0688: errors-as-values advisory (child 3 of T-0685's exception
    # may-raise umbrella, wires into T-0623's fallibility family) --
    # `frob.arch._exceptions.check_errors_as_values`, over
    # `frob.arch._mayraise.compute_may_raise`'s per-function sets. Same
    # unwaivable advisory channel as every other category here
    # (`frob.gates._unwaivable_channel_rules` picks up any new
    # `ArchCategory` value automatically); see
    # docs/modules/gates.md#errors-as-values-advisory-t-0688 for the detection
    # shape. Not yet dispatched by `analyze_project`'s live per-file walk
    # -- see `_exceptions.py`'s own module docstring for why that wiring
    # is a disclosed follow-up, not this ticket's own scope.
    "errors-as-values-recommended",
    # T-0687 (child 2 of T-0685's exception may-raise umbrella): a
    # `noexcept` C++ function reached (directly, or via same-file callee
    # propagation) by a may-throw or Unknown (unresolved-callee,
    # fail-closed) call with no encompassing `catch (...)` -- a hard
    # boundary violation (an escaping exception from `noexcept` is
    # `std::terminate` at runtime, not a recoverable condition), hence
    # `ArchSeverity` "error" rather than "warning"/"suggestion". See
    # `frob.arch._cpp_mayraise`'s module docstring.
    "cpp-noexcept-throws",
]

#: T-0687 added `"error"` (previously `warning`/`suggestion`/`info` were
#: the entire set) for a hard-boundary violation category
#: (`"cpp-noexcept-throws"`) whose
#: severity is not advisory -- an escaping exception from a `noexcept`
#: function is `std::terminate` at runtime, not a recoverable condition a
#: caller can choose to act on later. Promoting `"error"`-severity
#: `ArchSuggestion`s into an enforced, unwaivable gate finding (the way
#: `frob.gates._unwaivable_channel_rules` already does for every OTHER
#: `ArchCategory`) is `src/frob/gates/**` wiring, out of T-0687's own
#: declared scope (`src/frob/arch/**`/`src/frob/lang/**`/
#: `tests/unit/test_arch.py` alone) -- filed as a follow-up, same T-0728
#: "built and tested first, dispatch wiring landed later" precedent
#: `frob.arch._exceptions.check_errors_as_values`'s own module docstring
#: already establishes for exactly this class of scope carve-out.
# frob:doc docs/modules/arch.md#arch-suggestion
ArchSeverity = Literal["warning", "suggestion", "info", "error"]


# frob:doc docs/modules/arch.md#arch-suggestion
class ArchSuggestion(BaseModel):
    file: str
    line: int | None = None
    category: ArchCategory
    severity: ArchSeverity
    message: str
    detail: str | None = None
    # T-0289: set for checks that are about exactly one symbol (currently
    # long-function) so `frob.gates`' ARCH001 job can bind a `frob:waive`
    # directive to the precise function (`path::qualname`) instead of the
    # whole file, and so a `ceiling=` waiver can compare against `metric`.
    symref: str | None = None
    # T-0289: the raw measured value the finding is about (e.g. a
    # long-function's line count) -- lets a reasoned waiver's `ceiling=N`
    # re-fire once the function outgrows the ceiling, instead of muting it
    # permanently.
    metric: int | None = None


# frob:doc docs/modules/arch.md#arch-result
class ArchResult(BaseModel):
    root: str
    suggestions: list[ArchSuggestion]

    # frob:ticket T-0588
    # frob:tests tests/unit/test_arch.py::TestArchResultFormat.test_as_text_clean_project  # noqa: E501
    def as_text(self) -> str:
        # frob:doc docs/modules/arch.md#arch-result
        if not self.suggestions:
            return "no architectural issues found"
        lines: list[str] = []
        for s in self.suggestions:
            loc = s.file
            if s.line is not None:
                loc = f"{loc}:{s.line}"
            lines.append(f"{loc}  {s.severity}  {s.category}")
            lines.append(f"  {s.message}")
            if s.detail:
                lines.append(f"  {s.detail}")
        return "\n".join(lines)

    # frob:ticket T-0588
    # frob:tests tests/unit/test_arch.py::TestArchResultFormat.test_as_json_has_suggestions_key  # noqa: E501
    def as_json(self) -> str:
        # frob:doc docs/modules/arch.md#arch-result
        return json.dumps(self.model_dump(), indent=2)
