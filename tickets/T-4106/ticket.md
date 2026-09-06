---
id: T-4106
title: frob ticket accept gives a bare argparse error when an agent reaches for an
  evidence flag on it; three consumer agents in a row guessed the wrong verb
state: queued
kind: ux
origin: agent
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ticket/*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given frob ticket accept invoked with an evidence-shaped unrecognized flag,
    when argparse rejects it, then the output names frob ticket evidence and its acceptance-index
    flag
  evidence: []
- text: given an unrecognized flag unrelated to evidence, when frob ticket accept
    rejects it, then the message is the ordinary argparse error unchanged
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE VERB THAT MANAGES ACCEPTANCE CRITERIA AND THE VERB THAT BINDS EVIDENCE TO
THEM HAVE CONFUSABLE NAMES, AND AGENTS GUESS WRONG. Reported as logand.app-v2
F-305: across T-0257, T-0270 and T-0271, three agents in a row reached for an
evidence-command flag on the acceptance verb. Two of them tried it first, before
anything else.

MEASURED HERE, so the fix targets the right surface:

  `frob ticket accept` takes only criterion-text management flags -- add, amend
  by index, remove by index, with a reason. It has no evidence flag of any kind.
  `frob ticket evidence` is where both halves actually live: the flag that runs
  a command as evidence, and the 1-based acceptance-index flag that binds that
  evidence to a specific criterion.

So the mental model the agents had -- "acceptance and evidence are bound
together, and the binding is done where acceptance is" -- is HALF RIGHT, which
is why the guess is so attractive. The binding IS by acceptance index; it just
happens on the other verb. What they get instead is argparse's generic
unrecognized-argument error, which names the bad flag and nothing else, so the
recovery is a round trip through help output.

THREE AGENTS IN A ROW IS A DESIGN SIGNAL, NOT THREE MISTAKES. This is a
discoverability defect in frob, measured in a consumer repo, and the standing
directive on repeated friction applies: fix it in the tool rather than in each
prompt. Note the consumer's playbook and ticket prompts mention the two together,
so improving the prose alone would not have prevented it -- the prose is what
created the correct-but-misplaced expectation.

THE FIX IS A TARGETED ERROR HINT, not a new alias. Do NOT add the flag to the
acceptance verb: two verbs accepting the same flag with different meanings is
the duplication this repo exists to prevent, and an alias would make the wrong
model permanently correct-looking. Instead, when the acceptance verb is invoked
with an unrecognized argument that names evidence, emit one line naming the verb
and flags that actually do the job, with the acceptance-index flag shown, before
exiting.

CHECK FOR THE MIRROR CASE while implementing: an agent that has learned the
correct verb may then guess criterion-management flags on the evidence verb. If
that direction is equally cheap to hint, hint it too; if not, say so rather than
leaving it undiscussed.

MUST-FIRE FIXTURE:   invoking the acceptance verb with an evidence-shaped
                     unrecognized flag produces a message naming the evidence
                     verb and its acceptance-index flag.
MUST-STAY-QUIET:     an unrecognized flag unrelated to evidence produces the
                     ordinary argparse error, unchanged.
THIRD FIXTURE:       a correct invocation of either verb is byte-for-byte
                     unaffected.

ACCEPTANCE
- The hint fires only for evidence-shaped unrecognized arguments on that verb.
- No flag is aliased across the two verbs.
- The mirror direction is either handled or explicitly ruled out with a reason.
- All three fixtures committed.
