"""Data shapes for the smart-dup pipeline (docs/modules/dup.md's Public API section).

Every model is a frozen pydantic `BaseModel`, matching `frob.graph._models`'
posture: a `CloneReport` must compare and cache by identity-of-value, not
identity-of-object, so the DUP001/DUP002 gate rules can be pure functions
over it.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict
from typani import ErrorSet

__all__ = [
    "AntiUnifyTemplate",
    "CloneBinding",
    "CloneMatchGroup",
    "CloneRegion",
    "ClonePair",
    "CloneReport",
    "CloneTemplate",
    "DupConfig",
    "DupError",
    "DupStats",
    "ProbeVerdict",
]


# frob:doc docs/modules/dup.md#dup-error
class DupError(ErrorSet):
    """Failure values `find_clones`/`probe_equivalence` can return.

    `CoreUnavailable` is the no-silent-fallback rule (docs/modules/dup.md's Rust
    core section): rungs R3+ need `frob_core`; when it is not importable,
    callers get this error rather than a quietly degraded result.
    """

    CoreUnavailable = "frob-core native extension is not installed"
    NotPure = "Probe target has effects; observational probing refused"
    CacheCorrupt = "dup cache unreadable; delete .frob/dup.db to rebuild"
    NoGenerator = "no frob.fuzz Arbitrary generator for a probe parameter"
    SmtUnavailable = "z3-solver not installed; install with: uv pip install frob[smt]"
    SmtUnsupported = "function body is outside R7's bounded int/bool subset"
    HoleCeilingExceeded = (
        "anti-unification template is >50% holes; not a meaningful generalization"
    )


# frob:doc docs/modules/dup.md#clone-region
class CloneRegion(BaseModel):
    """A symbol, or a contiguous statement slice inside one, in match output."""

    model_config = ConfigDict(frozen=True)

    ref: str
    span: tuple[int, int]


# frob:doc docs/modules/dup.md#clone-pair
class ClonePair(BaseModel):
    """One region-to-region match at a given rung, with line alignment."""

    model_config = ConfigDict(frozen=True)

    left: CloneRegion
    right: CloneRegion
    similarity: float
    rung: str
    alignment: tuple[tuple[int, int], ...] = ()


# frob:doc docs/modules/dup.md#dup-stats
class DupStats(BaseModel):
    """Per-`find_clones` counters: how much work ran and how much was cached."""

    model_config = ConfigDict(frozen=True)

    fingerprinted: int = 0
    cache_hits: int = 0
    pairs_verified: int = 0


# frob:doc docs/modules/dup.md#clone-binding
class CloneBinding(BaseModel):
    """One hole's concrete side in a `CloneTemplate`: which member, which subtree.

    `source_text` is a structural skeleton rendering of the bound subtree
    (`label(child, child, ...)`), not literal source text -- `frob.lang.TreeNode`
    (docs/modules/lang.md) does not carry source spans/text today, so the
    report shows the bound subtree's shape rather than its exact characters.
    See docs/modules/dup.md's "Reverse-templating report" section for why.
    """

    model_config = ConfigDict(frozen=True)

    hole: int
    region: CloneRegion
    source_text: str


# frob:doc docs/modules/dup.md#clone-template
class CloneTemplate(BaseModel):
    """A clone group's generalized skeleton: shared structure plus per-hole bindings.

    `skeleton_text` is the anti-unified template (docs/modules/dup.md's
    "Anti-unification (Plotkin lgg)" section) rendered as readable
    `label(child, ...)` text with `$hole_N` at each divergence point.
    `bindings` holds one tuple of `CloneBinding` per distinct group member,
    in the same order every member's binding list uses the same hole ids
    (`build_group_template`'s per-member re-anti-unification against the
    folded template keeps hole numbering stable across members -- see
    `frob.dup._template`). `suggested_signature` is advisory text embedded
    in DUP001's message, never an auto-applied patch (every other frob gate
    is conformance-only; this one is no different).
    """

    model_config = ConfigDict(frozen=True)

    skeleton_text: str
    holes: tuple[int, ...] = ()
    bindings: tuple[tuple[CloneBinding, ...], ...] = ()
    suggested_signature: str = ""


# frob:doc docs/modules/dup.md#clone-group
class CloneMatchGroup(BaseModel):
    """One clone group: its region-pairs plus an optional reverse-templating report.

    `template` is `None` whenever anti-unification could not produce a
    meaningful generalization for this group -- a member's subtree could
    not be recovered, `frob_core` is not installed, or the hole-ceiling
    sanity check tripped (docs/modules/dup-sota-survey.md sec 4). Callers
    fall back to the plain `pairs` with no synthesized report in that case,
    never a low-value near-all-holes template.
    """

    model_config = ConfigDict(frozen=True)

    pairs: tuple[ClonePair, ...] = ()
    template: CloneTemplate | None = None


# frob:doc docs/modules/dup.md#clone-report
class CloneReport(BaseModel):
    """The whole result of one `find_clones` call: grouped pairs plus stats."""

    model_config = ConfigDict(frozen=True)

    groups: tuple[CloneMatchGroup, ...] = ()
    stats: DupStats = DupStats()


# frob:doc docs/modules/dup.md#dup-config
class DupConfig(BaseModel):
    """The `[dup]` table in frob.toml (docs/modules/dup.md's config block).

    `region_kernel_enabled` gates the R1.5 exact-region kernel
    independently of the whole-symbol rungs (R1-R5): it is `False` by
    default so a default `frob check` never pays the extra suffix-array
    pass, even when `[dup].enforce` is already on. Set `[dup].region_kernel
    = true` in frob.toml to opt in.

    `inline_calls` gates helper-inlining triage (T-0288, docs/modules/dup.md's
    "Helper-inlining triage" section): before fingerprinting, a symbol's
    body is spliced with the bodies of the PRIVATE helpers it calls (a
    bounded `frob.graph.callgraph` closure), so arch-forced small-helper
    splits do not hide Type-3/4 duplication. `inline_max_depth` /
    `inline_max_nodes` bound that closure (cycle-guarded, public-API
    stopping, falls back to the un-inlined body past the cap).
    `helper_min_tokens` is the (lower) `min_tokens` floor `find_helper_clones`
    uses for its dedicated pass over the private-helper population, so
    families of near-identical TINY helpers -- themselves usually below the
    whole-symbol `min_tokens` default -- are not silently skipped.
    """

    model_config = ConfigDict(frozen=True)

    threshold: float = 0.85
    min_tokens: int = 40
    cache_entries: int = 200_000
    region_kernel_enabled: bool = False
    region_min_tokens: int = 15
    inline_calls: bool = True
    inline_max_depth: int = 3
    inline_max_nodes: int = 12
    helper_min_tokens: int = 8


# frob:doc docs/modules/dup.md#anti-unification-plotkin-lgg
class AntiUnifyTemplate(BaseModel):
    """Plotkin lgg output: a generalized node array plus per-side hole bindings.

    `labels`/`parents` are the template in the same `(labels, parents)`
    node-array shape `apted_similarity` consumes -- shared nodes keep their
    original label, divergence points carry a `$hole_N` placeholder.
    `bindings_a`/`bindings_b` each hold one `(hole_id, node_index)` pair per
    hole, naming which concrete subtree (in the corresponding input tree's
    node-index space) that hole generalizes over. Only ever constructed for
    a template that passed the hole-ceiling sanity check (frob.dup._core's
    `anti_unify`); a >50%-holes result is `Err(DupError.HoleCeilingExceeded)`
    instead, never a low-value `AntiUnifyTemplate`.
    """

    model_config = ConfigDict(frozen=True)

    labels: tuple[str, ...]
    parents: tuple[int, ...]
    bindings_a: tuple[tuple[int, int], ...] = ()
    bindings_b: tuple[tuple[int, int], ...] = ()


# frob:doc docs/modules/dup.md#probe-verdict
class ProbeVerdict(BaseModel):
    """R6 result: whether two effect-free candidates behaved identically."""

    model_config = ConfigDict(frozen=True)

    left: str
    right: str
    equivalent: bool
    cases_run: int
    counterexample: Mapping[str, str] | None = None
