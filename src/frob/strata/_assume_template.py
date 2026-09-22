"""frob.strata._assume_template -- templated-assume detector (D-M8, T-5105).

Owner decision D-M8 (OVERRIDDEN and strengthened from the original proposal,
recorded on T-draft-0a0c7b43): the 33 boilerplate CWE assumes SF-08 measured
in design/frob.strata (one identical `noflow registry -> <node> owner logan
review "2026-10-15"` shape repeated per node per weakness class) are NOT
carried into the split module design. An assume must be module-owned and
specific -- its `id` names the concrete mechanism or evidence gap for THAT
module, not a copy-pasted template with only the node name changed.

This module holds the pure detection logic (no `Violation`/gate wiring --
that lives in `frob.gates._sys_selfaudit`, mirroring every other SYS/SELF-
AUDIT sub-family's split between a `frob.strata` detector and a
`frob.gates` finding-shape wrapper):

- `find_templated_assumes`: two (or more) assumes are a finding when their
  PARSED shape is identical after substituting only the node identifier
  each assume is about -- a TOKEN-level comparison over the parsed
  `Claim`/`ClaimBody` fields (owner directive: checks decide from parsed
  symbols, never lexically/by keyword), never a raw source-line diff.
- `find_shared_expiry`: assumes sharing one `review` expiry date across
  more than `max_modules` modules (module = the file an assume's `.strata`
  source was elaborated from, per `KernelModel` -- T-draft-a693d397's
  kernel `module` attribute on `Node` had not landed when this leaf was
  written, so a module is identified by its source file, not yet by a
  first-class kernel field; `_sys_selfaudit._templated_assume_violations`
  narrows this to the real kernel attribute once that leaf lands).

Both functions are PURE: given already-elaborated `Claim`s (with an
explicit per-claim module label supplied by the caller), they return
plain dataclasses describing each finding group -- no I/O, no `Violation`
construction, so they are unit-testable without a design tree on disk.
"""
# frob:ticket T-5105

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

from ._models import Claim

_log = get_logger(__name__)

#: Token boundary for the template comparison: runs of alphanumerics plus
#: the punctuation an assume id/path commonly embeds (`.`, `-`, `_`). Any
#: other character (whitespace, `:`, quotes) is a separator -- so
#: `"weakness:CWE-78:vet"` tokenizes as `["weakness", "CWE-78", "vet"]`,
#: keeping the weakness class and the node name as DISTINCT tokens (a
#: different CWE class must never collapse into the same template as
#: another just because both mention the same node).
_TOKEN_RE = re.compile(r"[A-Za-z0-9_.\-]+")

#: Placeholder a substituted node/module token is rewritten to before two
#: assumes' token streams are compared -- an arbitrary sentinel that can
#: never collide with a real identifier token (the surrounding literal
#: angle brackets are not a token character per `_TOKEN_RE`).
_NODE_PLACEHOLDER = "NODEPLACEHOLDER"

#: Default N in "assumes sharing one expiry date across more than N
#: modules is a finding" -- `[gates.sys] assume_template_max_modules` in
#: frob.toml overrides it (`frob.gates._sys_selfaudit._assume_template_max_
#: modules`). Two is the smallest N that does not fire on an ordinary
#: pair of sibling modules sharing a single, deliberately-chosen sprint
#: review date -- three or more sharing one date is the actual "nobody
#: looked, it just got copied forward" smell SF-08 measured.
DEFAULT_MAX_MODULES = 2


# frob:doc \
# docs/strata/selfconform.md#sys119sys120----the-templated-assume-gate-d-m8-t-5105  # noqa: E501
# frob:tests \
# tests/gates_suite/test_sys_assume_template.py::TestFindTemplatedAssumes.test_red_on_monolith_cwe78_cluster  # noqa: E501
class TemplatedAssumeGroup(BaseModel):
    """One set of >=2 assumes whose parsed shape is IDENTICAL once each
    assume's own node identifier is substituted out -- the D-M8 definition
    of a templated (boilerplate) assume."""

    model_config = ConfigDict(frozen=True)

    signature: str
    claim_ids: tuple[str, ...]
    nodes: tuple[str, ...]
    modules: tuple[str, ...]


