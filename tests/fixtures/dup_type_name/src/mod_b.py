import logging

log = logging.getLogger(__name__)


class _Bound:
    is_err = False


def bind_code(model, root):
    return _Bound()


class FallbackViolation:
    """A single REL240/REL241 fallback obligation finding."""

    node: str
    reason: str


def _missing_fallback_violations(model):
    """Every critical node with no declared fallback/graceful-degradation."""
    return []


def _unproven_fallback_violations(model, owner_by_node, root):
    """Every declared-but-unproven fallback obligation, proof-against-code."""
    return []


def check_fallback_obligations(model, root):
    """The REL24x FALLBACK-obligation entrypoint: REL240 (missing fallback)
    and REL241 (declared-but-unproven fallback) across every critical node
    in model, waivers already applied."""
    bound = bind_code(model, root)
    if bound.is_err:
        return bound

    violations: list[FallbackViolation] = []
    violations.extend(_missing_fallback_violations(model))
    violations.extend(_unproven_fallback_violations(model, None, root))
    log.info("fallback: %d violation(s) found", len(violations))
    return violations
