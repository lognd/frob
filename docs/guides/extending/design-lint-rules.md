# Design-lint rules (LINT001-005)

<!-- frob:describes src/frob/strata/_lint.py::LintViolation -->

## What / where

`src/frob/strata/_lint.py` (T-0155). Unlike most registries in this
series, LINT is **not a flat data table** -- there is no single tuple you
append an entry to. Each rule is a bespoke checker function:
`check_lint_rate_limit` (LINT001), `check_lint_cache_or_capacity`
(LINT002), `check_lint_surge_capacity_bound` (LINT003), `check_lint_kill_
switch` (LINT004, consumes `RISKY_CAPABILITY_KINDS` -- a narrower subset
of the vet capability vocabulary, see
[capability-registry.md](capability-registry.md)), `check_lint_fanin_
capacity` (LINT005). All emit `LintViolation` (rule id + firing target +
detail) collected into a `LintReport`.

## Add-an-entry recipe (LINT006+)

Adding a new lint rule means writing new code, not appending to a table:

1. Write `check_lint_<name>(model: KernelModel) -> tuple[LintViolation, ...]`
   following the existing checkers' shape (iterate nodes/flows/scenarios
   in a stable sorted order, emit `LintViolation(rule="LINT006", ...)`
   for each finding).
2. Wire it into the aggregator that calls all `check_lint_*` functions
   (grep `_lint.py`'s bottom-of-file `evaluate_lint`-equivalent or its
   test suite for the call site).
3. Update the `LintViolation.rule` docstring/comment enumerating LINT001-
   005 to include the new id.
4. If the new rule reuses a capability vocabulary, decide explicitly
   whether it wants the full sink taxonomy (`_threat.py`) or a narrower
   subset like LINT004's `RISKY_CAPABILITY_KINDS` -- do not assume one is
   a drop-in for the other.

## Drift-locks that fire

- No single generic "LINT completeness" gate exists (unlike THREAT001 or
  PII001) because there is no data catalog to check for completeness
  against -- completeness here means "every checker function is called by
  the aggregator," verified by ordinary test coverage on the aggregator,
  not a dedicated drift-lock rule.

## Worked example diff

```python
# src/frob/strata/_lint.py
def check_lint_new_rule(model: KernelModel) -> tuple[LintViolation, ...]:
    """LINT006: <one-line rule statement>."""
    violations: list[LintViolation] = []
    for node in sorted(model.nodes, key=lambda n: n.id):
        if <condition>:
            violations.append(
                LintViolation(rule="LINT006", target=node.id, detail="...")
            )
    return tuple(violations)
```

Then add the call to the aggregator and a unit test asserting both the
positive and negative case.

## Common mistakes

- **Expecting a data-table recipe.** This is the sharpest template
  deviation among frob's registries -- most guides in this series say
  "append an entry"; LINT genuinely requires new code. Do not go looking
  for a `LINT_RULES` tuple that does not exist.
- **Assuming LINT002 and LINT005 are redundant.** The module comment
  explicitly documents that a model can fail LINT002 (caching-covered
  node with a bad cache policy) and PASS LINT005 (jurisdiction-agnostic
  fan-in check, caching-blind) -- they intentionally check different
  things; do not merge or dedupe them under a "just check capacity"
  refactor.
- **Reusing the wrong capability vocabulary.** LINT004's `RISKY_
  CAPABILITY_KINDS` is deliberately smaller than `_threat.py`'s full sink
  taxonomy -- an operational kill-switch concern, not a security
  classification. Pulling in the full taxonomy for a new operational
  rule will over-fire.

## See also

- [Capability registry](capability-registry.md)
- [Threat catalog](threat-catalog.md)
