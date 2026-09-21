"""T-4951 litmus fixture: a real, planted violation of std.policy.analyzable's
`forbid call eval, exec` rule (positive control -- memory/positive-control-
or-it-proves-nothing.md).

This file exists ONLY to be bound as `worker`'s code in
design/litmus/forbid_rules.strata; it is not imported or exercised by
anything else in the repo.
"""


def _run_untrusted(expr: str) -> object:
    """Evaluate `expr` dynamically -- exactly what `std.policy.analyzable`
    forbids: this call is the planted FORBID001 finding (deliberate, not
    an oversight -- see this file's own module docstring)."""
    return eval(expr)
