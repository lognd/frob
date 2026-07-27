"""REL39x reliability family (continued): ABI/ISA COMPAT-WINDOW +
BOOT-CHAIN ATTESTATION obligations (T-0962, filed while reconciling
T-0958's `system-design.yaml` deferred rows: SDC-13-A-DECLARED-ABI-ISA-
TARGET-IS-STABLE-ACROSS-A-COMPATIBILITY-WINDOW-A-COMPILED-ARTIFA and
SDC-13-EVERY-BOOT-CHAIN-STAGE-IS-SIGNED-SECURE-BOOT-OR-MEASURED-INTO-AN-
ATTESTABLE-LOG-MEA). Mirrors `_process_bounds.py`'s REL39x structure
exactly (module docstring precedent, T-0646/T-0919/T-0960/...: one rule
module per obligation-pair-family, same `Report`/`Violation` pydantic
pair, registration/exemption from `_waive.py::
MULTI_INSTANCE_WAIVER_FAMILIES`, CLI wiring left as its own follow-up
ticket -- the same posture `_backpressure.py`/`_interactive_cost.py`/
`_process_bounds.py` are already in, not yet threaded into
`frob.app.sys_runner._run_audit`). Rule ids continue the REL39x block
`_process_bounds.py` (T-0960) started (REL390-REL393), rather than
opening a new REL4xx numbering -- both tickets were filed from the same
T-0958 reconciliation pass and share the "declaration + proof over
strata's own host/deploy vocabulary" shape.

TWO OBLIGATION PAIRS, each NODE-scoped (a node has at most one marker
attr per pair and fires at most one missing/unproven finding each --
single-instance-per-node, the same carve-out `_backpressure.py`'s
REL260/REL261, `_interactive_cost.py`'s REL310/REL311, and
`_process_bounds.py`'s REL390/REL391/REL392/REL393 pairs establish,
NEITHER pair registered in `MULTI_INSTANCE_WAIVER_FAMILIES`):

  - REL394 missing ABI/ISA compat-window declaration / REL395 unproven
    ABI/ISA compat-window: a node marked `compiled_artifact` (this node
    is a compiled binary/library targeting a declared ABI/ISA) needs a
    declared `abi_compat_window` attr (the compatibility window this
    artifact claims to honor); REL395 then requires real code-level
    evidence of a compat-window-shaped construct (a version/ABI-guard
    check, a semver range assertion, a symbol-versioning script) in that
    node's bound code, per the T-0331 PROVABILITY CONSTRAINT. Deny-by-
    default: a compiled artifact with no declared compat window has no
    tracked boundary for when a caller's assumption about its ABI/ISA
    stops holding.
  - REL396 missing boot-chain attestation / REL397 unproven boot-chain
    attestation: a node marked `boot_chain_stage` (this node models a
    stage in a boot chain -- firmware, bootloader, kernel, initrd) needs
    a declared `boot_attested` attr (this stage is signed via secure
    boot or measured into an attestable log); REL397 then requires real
    code-level evidence of a signing/measurement-shaped construct in
    that node's bound code. Deny-by-default: an unattested boot-chain
    stage has no cryptographic or measured record that it ran as
    expected, so a compromised stage inserted ahead of it is
    undetectable by design.

GRAMMAR-DATA CEILING, HONESTLY: `compiled_artifact`/`abi_compat_window`/
`boot_chain_stage`/`boot_attested` are all bare Node attrs (no numeric
magnitude -- the same digit-led-literal ceiling `strata-core/src/parse.rs`'s
generic `attr KEY=VALUE` clause imposes on every other REL2xx/REL3xx
marker), so REL394-REL397 prove PRESENCE of a declared obligation and its
code-level evidence, not a specific ABI version string or a specific
signature/measurement algorithm. This module is a static declaration-and-
proof check over strata's own host/deploy vocabulary, NOT runtime kernel
or firmware introspection -- it cannot observe an actual compiled
artifact's actual ABI surface or an actual boot chain's actual
measurement log, only whether the DECLARATION and its bound-code
evidence exist (the same honesty line REL201/REL222/REL231/REL261/
REL301/REL311/REL390-REL393 already establish for their own dimensions).
No `strata-core` change needed (this ticket's scope is
`src/frob/strata/**`/`docs/strata/**`/`tests/unit/strata/**` only, same
as T-0646/T-0919/T-0960's).
"""
# frob:waive INV006 reason="T-0962 first-turn-on: this module's 'only'/ 'deliberately \
# narrow' hits are source-level design-rationale/scope-cut prose mirroring \
# _backpressure.py's own identical waiver for the identical reason (module docstring \
# precedent), not a separate cross-module contract"

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

