---
name: document
description: Driven by drift -- frob check reports DRIFT001 (stale acked docs) and COV001 (missing doc edges); fix exactly those, then frob ack each re-verified ref. Use when frob check flags doc drift or missing documentation coverage, not as a free-standing "write some docs" pass.
---

# document

Docs work is driven by the drift report, not by browsing for things that
look undocumented. If `frob check` doesn't flag it, this skill doesn't
touch it.

## Step 1: Get the drift report

```bash
frob check --only drift               # DRIFT001: acked digest moved without re-ack
                                       # DRIFT002: edge endpoint no longer resolves
frob check --only coverage            # COV001: public symbol has no doc edge
```

Read every violation. Each one embeds its remedy command (`frob ack <ref>`
or a pointer to the missing edge) -- do not guess at what changed.

## Step 2: Fix exactly the flagged items

**DRIFT001** (acked digest moved): the code or doc changed since the last
ack. Read both sides:

```bash
frob graph why <ref>                  # what changed, sig vs body vs doc facet
```

- If the doc still accurately describes the current signature/behavior,
  the ack was just never re-run after a body-only change that doesn't
  affect the facet being tracked -- verify, then re-ack.
- If the doc is now wrong, fix the prose to match the current code before
  re-acking. Never `frob ack` a doc you haven't actually verified against
  the current symbol -- that's a rubber stamp, not documentation.

**DRIFT002** (dangling edge): the symbol was renamed or deleted. Check the
gate's rename candidates (body-digest match) before editing the doc:

```bash
frob graph why <ref>                  # lists candidate replacements
```

Update the doc anchor to the new symref, or remove the anchor if the
symbol was legitimately deleted (state that in the doc, don't just delete
the mention silently if other prose still refers to it).

**COV001** (missing doc edge): a public symbol has no `frob:doc` edge at
all. Write the doc section it's missing, then add the directive:

```markdown
<!-- frob:describes src/frob/pkg/module.py::function_name -->
### function_name

One sentence: what it does and why. Include failure semantics: "Returns
Ok(X) on success, Err(E.Y) if Z."
```

## Step 3: Docstring rules (same discipline as before)

- One line for simple functions. Multi-line only for non-obvious behavior.
- Describe behavior from the CALLER's perspective, including error
  semantics for fallible functions.
- Do NOT describe self-documenting parameters. No ASCII art.
- Do NOT reference the current ticket id or why it was added -- that's the
  ticket's job, not the doc's.

## Step 4: Re-ack

```bash
frob ack <ref> [--facet sig|body|doc]     # one ref at a time; verify first
```

Only ack refs you actually re-verified in Step 2. Never batch-ack a whole
file's worth of DRIFT001 hits without reading each one -- the ack is a
claim that a human or agent looked at it.

## Step 5: Verify clean

```bash
frob check --only drift
frob check --only coverage
```

Both must be clean (or carry a reasoned `frob:waive`) before this skill is
done.

## Hard rules

- Never write or update docs that `frob check` did not flag as drifted or
  missing -- that's scope creep on a documentation pass with no ticket.
- Never `frob ack` a ref you have not personally re-verified this pass.
- If this doc work is bound to a ticket, bind the diff with
  `frob:ticket T-00xx` the same as any other change.
