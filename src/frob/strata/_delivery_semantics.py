"""REL33x reliability family: DELIVERY-SEMANTICS obligation on queue
nodes (T-0652, child of the T-0331 systems-checks epic, docs/strata/
reliability.md), mirroring `_message_schema.py`'s REL32x structure
(module docstring precedent, T-0646/.../T-0651: one rule module per
obligation, same `Report`/`Violation` pydantic pair, NOT registered in
`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`). SHARES the `queue` node-attr
population `_message_schema.py`'s REL32x family already established
(module docstring precedent there: "queue is reused unchanged from
`_backpressure.py`") -- this module adds a THIRD orthogonal obligation on
the same `queue` population, alongside REL26x's bounded-intake and REL32x's
schema-version.

A queue node with no declared delivery semantics leaves consumers unable
to reason about duplicate/loss risk: a consumer written assuming
exactly_once processing silently double-applies side effects against an
at_least_once queue (or vice versa -- a consumer written idempotent
"just in case" pays needless dedup cost against a genuinely exactly_once
queue), with no declared contract to catch the mismatch.

TWO RULES, both NODE-scoped (a node has at most one `queue` marker and
fires at most one REL330/REL331 finding each -- single-instance-per-node,
the same carve-out `_message_schema.py`'s REL320/REL321 pair already
establishes, NOT registered in `MULTI_INSTANCE_WAIVER_FAMILIES`):

  - REL330 missing/invalid delivery semantics: a `queue` node with no
    `delivery=<value>` attr declared, OR one declared whose value is not
    one of the fixed two (`DELIVERY_SEMANTICS`: `exactly_once`,
    `at_least_once`). Deny-by-default: an undeclared or malformed
    delivery-semantics value gives a consumer nothing to reason against --
    the grammar's generic `attr KEY=IDENT` clause
    (`strata-core/src/parse.rs::Parser::parse_attrval`, already exercised
    by its own `attr delivery=at_least_once;` parser fixture) cannot
    validate the two-value catalog at parse time (the same disclosure
    `_pii.py`'s PII001 catalog check makes for `carries` tags), so this
    is a structural check here.
    Folding the catalog check into REL330 (rather than a third rule)
    mirrors `_pii.py::check_pii_catalog`'s precedent that a malformed
    declaration is itself a form of "not declared" -- the ticket's own
    acceptance criterion ("no delivery-semantics declared ... fires")
    covers both the absent and the malformed case identically: neither
    gives a consumer a real contract to code against.
  - REL331 unproven delivery semantics: a queue node DOES declare a
    valid `delivery=<value>`, but the T-0331 PROVABILITY CONSTRAINT
    forbids discharging it by bare declaration alone -- the node must
    have at least one file bound to it (`_obligation_proof.py::
    node_has_bound_code`) containing a real delivery-semantics-shaped
    token (an idempotency-key/dedup construct for `exactly_once`, an
    ack/retry/redelivery construct for `at_least_once`). A node with no
    bound code at all is UNCHECKABLE, not unproven -- the same ceiling
    REL201/REL222/REL231/REL261/REL271/REL281/REL291/REL301/REL311/REL321
    draw.

GRAMMAR-DATA CEILING, HONESTLY: `delivery=<value>` is an IDENT-valued
attr (the same `retention=<value><unit>` convention `_compliance.py`
establishes, not a bare presence-only marker like `queue`/`bounded_intake`
-- this family genuinely needs a two-way distinction, so it reuses the
existing value-attr desugar convention rather than inventing a new kernel
primitive; the grammar's `ATTRVAL := IDENT ['=' IDENT]` production forces
underscore-joined values, `exactly_once`/`at_least_once`, not the
hyphenated spelling common in prose -- the same "ship what the parser
already accepts" honesty this family's every sibling states), so
REL330/REL331 prove PRESENCE of one of exactly two
catalogued values and its code-level evidence, not a specific broker
configuration or dedup-window size. No `strata-core` change needed (this
ticket's scope is `src/frob/strata/**`/`docs/strata/**`/
`tests/unit/strata/**` only, same as T-0640/.../T-0651's).
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's \
# 'only' hits are source-level design-rationale/scope-cut prose mirroring \
# _message_schema.py's own identical waiver for the identical reason \
# (module docstring precedent, T-0652), not a separate cross-module \
# contract"

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._code_binding import bind_code
from ._errors import StrataError
from ._models import KernelModel
from ._obligation_proof import files_evidence_token, node_has_bound_code, owner_index
from ._waive import apply_waivers

_log = get_logger(__name__)

#: `frob sys audit` rule id for REL330 missing/invalid delivery
#: semantics: a `queue` node with no `delivery=<value>` attr, or a value
#: not in `DELIVERY_SEMANTICS`.
# frob:doc docs/strata/reliability.md#rel33x-delivery-semantics-obligation-t-0652  # noqa: E501
REL_MISSING_DELIVERY_SEMANTICS = "REL330"

#: `frob sys audit` rule id for REL331 unproven delivery semantics: a
#: node declares a valid `delivery=<value>`, but its bound code has no
#: real delivery-semantics-shaped token (PROVABILITY CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel33x-delivery-semantics-obligation-t-0652  # noqa: E501
REL_UNPROVEN_DELIVERY_SEMANTICS = "REL331"

#: Every REL33x rule id this module can emit -- this module's own, narrow
#: family for `_apply_delivery_semantics_waivers`' `in_scope` (the "never
#: a shared superset" discipline `_reliability.py`'s module docstring
#: documents the real regression for).
# frob:doc docs/strata/reliability.md#rel33x-delivery-semantics-obligation-t-0652  # noqa: E501
DELIVERY_SEMANTICS_RULES: frozenset[str] = frozenset(
    {REL_MISSING_DELIVERY_SEMANTICS, REL_UNPROVEN_DELIVERY_SEMANTICS}
)

#: Node attr marking a message/work queue -- reused unchanged from
#: `_backpressure.py`/`_message_schema.py` (module docstring: the third
#: orthogonal obligation on this population).
_QUEUE_ATTR = "queue"

#: Node attr value-prefix a `delivery=<value>` surface statement
#: desugars to (mirrors `_compliance.py::_RETENTION_PREFIX`'s value-attr
#: convention).
_DELIVERY_PREFIX = "delivery="

#: The fixed two delivery-semantics values (ticket body: "exactly_once
#: vs at_least_once").
# frob:doc docs/strata/reliability.md#rel33x-delivery-semantics-obligation-t-0652  # noqa: E501
DELIVERY_SEMANTICS: frozenset[str] = frozenset({"exactly_once", "at_least_once"})

#: Regex proving a real delivery-semantics-shaped token in bound source
#: text (REL331) -- deliberately narrow (a syntactic token scan, not a
#: semantic call-argument binding), matching common delivery-semantics
#: constructs: an idempotency-key/dedup construct (`exactly_once`'s
#: usual implementation shape) or an ack/nack/redelivery/retry construct
#: (`at_least_once`'s usual implementation shape). Same honesty line
#: `_message_schema.py::_SCHEMA_VERSION_TOKEN_RE`'s docstring already
#: establishes: not a claim the matched token implements the SAME
#: semantics the node declares, only that the node's bound code contains
#: real evidence of a delivery-semantics construct.
_DELIVERY_SEMANTICS_TOKEN_RE = re.compile(
    r"(idempotenc\w*|dedup\w*|idempotency_key|\back\(|\bnack\(|redeliver\w*|"
    r"at_least_once|exactly_once|\bretry\b)",
    re.IGNORECASE,
)


# frob:doc docs/strata/reliability.md#rel33x-delivery-semantics-obligation-t-0652  # noqa: E501
class DeliverySemanticsViolation(BaseModel):
    """One REL33x finding: rule id, the node, a human-readable detail.
    `sub_target` stays `None` -- single-instance-per-node (module
    docstring: at most one REL330/REL331 finding each), the same bare-
    rule waiver carve-out REL320/REL321 use. Mirrors
    `_message_schema.py::MessageSchemaViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel33x-delivery-semantics-obligation-t-0652  # noqa: E501
class DeliverySemanticsReport(BaseModel):
    """Every UNWAIVED REL33x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_message_schema.py::MessageSchemaReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[DeliverySemanticsViolation, ...] = ()
    waived: tuple[DeliverySemanticsViolation, ...] = ()


def _is_queue(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the `queue` marker -- the
    REL330/REL331 population (module docstring)."""
    return _QUEUE_ATTR in attrs


def _declared_delivery_semantics(attrs: tuple[str, ...]) -> str | None:
    """The node's declared `delivery=<value>` value, or `None` if no
    `delivery=` attr is present at all (distinct from a present-but-
    invalid value, which this returns verbatim for the caller to
    catalog-check)."""
    for attr in attrs:
        if attr.startswith(_DELIVERY_PREFIX):
            return attr[len(_DELIVERY_PREFIX) :]
    return None


def _missing_or_invalid_delivery_semantics_violations(
    model: KernelModel,
) -> list[DeliverySemanticsViolation]:
    """REL330: every `queue` node with no `delivery=` attr, or a value
    not in `DELIVERY_SEMANTICS` (module docstring: folded into one rule,
    the `_pii.py::check_pii_catalog` precedent that malformed counts as
    undeclared)."""
    violations: list[DeliverySemanticsViolation] = []
    for node in model.nodes:
        if not _is_queue(node.attrs):
            continue
        value = _declared_delivery_semantics(node.attrs)
        if value in DELIVERY_SEMANTICS:
            continue
        _log.warning(
            "delivery_semantics: REL330 node %s is queue with no valid "
            "delivery-semantics declaration (got %r)",
            node.id,
            value,
        )
        detail = (
            f"node {node.id} is a queue with no declared delivery-semantics "
            "obligation (no `delivery=` attr)"
            if value is None
            else (
                f"node {node.id} declares delivery={value!r}, which is not "
                f"one of {sorted(DELIVERY_SEMANTICS)}"
            )
        )
        violations.append(
            DeliverySemanticsViolation(
                rule=REL_MISSING_DELIVERY_SEMANTICS,
                node=node.id,
                detail=detail,
            )
        )
    return violations


def _unproven_delivery_semantics_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[DeliverySemanticsViolation]:
    """REL331: every `queue` node declaring a valid `delivery=<value>`
    with bound code, but whose bound code carries no real delivery-
    semantics-shaped token (PROVABILITY CONSTRAINT). Mirrors
    `_message_schema.py::_unproven_schema_version_violations` exactly,
    parameterized on `_DELIVERY_SEMANTICS_TOKEN_RE`."""
    violations: list[DeliverySemanticsViolation] = []
    for node in model.nodes:
        if not _is_queue(node.attrs):
            continue
        value = _declared_delivery_semantics(node.attrs)
        if value not in DELIVERY_SEMANTICS:
            continue
        if not node_has_bound_code(node.id, owner_by_node):
            continue
        if files_evidence_token(
            owner_by_node[node.id], root, _DELIVERY_SEMANTICS_TOKEN_RE
        ):
            continue
        _log.warning(
            "delivery_semantics: REL331 node %s declares delivery=%s but "
            "bound code has no real delivery-semantics token",
            node.id,
            value,
        )
        violations.append(
            DeliverySemanticsViolation(
                rule=REL_UNPROVEN_DELIVERY_SEMANTICS,
                node=node.id,
                detail=(
                    f"node {node.id} declares delivery={value!r}, but its "
                    "bound code has no real delivery-semantics token "
                    "(proof-against-code, T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_delivery_semantics_waivers(
    model: KernelModel, violations: list[DeliverySemanticsViolation]
):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_message_schema.py::_apply_message_schema_waivers`'s pattern reused
    for the REL33x family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in DELIVERY_SEMANTICS_RULES,
    )


