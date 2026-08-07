## Done report
Validates std.host `owns` MODE (3-4 octal digits via _MODE_RE) and `listens`
PORT (1-65535) at manifest construction time via pydantic field_validators --
a non-octal mode (`rwx`), out-of-range mode (`999`), or bad/out-of-range/
non-numeric port now fails closed as a malformed manifest instead of being
silently accepted (deferred from T-0255). Mode stays a platform-opaque string
(POSIX octal today; Windows ACL later under T-0261) -- shape-validated, not
type-narrowed. New TestHostOwnsModeValidation + TestHostManifestListensValidation
assertions (bad rejected, valid accepted). Coordinator self-reviewed (agent
stalled on a background make coverage before finishing): host tests green,
ruff/format/ty clean, pydantic-idiomatic validation.
