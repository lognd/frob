---
name: audit
description: Dispatch interface-auditor per package boundary plus security-auditor across the repo. Output is tickets, policy rules, and invariants -- no prose findings file. Use for a repo-wide or subtree quality/security sweep.
---

# audit

Sweep the repo, write findings only to the queue and to durable policy/
invariant artifacts. There is no findings-file output from this skill --
if it isn't a ticket, a policy rule, or an invariant, it didn't happen.

## Step 1: Enumerate boundaries

```bash
frob map src/                        # package layout
frob check --only test                # TEST003 already flags known interfaces
```

A package is a boundary if another package imports its public symbols.
List every such package before dispatching anything.

## Step 2: Dispatch interface-auditor, one mission per boundary

For each boundary package identified in Step 1, dispatch a fresh
`interface-auditor` mission scoped to exactly that package. Run these in
parallel where the harness allows -- each mission is independent and reads
only its own boundary plus its callers.

Do not dispatch one `interface-auditor` mission against the whole repo --
the agent's contract is one boundary per mission; a repo-wide dispatch
produces shallow, unscoped findings.

## Step 3: Dispatch security-auditor across the repo

One `security-auditor` mission, repo-wide (or scoped to the subtree named
in the goal, if this is a partial sweep). It returns policy rule ids,
invariant ids, and ticket ids -- verify all three lists are non-empty if
any real finding was reported.

## Step 4: Collect and dedupe

```bash
frob ticket list --kind bug --kind security --origin auditor
```

- [ ] No two tickets describe the same finding (auditors run independently
      and may overlap at a boundary both packages share)
- [ ] Every `security-auditor` finding has a matching policy rule or
      invariant id referenced in its ticket body
- [ ] Every ticket has a scope narrower than the audited package/repo

If two tickets duplicate a finding, close the weaker one as `dropped` with
a reason pointing at the surviving ticket -- do not silently ignore either.

## Step 5: Queue summary

End with a summary, not prose findings:

```
Audit sweep: N boundaries + repo-wide security pass

Interface findings:
- src/frob/graph: T-0051, T-0052
- src/frob/tickets: (clean)

Security findings:
- policy rules added: POL-no-shell-true
- invariants added: INV-012
- tickets filed: T-0053, T-0054

Total new tickets: T-0051, T-0052, T-0053, T-0054
```

## Hard rules

- Never fix anything in this skill. Both auditor agents are report-only by
  contract; this skill only dispatches and collects.
- Never write a prose findings document -- the queue, `frob.toml`, and
  `invariants/` are the only outputs.
- One `interface-auditor` mission per boundary, always -- never batched.