#: `frob sys audit` rule id for REL394 missing ABI/ISA compat-window
#: declaration: a `compiled_artifact` node with no `abi_compat_window`
#: attr declared.
# frob:doc docs/strata/reliability.md#rel39y-abi-compat-window--boot-attestation-t-0962
REL_MISSING_ABI_COMPAT_WINDOW = "REL394"

#: `frob sys audit` rule id for REL395 unproven ABI/ISA compat-window: a
#: node declares `abi_compat_window`, but its bound code has no real
#: compat-window-shaped token (PROVABILITY CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel39y-abi-compat-window--boot-attestation-t-0962
REL_UNPROVEN_ABI_COMPAT_WINDOW = "REL395"

#: `frob sys audit` rule id for REL396 missing boot-chain attestation: a
#: `boot_chain_stage` node with no `boot_attested` attr declared.
# frob:doc docs/strata/reliability.md#rel39y-abi-compat-window--boot-attestation-t-0962
REL_MISSING_BOOT_ATTESTATION = "REL396"

#: `frob sys audit` rule id for REL397 unproven boot-chain attestation: a
#: node declares `boot_attested`, but its bound code has no real
#: signing/measurement-shaped token (PROVABILITY CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel39y-abi-compat-window--boot-attestation-t-0962
REL_UNPROVEN_BOOT_ATTESTATION = "REL397"

#: Every REL39x (continued) rule id this module can emit -- this module's
#: own, narrow family for `_apply_supply_chain_boot_waivers`' `in_scope`
#: (the "never a shared superset" discipline `_reliability.py`'s module
#: docstring documents the real regression for).
# frob:doc docs/strata/reliability.md#rel39y-abi-compat-window--boot-attestation-t-0962
SUPPLY_CHAIN_BOOT_RULES: frozenset[str] = frozenset(
    {
        REL_MISSING_ABI_COMPAT_WINDOW,
        REL_UNPROVEN_ABI_COMPAT_WINDOW,
        REL_MISSING_BOOT_ATTESTATION,
        REL_UNPROVEN_BOOT_ATTESTATION,
    }
)

#: Node attr marking a compiled binary/library targeting a declared
#: ABI/ISA -- the REL394/REL395 population.
_COMPILED_ARTIFACT_ATTR = "compiled_artifact"

#: Node attr discharging the REL394 compat-window obligation
#: (presence-only, module docstring's grammar-data ceiling).
_ABI_COMPAT_WINDOW_ATTR = "abi_compat_window"

#: Node attr marking a stage in a boot chain (firmware, bootloader,
#: kernel, initrd) -- the REL396/REL397 population.
_BOOT_CHAIN_STAGE_ATTR = "boot_chain_stage"

#: Node attr discharging the REL396 attestation obligation
#: (presence-only, module docstring's grammar-data ceiling).
_BOOT_ATTESTED_ATTR = "boot_attested"

#: Regex proving a real ABI/ISA compat-window-shaped token in bound
#: source text (REL395) -- deliberately narrow (a syntactic token scan,
#: not a semantic call-argument binding), matching common compat-window
#: shapes: a semver/version-range guard (`semver`, `version_range`,
#: `compat_window`, `abi_version`), a symbol-versioning construct
#: (`symbol_version`, `soname`, `abi_break`), or an explicit
#: deprecation-window check. Same honesty line `_backpressure.py::
#: _BOUNDED_INTAKE_TOKEN_RE`'s docstring already establishes: not a claim
#: the matched token proves the SAME compat window the node models, only
#: that the node's bound code contains real evidence of a compat-window
#: construct.
_ABI_COMPAT_WINDOW_TOKEN_RE = re.compile(
    r"(semver|version_range|compat_window|abi_version|symbol_version|"
    r"soname|abi_break|deprecat)",
    re.IGNORECASE,
)

#: Regex proving a real signing/measurement-shaped token in bound source
#: text (REL397) -- deliberately narrow, matching common boot-attestation
#: shapes: a secure-boot/signature verification construct (`secure_boot`,
#: `verify_signature`, `signature_valid`, `codesign`), or a measured-boot
#: construct (`measured_boot`, `\bpcr\b`, `tpm`, `attestation_log`). Same
#: honesty line as `_ABI_COMPAT_WINDOW_TOKEN_RE` above: not a claim the
#: matched token attests the SAME boot chain the node models, only that
#: the node's bound code contains real evidence of a signing/measurement
#: construct.
_BOOT_ATTESTATION_TOKEN_RE = re.compile(
    r"(secure_boot|verify_signature|signature_valid|codesign|"
    r"measured_boot|\bpcr\b|\btpm\b|attestation_log)",
    re.IGNORECASE,
)


