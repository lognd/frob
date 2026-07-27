"""REL32x reliability family: MESSAGE SCHEMA VERSION obligation on
event/queue nodes (T-0651, child of the T-0331 systems-checks epic,
docs/strata/reliability.md), mirroring `_backpressure.py`'s REL26x
structure (module docstring precedent, T-0646/T-0650/T-0919: one rule
module per obligation, same `Report`/`Violation` pydantic pair, NOT
registered in `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`). An event or
queue node with no declared message schema version has no backward-compat
tracking: a producer and consumer can silently drift onto incompatible
message shapes with no version boundary to detect the break.

TWO RULES, both NODE-scoped (a node has at most one `event`/`queue`
marker pairing and fires at most one REL320/REL321 finding each --
single-instance-per-node, the same carve-out `_backpressure.py`'s
REL260/REL261 pair already establishes, NOT registered in
`MULTI_INSTANCE_WAIVER_FAMILIES`):

  - REL320 missing schema version: a node marked `event` or `queue` (this
    node models a published event or a message/work queue -- both
    populations that carry a message payload across a producer/consumer
    boundary) with no `schema_version` attr declared. Deny-by-default: an
    event/queue with no declared schema version has no backward-compat
    tracking -- a producer can change the message shape with no version
    boundary for a consumer to detect the break against.
  - REL321 unproven schema version: a node DOES declare `schema_version`,
    but the T-0331 PROVABILITY CONSTRAINT forbids discharging it by bare
    declaration alone -- the node must have at least one file bound to it
    (`_obligation_proof.py::node_has_bound_code`) containing a real
    schema-version-shaped token. A node with no bound code at all is
    UNCHECKABLE, not unproven -- the same ceiling REL201/REL222/REL231/
    REL261/REL271/REL281/REL291/REL301 draw.

GRAMMAR-DATA CEILING, HONESTLY: `event`/`queue`/`schema_version` are all
presence-only bare Node attrs (no numeric magnitude -- the same digit-
led-literal ceiling every other REL2xx/REL3xx marker in this family
discloses), so REL320/REL321 prove PRESENCE of a declared schema-version
obligation and its code-level evidence, not a specific version number or
compatibility policy. No `strata-core` change needed (this ticket's
scope is `src/frob/strata/**`/`docs/strata/**`/`tests/unit/strata/**`
only, same as T-0640/T-0641/.../T-0651's).

`event` is a NEW node-attr marker this module introduces (module
docstring's population is "event/queue"; `_backpressure.py`'s `queue`/
`consumer` markers cover the buffering/draining side but not a bare
published-event node with no queue semantics of its own) -- `queue` is
reused unchanged from `_backpressure.py` (a queue is simultaneously
subject to REL260/REL261's bounded-intake obligation AND this module's
REL320/REL321 schema-version obligation; the two families are
orthogonal, not exclusive).
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's \
# 'only' hits are source-level design-rationale/scope-cut prose mirroring \
# _backpressure.py's own identical waiver for the identical reason (module \
# docstring precedent, T-0651), not a separate cross-module contract"

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

#: `frob sys audit` rule id for REL320 missing schema version: an
#: `event`/`queue` node with no `schema_version` attr declared.
# frob:doc docs/strata/reliability.md#rel32x-message-schema-version-obligation-t-0651  # noqa: E501
REL_MISSING_SCHEMA_VERSION = "REL320"

#: `frob sys audit` rule id for REL321 unproven schema version: a node
#: declares `schema_version`, but its bound code has no real schema-
#: version-shaped token (PROVABILITY CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel32x-message-schema-version-obligation-t-0651  # noqa: E501
REL_UNPROVEN_SCHEMA_VERSION = "REL321"

#: Every REL32x rule id this module can emit -- this module's own, narrow
#: family for `_apply_message_schema_waivers`' `in_scope` (the "never a
#: shared superset" discipline `_reliability.py`'s module docstring
#: documents the real regression for).
# frob:doc docs/strata/reliability.md#rel32x-message-schema-version-obligation-t-0651  # noqa: E501
MESSAGE_SCHEMA_RULES: frozenset[str] = frozenset(
    {REL_MISSING_SCHEMA_VERSION, REL_UNPROVEN_SCHEMA_VERSION}
)

#: Node attr marking a published event -- one half of the REL320/REL321
#: population (module docstring's new marker).
_EVENT_ATTR = "event"

#: Node attr marking a message/work queue -- the other half of the
#: REL320/REL321 population, reused unchanged from `_backpressure.py`.
_QUEUE_ATTR = "queue"

#: Node attr discharging the REL320 schema-version obligation (presence-
#: only, module docstring's grammar-data ceiling).
_SCHEMA_VERSION_ATTR = "schema_version"

#: Regex proving a real schema-version-shaped token in bound source text
#: (REL321) -- deliberately narrow (a syntactic token scan, not a
#: semantic call-argument binding), matching common message-schema-
#: versioning shapes: a `schema_version=`/`schemaVersion=` kwarg/field, an
#: `avro`/`protobuf`/`proto`-schema construct with a version marker, or a
#: literal `schema_version`/`SCHEMA_VERSION` identifier. Same honesty line
#: `_backpressure.py::_BOUNDED_INTAKE_TOKEN_RE`'s docstring already
#: establishes: not a claim the matched token versions the SAME event/
#: queue the node models, only that the node's bound code contains real
#: evidence of a schema-version construct.
_SCHEMA_VERSION_TOKEN_RE = re.compile(
    r"(schema[_]?version\s*[:=]|SCHEMA_VERSION|schema_registry|"
    r"avro.*schema|proto.*version)",
    re.IGNORECASE,
)


# frob:doc docs/strata/reliability.md#rel32x-message-schema-version-obligation-t-0651  # noqa: E501
class MessageSchemaViolation(BaseModel):
    """One REL32x finding: rule id, the node, a human-readable detail.
    `sub_target` stays `None` -- single-instance-per-node (module
    docstring: at most one REL320/REL321 finding each), the same bare-
    rule waiver carve-out REL260/REL261 use. Mirrors
    `_backpressure.py::BackpressureViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel32x-message-schema-version-obligation-t-0651  # noqa: E501
class MessageSchemaReport(BaseModel):
    """Every UNWAIVED REL32x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_backpressure.py::BackpressureReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[MessageSchemaViolation, ...] = ()
    waived: tuple[MessageSchemaViolation, ...] = ()


def _is_event_or_queue(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the `event` or `queue` marker --
    the REL320/REL321 population (module docstring)."""
    return _EVENT_ATTR in attrs or _QUEUE_ATTR in attrs


def _has_schema_version(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the bare `schema_version` marker."""
    return _SCHEMA_VERSION_ATTR in attrs


def _missing_schema_version_violations(
    model: KernelModel,
) -> list[MessageSchemaViolation]:
    """REL320: every `event`/`queue` node with no `schema_version` attr."""
    violations: list[MessageSchemaViolation] = []
    for node in model.nodes:
        if not _is_event_or_queue(node.attrs) or _has_schema_version(node.attrs):
            continue
        _log.warning(
            "message_schema: REL320 node %s is event/queue with no schema "
            "version declared",
            node.id,
        )
        violations.append(
            MessageSchemaViolation(
                rule=REL_MISSING_SCHEMA_VERSION,
                node=node.id,
                detail=(
                    f"node {node.id} is an event/queue with no declared "
                    "message-schema-version obligation (no `schema_version` "
                    "attr)"
                ),
            )
        )
    return violations


def _unproven_schema_version_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[MessageSchemaViolation]:
    """REL321: every `event`/`queue` node declaring `schema_version` with
    bound code, but whose bound code carries no real schema-version-
    shaped token (PROVABILITY CONSTRAINT). Mirrors `_backpressure.py::
    _unproven_bounded_intake_violations` exactly, parameterized on
    `_SCHEMA_VERSION_TOKEN_RE`."""
    violations: list[MessageSchemaViolation] = []
    for node in model.nodes:
        if not _is_event_or_queue(node.attrs) or not _has_schema_version(node.attrs):
            continue
        if not node_has_bound_code(node.id, owner_by_node):
            continue
        if files_evidence_token(owner_by_node[node.id], root, _SCHEMA_VERSION_TOKEN_RE):
            continue
        _log.warning(
            "message_schema: REL321 node %s declares schema_version but bound "
            "code has no real schema-version token",
            node.id,
        )
        violations.append(
            MessageSchemaViolation(
                rule=REL_UNPROVEN_SCHEMA_VERSION,
                node=node.id,
                detail=(
                    f"node {node.id} declares schema_version, but its bound "
                    "code has no real schema-version token (proof-against-"
                    "code, T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_message_schema_waivers(
    model: KernelModel, violations: list[MessageSchemaViolation]
):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_backpressure.py::_apply_backpressure_waivers`'s pattern reused for
    the REL32x family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in MESSAGE_SCHEMA_RULES,
    )