# frob:doc docs/strata/reliability.md#rel33x-delivery-semantics-obligation-t-0652  # noqa: E501
# frob:ticket T-0652
# frob:tests tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics.test_queue_node_without_delivery_semantics_fires  # noqa: E501
def check_delivery_semantics_obligations(
    model: KernelModel, root: Path
) -> Result[DeliverySemanticsReport, StrataError]:
    """The REL33x DELIVERY-SEMANTICS-obligation entrypoint (T-0652):
    REL330 (missing/invalid delivery semantics) and REL331 (declared-but-
    unproven delivery semantics, proof-against-code) across every queue
    node in `model`, waivers already applied. `root` is the repo root
    `_code_binding.py::bind_code` binds against -- `Err` propagates
    `bind_code`'s `AmbiguousCodeBinding` unchanged (deny by default, the
    same discipline `check_message_schema_obligations` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[DeliverySemanticsViolation] = []
    violations.extend(_missing_or_invalid_delivery_semantics_violations(model))
    violations.extend(
        _unproven_delivery_semantics_violations(model, owner_by_node, root)
    )
    applied = _apply_delivery_semantics_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        DeliverySemanticsViolation(
            rule="RELWAIVE002",
            node=stale_waiver.node,
            sub_target=stale_waiver.rule,
            detail=(
                f"waive {stale_waiver.rule!r} on node {stale_waiver.node} "
                f"reason={stale_waiver.reason!r} is stale -- no matching "
                f"finding fired this run"
            ),
        )
        for stale_waiver in applied.stale
    )
    _log.info(
        "delivery_semantics: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(
        DeliverySemanticsReport(violations=tuple(applied.kept) + stale, waived=waived)
    )


__all__ = [
    "DELIVERY_SEMANTICS",
    "DELIVERY_SEMANTICS_RULES",
    "REL_MISSING_DELIVERY_SEMANTICS",
    "REL_UNPROVEN_DELIVERY_SEMANTICS",
    "DeliverySemanticsReport",
    "DeliverySemanticsViolation",
    "check_delivery_semantics_obligations",
]
