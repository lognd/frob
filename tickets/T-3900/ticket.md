---
id: T-3900
title: DOC006 reads markdown link syntax as a TOML config pointer, so ordinary reference
  links are hard errors in any consumer repo
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'describe the bracketed link labels in words: the ticket documenting the
    bracket false positive was itself tripping it and blocking T-3857s land'
  actor: logan
  at: '2026-09-05'
  old_length: 3573
  new_length: 3659
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported as typani FROBLEMS T-025. DOC006 reads MARKDOWN LINK SYNTAX as a TOML
config-section pointer.

    site:     CODE_OF_CONDUCT.md:124 and :134
    content:  the Contributor Covenant's own attribution links -- the labels
              v2.1 and homepage, each written in square brackets
    observed: a config-reference-pointer finding saying the bracketed v2.1
              label is not a real frob.toml/pyproject.toml/Cargo.toml
              section or key

`[text]` followed by `(url)`, or defined elsewhere as `[text]: url`, is markdown
reference-link syntax. It is not a TOML table header. The two share a bracket
and nothing else.

THIS IS NOW URGENT RATHER THAN COSMETIC, and the reason is a change that landed
today. T-3844 ratcheted gate severity: 307 rules are now hard errors. DOC006 was
ALREADY an error before that -- it was the single error in this repo's floor
measurement. So any consumer repo containing ordinary markdown reference links
gets DOC006 ERRORS, and markdown reference links are a completely standard
idiom. This is a build-breaker for adopters, and it is exactly the shape that
makes a tool feel hostile on first contact.

IT IS ALSO EFFECTIVELY UNFIXABLE AT THE SITE. The reporter's file is
CODE_OF_CONDUCT.md -- a VERBATIM third-party document. You cannot restructure
the Contributor Covenant's attribution links to satisfy a linter, so the only
available action is a waiver inside someone else's text. That is the same
no-correct-disposition shape as T-3843 (frontmatter), T-3852 (container close)
and T-3855 (Protocol members): the rule demands something the subject cannot
provide.

THE FIX: exclude markdown link syntax from config-pointer resolution. A
bracketed token is a link reference when it is followed by `(` (inline link) or
when a matching `[token]:` definition exists in the document (reference link).
Both are decidable from the document itself. Do this as a PARSE-LEVEL
distinction, not a denylist of common words -- the v2.1 and homepage labels are
just two instances and a denylist would leave the next one.

WIDEN BEFORE FIXING: what else does the config-pointer rule match that is not a
config pointer? Markdown has several bracketed constructs -- footnotes
(`[^1]`), task list markers (`- [ ]`, `- [x]`), and citation-style references.
Enumerate what the rule currently accepts as a candidate and report which are
genuine config pointers. That enumeration is the durable output; fixing only
link syntax leaves footnotes to be discovered by the next consumer.

CHECK THE SIBLING RULE while you are here: DOC006 also resolves file/path
pointers and cli-invocation pointers. Does either have an analogous
false-positive against ordinary markdown? A path pointer rule that matches
inside a fenced code block, for instance, would have the same character.

DO NOT fix this by exempting whole files by name (CODE_OF_CONDUCT.md,
LICENSE.md). That is a denylist wearing different clothes, and a verbatim
third-party document can be called anything.

MUST-FIRE FIXTURE:   a genuine non-resolving `[tool.foo]` config reference in
                     prose is still flagged
MUST-STAY-QUIET FIXTURES:
  - an inline markdown link `[text](url)` is not flagged
  - a reference-style link `[text]` with a matching `[text]: url` definition is
    not flagged
  - whichever other bracketed markdown constructs the enumeration turns up

ACCEPTANCE
- Markdown link syntax excluded at parse level, not by denylist.
- The enumeration of bracketed-construct candidates reported.
- The sibling pointer kinds (file/path, cli-invocation) checked for the
  analogous defect and reported either way.
- All fixtures committed.
