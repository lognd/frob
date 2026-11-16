# Ack

Status: current
Owner: frob
Decisions: none
Audience: user

An ack is a recorded acknowledgement that a code symbol and the doc
section that describes it were read together and still agree. `frob
ack` stores the digests of both sides in `frob.lock`. While those
digests match the current content, the pair is in sync; when either
side changes, DRIFT001 fires until the pair is re-read and acked
again.

Pairs are bound with a `frob:doc path#section` directive on the symbol
or a `frob:describes` directive in the doc. Run `frob ack` after
reviewing both sides; it rewrites only the digests, never the code or
the doc. Commit the updated `frob.lock` with the change.

An ack is a human statement, not a waiver: it says "I checked, they
agree". To except a finding without re-reading, use a reasoned
`frob:waive` instead.

See also: [obligation](obligation.md), [cycle](cycle.md).
