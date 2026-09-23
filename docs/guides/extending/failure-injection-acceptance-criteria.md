# Failure-injection acceptance criteria: name every field

## The incident this closes

F-307 H3-6: a prior audit named the general shape a health/probe
component's test must cover ("inject a failing dependency, assert the
probe reports it"). A fix satisfied the written acceptance-criteria row
("reports db and redis") LITERALLY -- it applied the failure-injection
assertion to the `db` field but never to the roll-up `status` field,
which stayed constant `"ok"` through the whole incident. The row was
written loosely, the fix matched it to the letter, and the gap between
"satisfies the written row" and "actually asserts on everything the
row's INTENT covers" went unnoticed until the incident.

This is a PROCESS rule about how a test-plan acceptance row gets
written, not a code-analysis rule -- no runnable check exists (or is
proposed here) that inspects ticket/acceptance-criteria TEXT for shape;
this repo has no precedent for that class of check, and inventing a
speculative AST check against ticket prose is out of scope for this fix.
This doc is the authoring guidance itself, so the next person (or agent)
writing a failure-injection acceptance criterion has the rule and a
worked example in front of them at write time.

## The rule

A failure-injection acceptance criterion for a health/probe/status-
roll-up component MUST do one of:

1. Name EVERY field of the response the test asserts on -- not just the
   field under direct test (the dependency you are injecting the
   failure into), but every other field the response carries, roll-up
   fields included; or
2. Explicitly call out which fields are deliberately excluded from the
   assertion, and why (e.g. "excludes `request_id`: opaque per-request
   value, not a function of dependency health").

A criterion naming only the injected dependency's own field is
under-specified: it lets a fix that flips that one field while leaving
every other field (most importantly a roll-up `status`/`ok`/`healthy`
field) silently wrong still satisfy the row to the letter.

## Worked example

**BAD** (the H3-6 incident shape -- names only the field under direct
test, silently permits the roll-up field to go unchecked):

> Acceptance: when redis is unreachable, the health endpoint reports
> `redis: down`.

A fix satisfying this row literally can leave `status: "ok"` in the same
response and still pass -- exactly what happened.

**GOOD** (names every response field the failure-injection test must
assert on):

> Acceptance: when redis is unreachable, the health endpoint's response
> reports `redis: down` AND `status: degraded` (the roll-up field) AND
> `db: ok` (the unaffected dependency stays reported correctly, proving
> the roll-up is computed from live state, not hardcoded per-branch).
> Excludes `checked_at`: a timestamp, not a function of dependency
> health.

The GOOD row leaves no field of the response unaccounted for: each one
is either asserted on directly, or excluded with a stated reason. A test
written against the GOOD row cannot pass while a roll-up field silently
stays constant through the failure injection.

## When writing a failure-injection acceptance criterion

1. List every field the response under test actually returns (read the
   response model / handler, not just the ticket's own prose -- the
   prose is what you are about to write, not a source of truth for it).
2. For each field, either name it in the assertion or state why it is
   excluded.
3. If the component is a health/probe/status roll-up specifically,
   the roll-up field (`status`, `ok`, `healthy`, or whatever this
   component calls its summary) is never implicitly excluded -- it is
   the field most likely to be wrong exactly because it is computed
   from every other field, not read directly off the injected failure.
