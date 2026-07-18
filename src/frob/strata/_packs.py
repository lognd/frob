"""`std.policy.analyzable` mandatory base pack (docs/strata/policy.md#packs).

The pack is data, not code: a tuple of `PolicyDecl`s forbidding dynamic
code execution, reflection dispatch, and unconfined FFI -- the analyzable
subset that `enables extraction_soundness` (docs/strata/evidence.md#the-
enables-cascade) rests on. `require_analyzable` is the auto-inject seam
the elaborator calls: v0 amends policy.md to auto-supply the pack (with a
WARNING log) rather than erroring when a trusted component lacks it,
since the pack is mandatory and the tool is expected to guarantee it.
"""

from __future__ import annotations

from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._ast import ConfineUse, ForbidCall, Module, PolicyDecl, ScopeSpec
from ._errors import StrataError
from ._models import TRUST

_log = get_logger(__name__)

#: The mandatory base pack's policy id; matched by id for auto-inject and
#: for override detection (docs/strata/policy.md#packs).
ANALYZABLE_POLICY_ID = "std.policy.analyzable"

#: The soundness atom every base-pack rule enables (docs/strata/evidence.md
#: #the-enables-cascade): confinement/chokepoint L4 proofs are meaningless
#: without it.
EXTRACTION_SOUNDNESS = "extraction_soundness"

# frob:doc docs/strata/policy.md#packs
ANALYZABLE: tuple[PolicyDecl, ...] = (
    PolicyDecl(
        id=ANALYZABLE_POLICY_ID,
        scope=ScopeSpec(kind="trust", value="trusted"),
        rules=(
            # no eval/exec/dynamic import
            ForbidCall(
                idents=("eval", "exec", "importlib.import_module", "__import__")
            ),
            # no reflection dispatch; `setattr` here doubles as the
            # monkey-patching ban (docs/strata/policy.md#packs), so it is
            # not repeated as a separate rule
            ForbidCall(idents=("getattr", "setattr", "delattr")),
            # FFI only via frob bind
            ConfineUse(ident="ctypes", home="src/frob/strata/_ffi.py"),
            ConfineUse(ident="cffi", home="src/frob/strata/_ffi.py"),
        ),
        enables=(EXTRACTION_SOUNDNESS,),
        rationale=(
            "L4 soundness for every confinement/chokepoint policy assumes a "
            "closed, statically-visible call/import graph; dynamic code "
            "execution, reflection dispatch, and unconfined FFI each defeat "
            "the tree-sitter closure that makes that graph sound "
            "(docs/strata/evidence.md#the-enables-cascade).",
        ),
    ),
)


# frob:doc docs/strata/policy.md#packs
def require_analyzable(module: Module) -> Result[Module, StrataError]:
    """Auto-inject `std.policy.analyzable` when a trusted node lacks it.

    v0 amendment (docs/strata/policy.md#v0-implementation): the pack is
    mandatory, so the tool supplies it rather than failing the module,
    logged at WARNING since it silently changes what is checked. A module
    that already declares the pack id gets it left alone -- that is how a
    designer later overrides individual pack members. Fails closed only if
    a node's trust level cannot be checked against the lattice (unknown
    level name), never on the presence/absence of the pack itself.
    """
    has_trusted = False
    for node in module.nodes:
        leq = TRUST.leq("trusted", node.trust)
        if leq.is_err:
            return Err(leq.danger_err)
        if leq.danger_ok:
            has_trusted = True
            break

    already_present = any(p.id == ANALYZABLE_POLICY_ID for p in module.policies)
    if has_trusted and not already_present:
        _log.warning(
            "module %s: trusted component present without %s; "
            "auto-injecting mandatory base pack",
            module.name,
            ANALYZABLE_POLICY_ID,
        )
        return Ok(
            module.model_copy(update={"policies": (*module.policies, *ANALYZABLE)})
        )
    return Ok(module)
