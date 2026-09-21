"""T-4951 litmus fixture: the negative control (crying-wolf guard) for
`design/litmus/forbid_rules.strata`'s `clean_worker` node -- mentions
`eval` only in a comment and inside a string literal, never as a real
call, so `forbid_rules_gate` must produce NO finding against this file.
"""

# eval() is exactly what std.policy.analyzable's forbid_call rule bans --
# this comment names it but calls nothing.

_WARNING_TEXT = "never call eval() on untrusted input"


def _describe_policy() -> str:
    """Return the warning text above -- no forbidden call anywhere here."""
    return _WARNING_TEXT