# frob:doc docs/strata/reliability.md#rel32x-message-schema-version-obligation-t-0651  # noqa: E501
# frob:ticket T-0651
# frob:tests tests/unit/strata/test_message_schema.py::TestMissingSchemaVersion.test_queue_node_without_schema_version_fires  # noqa: E501
def check_message_schema_obligations(
    model: KernelModel, root: Path
) -> Result[MessageSchemaReport, StrataError]:
    """The REL32x MESSAGE-SCHEMA-VERSION-obligation entrypoint (T-0651):
    REL320 (missing schema version) and REL321 (declared-but-unproven
    schema version, proof-against-code) across every event/queue node in
    `model`, waivers already applied. `root` is the repo root
    `_code_binding.py::bind_code` binds against -- `Err` propagates
    `bind_code`'s `AmbiguousCodeBinding` unchanged (deny by default, the
    same discipline `check_backpressure_obligations` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[MessageSchemaViolation] = []
    violations.extend(_missing_schema_version_violations(model))
    violations.extend(_unproven_schema_version_violations(model, owner_by_node, root))
    applied = _apply_message_schema_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        MessageSchemaViolation(
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
        "message_schema: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(
        MessageSchemaReport(violations=tuple(applied.kept) + stale, waived=waived)
    )


__all__ = [
    "MESSAGE_SCHEMA_RULES",
    "REL_MISSING_SCHEMA_VERSION",
    "REL_UNPROVEN_SCHEMA_VERSION",
    "MessageSchemaReport",
    "MessageSchemaViolation",
    "check_message_schema_obligations",
]