# frob:doc \
# docs/strata/selfconform.md#sys119sys120----the-templated-assume-gate-d-m8-t-5105  # noqa: E501
# frob:tests \
# tests/gates_suite/test_sys_assume_template.py::TestFindSharedExpiry.test_red_on_monolith_shared_date  # noqa: E501
class SharedExpiryGroup(BaseModel):
    """One `review` expiry date shared by assumes across more than N
    distinct modules -- D-M8's second templated-assume smell (a
    copy-forward date nobody actually re-reviewed per module)."""

    model_config = ConfigDict(frozen=True)

    review: str
    claim_ids: tuple[str, ...]
    modules: tuple[str, ...]


# frob:doc \
# docs/strata/selfconform.md#sys119sys120----the-templated-assume-gate-d-m8-t-5105  # noqa: E501
# frob:tests \
# tests/gates_suite/test_sys_assume_template.py::TestModuleClaimsFromModels.test_flattens_and_tags_each_claim_with_its_module  # noqa: E501
class ModuleClaim(BaseModel):
    """One assumed `Claim` plus the module label the caller resolved it
    to -- the unit both detector functions in this module operate over,
    keeping them independent of how a caller derives "module" (file stem
    today per T-draft-a693d397 not having landed yet, the real kernel
    `module` attribute once it does)."""

    model_config = ConfigDict(frozen=True)

    claim: Claim
    module: str


def _claim_node(claim: Claim) -> str | None:
    """The node/target identifier an assume is ABOUT: a `noflow`/`reach`
    body's `dst`, or a `bound` claim's `target` -- the field D-M8's "node
    or module name" substitution rewrites. `None` when the claim body
    carries neither (nothing to substitute, so the claim is excluded from
    template comparison rather than guessed at)."""
    body = claim.body
    dst = getattr(body, "dst", None)
    if isinstance(dst, str):
        return dst
    target = getattr(body, "target", None)
    if isinstance(target, str):
        return target
    return None


def _claim_tokens(claim: Claim) -> tuple[str, ...]:
    """Tokenize the claim's own PARSED fields (id, body kind + every body
    field, owner, review) -- never the raw `.strata` source line -- into
    the token stream `find_templated_assumes` compares. Field order is
    fixed so two structurally-equal claims always tokenize identically
    regardless of which fields happen to be set."""
    body = claim.body
    fields = [
        claim.id,
        type(body).__name__,
        getattr(body, "src", None),
        getattr(body, "dst", None),
        getattr(body, "metric", None),
        getattr(body, "target", None),
        getattr(body, "limit", None),
        claim.owner,
        claim.review,
    ]
    text = " ".join(str(field) for field in fields if field is not None)
    return tuple(_TOKEN_RE.findall(text))


def _template_signature(claim: Claim, *, module: str) -> str | None:
    """The claim's token stream with every occurrence of its own node
    identifier AND its own module label rewritten to `_NODE_PLACEHOLDER`
    -- two assumes with the same signature are identical after
    substituting only the node/module name, D-M8's exact test. Returns
    `None` when the claim has no node identifier (see `_claim_node`)."""
    node = _claim_node(claim)
    if node is None:
        return None
    placeholders = {node, module}
    tokens = _claim_tokens(claim)
    canon = tuple(_NODE_PLACEHOLDER if tok in placeholders else tok for tok in tokens)
    return " ".join(canon)


# frob:ticket T-5105
# frob:doc \
# docs/strata/selfconform.md#sys119sys120----the-templated-assume-gate-d-m8-t-5105  # noqa: E501
# frob:tests \
# tests/gates_suite/test_sys_assume_template.py::TestFindTemplatedAssumes.test_red_on_monolith_cwe78_cluster  # noqa: E501
# frob:tests \
# tests/gates_suite/test_sys_assume_template.py::TestFindTemplatedAssumes.test_distinct_weakness_class_not_merged  # noqa: E501
# frob:tests \
# tests/gates_suite/test_sys_assume_template.py::TestFindTemplatedAssumes.test_genuinely_specific_assume_not_reported  # noqa: E501
def find_templated_assumes(
    claims: Sequence[ModuleClaim],
) -> tuple[TemplatedAssumeGroup, ...]:
    """Group `claims` by `_template_signature` and return one
    `TemplatedAssumeGroup` per signature shared by 2 or more assumes --
    D-M8's structural refusal of a copy-pasted-with-the-node-renamed
    assume. A group of size 1 (a signature only one assume ever produces)
    is not a finding: nothing was templated FROM anything. Deterministic
    order: by signature, then by claim id within a group, so two runs
    over the same input never reorder findings."""
    by_signature: dict[str, list[Claim]] = defaultdict(list)
    module_by_id: dict[str, str] = {}
    for entry in claims:
        if not entry.claim.assumed:
            continue
        signature = _template_signature(entry.claim, module=entry.module)
        if signature is None:
            _log.debug(
                "find_templated_assumes: claim %s has no node identifier, "
                "excluded from template comparison",
                entry.claim.id,
            )
            continue
        by_signature[signature].append(entry.claim)
        module_by_id[entry.claim.id] = entry.module

    groups: list[TemplatedAssumeGroup] = []
    for signature in sorted(by_signature):
        members = sorted(by_signature[signature], key=lambda c: c.id)
        if len(members) < 2:
            continue
        groups.append(
            TemplatedAssumeGroup(
                signature=signature,
                claim_ids=tuple(claim.id for claim in members),
                nodes=tuple(
                    node
                    for node in (_claim_node(claim) for claim in members)
                    if node is not None
                ),
                modules=tuple(module_by_id[claim.id] for claim in members),
            )
        )
    _log.info(
        "find_templated_assumes: %d assume(s) evaluated, %d templated group(s) found",
        sum(len(v) for v in by_signature.values()),
        len(groups),
    )
    return tuple(groups)