# frob:doc docs/strata/reliability.md#rel39y-abi-compat-window--boot-attestation-t-0962
class SupplyChainBootViolation(BaseModel):
    """One REL394-REL397 finding: rule id, the node, a human-readable
    detail. `sub_target` stays `None` -- single-instance-per-node (module
    docstring: at most one finding per rule per node), the same bare-rule
    waiver carve-out REL260/REL261/REL310/REL311/REL390-REL393 use.
    Mirrors `_process_bounds.py::ProcessBoundsViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel39y-abi-compat-window--boot-attestation-t-0962
class SupplyChainBootReport(BaseModel):
    """Every UNWAIVED REL394-REL397 finding, plus `waived` (T-0174
    channel, kept for report visibility, never silently dropped). Mirrors
    `_process_bounds.py::ProcessBoundsReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[SupplyChainBootViolation, ...] = ()
    waived: tuple[SupplyChainBootViolation, ...] = ()


def _is_compiled_artifact(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the `compiled_artifact` marker --
    the REL394/REL395 population."""
    return _COMPILED_ARTIFACT_ATTR in attrs


def _has_abi_compat_window(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the bare `abi_compat_window`
    marker."""
    return _ABI_COMPAT_WINDOW_ATTR in attrs


def _is_boot_chain_stage(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the `boot_chain_stage` marker --
    the REL396/REL397 population."""
    return _BOOT_CHAIN_STAGE_ATTR in attrs


def _has_boot_attested(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the bare `boot_attested`
    marker."""
    return _BOOT_ATTESTED_ATTR in attrs


def _missing_abi_compat_window_violations(
    model: KernelModel,
) -> list[SupplyChainBootViolation]:
    """REL394: every `compiled_artifact` node with no `abi_compat_window`
    attr."""
    violations: list[SupplyChainBootViolation] = []
    for node in model.nodes:
        if not _is_compiled_artifact(node.attrs) or _has_abi_compat_window(node.attrs):
            continue
        _log.warning(
            "supply_chain_boot: REL394 node %s is a compiled artifact with "
            "no ABI/ISA compat-window declared",
            node.id,
        )
        violations.append(
            SupplyChainBootViolation(
                rule=REL_MISSING_ABI_COMPAT_WINDOW,
                node=node.id,
                detail=(
                    f"node {node.id} is a compiled artifact with no "
                    "ABI/ISA compat-window obligation (no "
                    "`abi_compat_window` attr) -- a compiled artifact with "
                    "no declared compat window has no tracked boundary for "
                    "when a caller's ABI/ISA assumption stops holding"
                ),
            )
        )
    return violations


def _unproven_abi_compat_window_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[SupplyChainBootViolation]:
    """REL395: every `compiled_artifact` node declaring
    `abi_compat_window` with bound code, but whose bound code carries no
    real compat-window-shaped token (PROVABILITY CONSTRAINT). Mirrors
    `_process_bounds.py::_unproven_interface_classification_violations`
    exactly, parameterized on `_ABI_COMPAT_WINDOW_TOKEN_RE`."""
    violations: list[SupplyChainBootViolation] = []
    for node in model.nodes:
        if not _is_compiled_artifact(node.attrs) or not _has_abi_compat_window(
            node.attrs
        ):
            continue
        if not node_has_bound_code(node.id, owner_by_node):
            continue
        if files_evidence_token(
            owner_by_node[node.id], root, _ABI_COMPAT_WINDOW_TOKEN_RE
        ):
            continue
        _log.warning(
            "supply_chain_boot: REL395 node %s declares abi_compat_window "
            "but bound code has no real compat-window token",
            node.id,
        )
        violations.append(
            SupplyChainBootViolation(
                rule=REL_UNPROVEN_ABI_COMPAT_WINDOW,
                node=node.id,
                detail=(
                    f"node {node.id} declares abi_compat_window, but its "
                    "bound code has no real compat-window token "
                    "(proof-against-code, T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _missing_boot_attestation_violations(
    model: KernelModel,
) -> list[SupplyChainBootViolation]:
    """REL396: every `boot_chain_stage` node with no `boot_attested`
    attr."""
    violations: list[SupplyChainBootViolation] = []
    for node in model.nodes:
        if not _is_boot_chain_stage(node.attrs) or _has_boot_attested(node.attrs):
            continue
        _log.warning(
            "supply_chain_boot: REL396 node %s is a boot-chain stage with "
            "no attestation declared",
            node.id,
        )
        violations.append(
            SupplyChainBootViolation(
                rule=REL_MISSING_BOOT_ATTESTATION,
                node=node.id,
                detail=(
                    f"node {node.id} is a boot-chain stage with no "
                    "attestation obligation (no `boot_attested` attr) -- an "
                    "unattested boot-chain stage has no cryptographic or "
                    "measured record it ran as expected"
                ),
            )
        )
    return violations


def _unproven_boot_attestation_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[SupplyChainBootViolation]:
    """REL397: every `boot_chain_stage` node declaring `boot_attested`
    with bound code, but whose bound code carries no real signing/
    measurement-shaped token (PROVABILITY CONSTRAINT). Mirrors
    `_process_bounds.py::_unproven_process_bounds_violations` exactly,
    parameterized on `_BOOT_ATTESTATION_TOKEN_RE`."""
    violations: list[SupplyChainBootViolation] = []
    for node in model.nodes:
        if not _is_boot_chain_stage(node.attrs) or not _has_boot_attested(node.attrs):
            continue
        if not node_has_bound_code(node.id, owner_by_node):
            continue
        if files_evidence_token(
            owner_by_node[node.id], root, _BOOT_ATTESTATION_TOKEN_RE
        ):
            continue
        _log.warning(
            "supply_chain_boot: REL397 node %s declares boot_attested but "
            "bound code has no real signing/measurement token",
            node.id,
        )
        violations.append(
            SupplyChainBootViolation(
                rule=REL_UNPROVEN_BOOT_ATTESTATION,
                node=node.id,
                detail=(
                    f"node {node.id} declares boot_attested, but its bound "
                    "code has no real signing/measurement token "
                    "(proof-against-code, T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_supply_chain_boot_waivers(
    model: KernelModel, violations: list[SupplyChainBootViolation]
):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_process_bounds.py::_apply_process_bounds_waivers`'s pattern reused
    for this family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in SUPPLY_CHAIN_BOOT_RULES,
    )


