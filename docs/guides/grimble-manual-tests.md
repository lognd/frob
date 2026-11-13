# grimble manual tests: what `grimble status` lists and how to run each

Status: current
Owner: grimble
Decisions: D150
Audience: user

A manual test is a check a person performs, because no runner can. `grimble status`
ends with a `manual tests:` section that lists each one with the reason it is not run
by a machine. This page says how to read that list, how to declare a manual test, and
how to run each one.

## Read the listing

```text
grimble status --text
...
manual tests: 1
  manual: t_hand because needs a person at the console
```

Each row is `manual: <test anchor> because <reason>`. Rows are ordered by anchor.
`grimble status` (without `--text`) returns the same rows as `manual_tests`, a list of
`{test, reason}` objects. A model with none prints `manual tests: 0`; this repository's
own model currently declares none, so the list is empty here.

## Declare one

A test vmodel carries either `runnable` clauses or one `manual because="REASON";`,
never both, and the reason is never empty (MDL014; see
[MDL014](../reference/rules/MDL014.md)). Any other verifiable entity spells it
`verified_by manual because="REASON";` (D150).

```grmb expect=clean file=design/model.grmb
grimble = "2";
module m;
vmodel t_hand {
  kind test;
  level acceptance;
  manual because="needs a person at the console";
}
```

## Run each listed test

A manual test has no code term, so there is no command that runs it, and
`frob test` and `grimble check` never execute it. To run one:

1. Run `grimble status --text` and note each `manual:` row. The anchor names the test
   and the reason says what a machine cannot do (hardware, a console, a human judgement).
2. Find the anchor in the model (`grep -rn "<anchor>" design/`) and read the entity it
   verifies say what to check.
3. Perform the check by hand under the condition the reason names, for example at the
   console for "needs a person at the console".
4. Record the outcome where your project keeps verification results (the ticket, the
   release checklist). grimble does not store a pass or fail for a manual test.

The kernel counts manual evidence at the manual rung only: a claim that requires an
automated proof rung cannot be satisfied by a manual test and reports SYS010. To make a
manual test automatic, replace `manual because=` with a `runnable` clause (see
[grmb-spec 4.5](../design/grimble/grmb-spec.md)); it then leaves the status listing.

See also: [watching grants grow](grimble.md#watching-grants-grow) for the rest of
`grimble status`.
