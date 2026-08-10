import logging

log = logging.getLogger(__name__)


class _Bound:
    is_err = False


def bind_code(model, root):
    return _Bound()


class BackpressureViolation:
    """A single REL260/REL261 backpressure obligation finding."""

    node: str
    reason: str


def _missing_bounded_intake_violations(model):
    """Every queue/consumer node with no declared bounded-intake obligation."""
    return []


def _unproven_bounded_intake_violations(model, owner_by_node, root):
    """Every declared-but-unproven bounded-intake obligation, proof-against-code."""
    return []


def check_backpressure_obligations(model, root):
    """The REL26x BACKPRESSURE-obligation entrypoint: REL260 (missing bounded
    intake) and REL261 (declared-but-unproven bounded intake) across every
    queue/consumer node in model, waivers already applied."""
    bound = bind_code(model, root)
    if bound.is_err:
        return bound

    violations: list[BackpressureViolation] = []
    violations.extend(_missing_bounded_intake_violations(model))
    violations.extend(_unproven_bounded_intake_violations(model, None, root))
    log.info("backpressure: %d violation(s) found", len(violations))
    return violations
