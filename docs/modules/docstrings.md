# Docstring standard (T-2988)

Supersedes the blanket "every public symbol gets a one-line docstring"
rule. That rule is both ignored in practice (see the measured baseline
below) and no longer what the project wants: it is not a line budget, it
is a purpose test, and the right bar differs by how visible a symbol is.

This document states the standard; DOCARCH001 (`frob.gates.
_docstring_archaeology`, cataloged in [gates.md](gates.md#rule-catalog))
enforces the one half of it that is mechanically checkable.

## The purpose test

A docstring exists to illuminate a symbol's UTILITY. The operative
question, for every docstring written or reviewed:

> Would this make it clearer to a reader -- explicitly including an LLM --
> how and when to REUSE this code?

If yes, the docstring earns its length. A long docstring doing that job
is not bloat: it is doing exactly what a docstring is for. If no, it
should not be there at all -- **absence is a valid, intentional state**,
not a gap to be filled. A function simple enough that its name and
signature already say everything a caller needs does not need a
docstring padding out that fact.

## Narrative belongs in tickets, not code

Change narrative, justification, and history do NOT belong in a
docstring:

- why we arrived at this design over some prior one
- what an earlier attempt got wrong
- which policy or ticket superseded which

That is real and worth keeping -- this drive has repeatedly seen an
agent avoid repeating a landed mistake purely because a docstring
recorded it -- but its home is the ticket that did the deciding, not the
function that resulted from it. A docstring MAY carry a ticket
REFERENCE (`see T-0632 for the design rationale`, `T-1024: deliberately
dead by construction`); it must not carry the ARGUMENT itself. The
distinction is not "does it mention a ticket" -- most legitimate
provenance references do -- it is whether the prose reads as describing
a **change that happened** (used to, previously, folded into, replaced,
superseded, the old ...) versus a **property the code has now** (why an
invariant holds, what a non-obvious choice buys a caller).

## Three tiers, not one standard applied three times

The bar differs by visibility. Applying one rule uniformly is itself
part of what went wrong (see the measured baseline: private and public
functions are documented at almost the same rate today, which is the
opposite of what three real tiers would produce).

1. **Public API** (imported and used outside its own package boundary --
   `frob.gates`, `frob.tickets`, `frob.lang`'s exported surface, ...).
   Highest bar: a caller elsewhere in the codebase, or an adopter, has
   only the docstring and the signature to go on. Explain what it does,
   what it returns/raises, and any non-obvious contract (ordering,
   mutation, error behavior). Long is fine when every line is doing that
   job.

2. **Module-public** (no leading underscore, but not part of the
   package's exported surface -- an internal helper another function in
   the same module or a sibling module within the package calls).
   Middle bar: a one- or two-line docstring stating what it does and why
   it exists as its own function, when that is not obvious from the name
   and a five-second read of the body. Skip it when it is not.

3. **Private** (leading underscore). Lowest bar. Skip the docstring
   unless the function's behavior is genuinely non-obvious from its name,
   signature, and body -- most private helpers should have none. The
   measured baseline found private functions documented at 98%, almost
   the same rate as public; that is this tier's rule not being practiced
   at all, and the direction to correct in is fewer, not zero.

## Measured baseline (2026-08-26, AST walk over `src/**/*.py`)

| tier    | funcs | documented | undocumented | doc lines | avg  | cite a T-id |
|---------|-------|------------|---------------|-----------|------|-------------|
| public  |  1438 |       1304 |           134 |    13,882 | 10.6 |  747 (57%)  |
| private |  5575 |       5467 |           108 |    40,418 |  7.4 | 2829 (52%)  |

54% of docstrings cite a ticket id (3,576 of 6,771) -- most of that is
legitimate provenance reference, but the T-2988 worked example
(`frob.arch._python`'s tuple-returning function, roughly three of its
~20 docstring lines stating what it returns, the rest T-0632/T-0370
archaeology) shows the failure mode this document and DOCARCH001 exist
to correct.

## DOCARCH001

The detector: a public symbol's docstring cites a `T-####`/`T-draft-...`
id AND matches one of a curated set of change-narrative phrases ("used
to", "previously", "prior attempt", "folded into", "moved to/from",
"extracted from/to", "superseded", "replaced by", "the old", "the
prior", "historically", "now lives in/at", ...). Either alone is fine --
a bare ticket mention with no narrative wording is the normal shape of a
legitimate provenance reference; narrative wording with no ticket in
sight is ordinary prose about the code's current behavior. Only the
conjunction is flagged, WARNING-tier, waivable with `frob:waive
DOCARCH001 reason="..."` for a docstring the detector misreads. Private
symbols (leading underscore) are exempt outright -- tier 3's bar is
lower, and flagging archaeology there would relitigate the same
over-documentation problem on the tier that should have the LEAST
ceremony, not more.

## Migration

Moving existing archaeology into its cited ticket is real work, done
incrementally, never by mass-stripping to hit a number -- see T-2988's
Done report for the archived-ticket write-path hazard that must be
proven safe on one ticket before any batch, and this document's own
history for what has been migrated so far. `frob:waive DOCARCH001
reason="..."` covers a docstring the detector misreads while a real
migration is pending.