# frob:ticket T-5105
# frob:doc \
# docs/strata/selfconform.md#sys119sys120----the-templated-assume-gate-d-m8-t-5105  # noqa: E501
# frob:tests \
# tests/gates_suite/test_sys_assume_template.py::TestFindSharedExpiry.test_red_on_monolith_shared_date  # noqa: E501
# frob:tests \
# tests/gates_suite/test_sys_assume_template.py::TestFindSharedExpiry.test_at_or_below_n_modules_not_reported  # noqa: E501
def find_shared_expiry(
    claims: Sequence[ModuleClaim],
    *,
    max_modules: int = DEFAULT_MAX_MODULES,
) -> tuple[SharedExpiryGroup, ...]:
    """One `SharedExpiryGroup` per `review` date shared by assumes across
    MORE than `max_modules` distinct modules -- D-M8's second templated-
    assume smell (a copy-forward review date nobody actually revisited
    per module). Assumes with no `review` set are excluded (nothing to
    compare). Deterministic order: by review date."""
    by_review: dict[str, list[Claim]] = defaultdict(list)
    module_by_id: dict[str, str] = {}
    modules_by_review: dict[str, set[str]] = defaultdict(set)
    for entry in claims:
        if not entry.claim.assumed or entry.claim.review is None:
            continue
        by_review[entry.claim.review].append(entry.claim)
        module_by_id[entry.claim.id] = entry.module
        modules_by_review[entry.claim.review].add(entry.module)

    groups: list[SharedExpiryGroup] = []
    for review in sorted(by_review):
        modules = modules_by_review[review]
        if len(modules) <= max_modules:
            continue
        members = sorted(by_review[review], key=lambda c: c.id)
        groups.append(
            SharedExpiryGroup(
                review=review,
                claim_ids=tuple(claim.id for claim in members),
                modules=tuple(sorted(modules)),
            )
        )
    _log.info(
        "find_shared_expiry: %d review date(s) evaluated (max_modules=%d), "
        "%d shared-expiry group(s) found",
        len(by_review),
        max_modules,
        len(groups),
    )
    return tuple(groups)


# frob:doc \
# docs/strata/selfconform.md#sys119sys120----the-templated-assume-gate-d-m8-t-5105  # noqa: E501
# frob:tests \
# tests/gates_suite/test_sys_assume_template.py::TestModuleClaimsFromModels.test_flattens_and_tags_each_claim_with_its_module  # noqa: E501
# frob:tests \
# tests/gates_suite/test_sys_assume_template.py::TestModuleClaimsFromModels.test_empty_mapping_yields_empty_tuple  # noqa: E501
def module_claims_from_models(
    models_by_module: Mapping[str, Sequence[Claim]],
) -> tuple[ModuleClaim, ...]:
    """Flatten a `{module_label: claims}` mapping into the `ModuleClaim`
    sequence both detector functions take -- the seam a caller (`frob.
    gates._sys_selfaudit`) uses to supply "module" however it currently
    resolves it (a source-file stem today, the real kernel `module`
    attribute once T-draft-a693d397 lands)."""
    return tuple(
        ModuleClaim(claim=claim, module=module)
        for module, claims in models_by_module.items()
        for claim in claims
    )


__all__ = [
    "DEFAULT_MAX_MODULES",
    "ModuleClaim",
    "SharedExpiryGroup",
    "TemplatedAssumeGroup",
    "find_shared_expiry",
    "find_templated_assumes",
    "module_claims_from_models",
]