# frob:doc docs/strata/reliability.md#rel39y-abi-compat-window--boot-attestation-t-0962
# frob:ticket T-0962
# frob:tests tests/unit/strata/test_supply_chain_boot.py::TestMissingAbiCompatWindow.test_compiled_artifact_node_without_compat_window_fires  # noqa: E501
def check_supply_chain_boot_obligations(
    model: KernelModel, root: Path
) -> Result[SupplyChainBootReport, StrataError]:
    """The REL394-REL397 ABI/ISA COMPAT-WINDOW + BOOT-CHAIN-ATTESTATION
    obligations entrypoint (T-0962): REL394/REL395 (ABI/ISA compat-window,
    missing then unproven) and REL396/REL397 (boot-chain attestation,
    missing then unproven) across every relevant node in `model`, waivers
    already applied. `root` is the repo root `_code_binding.py::bind_code`
    binds against -- `Err` propagates `bind_code`'s
    `AmbiguousCodeBinding` unchanged (deny by default, the same
    discipline `check_process_bounds_obligations` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[SupplyChainBootViolation] = []
    violations.extend(_missing_abi_compat_window_violations(model))
    violations.extend(
        _unproven_abi_compat_window_violations(model, owner_by_node, root)
    )
    violations.extend(_missing_boot_attestation_violations(model))
    violations.extend(_unproven_boot_attestation_violations(model, owner_by_node, root))
    applied = _apply_supply_chain_boot_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        SupplyChainBootViolation(
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
        "supply_chain_boot: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(
        SupplyChainBootReport(violations=tuple(applied.kept) + stale, waived=waived)
    )


__all__ = [
    "REL_MISSING_ABI_COMPAT_WINDOW",
    "REL_MISSING_BOOT_ATTESTATION",
    "REL_UNPROVEN_ABI_COMPAT_WINDOW",
    "REL_UNPROVEN_BOOT_ATTESTATION",
    "SUPPLY_CHAIN_BOOT_RULES",
    "SupplyChainBootReport",
    "SupplyChainBootViolation",
    "check_supply_chain_boot_obligations",
]
