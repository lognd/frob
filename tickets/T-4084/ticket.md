---
id: T-4084
title: 'Lab1-Reference (tenth consumer): scaffold-to-first-check friction, plus docs
  absent from the wheel and a graph cache that goes stale mid-check'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'tier=epic: collects a tenth consumer''s ten findings; most
  are corroboration routed to existing tickets, and the two genuinely new items (docs
  absent from the wheel, graph cache stale mid-check) need their own scoped children'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A TENTH DOWNSTREAM CONSUMER (Lab1-Reference, frob 0.530.0, 2026-09-06) filed ten
findings from a FRESH `frob scaffold new python-tool`. Their most severe item is
being fixed separately (ticket-new resolving a non-repo directory as the root and
writing sixty tickets into it). This ticket collects the REST, several of which
corroborate existing tickets from a third or fourth independent repo.

ALREADY-FILED, NOW CORROBORATED FROM A NEW REPO -- record the arrival, do not
refile:
  item 2   REF001 reports every tickets/T-####/ticket.md frob ITSELF WRITES as an
           orphan (70 findings on a fresh repo). Third arrival: kicad-libsync
           reported it (T-3931) and logand.app-v2 hit it too. Their proposed fix
           is the same: put the ledger on the REF allowlist by default, as
           docs/tickets/design already are for ROOT001.
  item 3   A fresh scaffold ships with no [tickets].default_milestone (so every
           new ticket fails MILE003) and no [[docblocks.commands]] (so FLAGCOV001
           is "unmeasured" from the first check). Both are T-3931's
           scaffold-noise finding, now confirmed on a different scaffold run.
  item 10  FLAGCOV001 cannot be measured for a uv-managed project: the parser
           import runs INSIDE FROB'S OWN TOOL VENV, where the project package is
           not installed ("No module named 'lab1clean'"). THIS IS T-3887's
           environment-isolation class from a THIRD repository, and it is the
           same shape kicad-libsync reported. Their proposed remedy matches the
           one already on that ticket: import through the project's interpreter
           (uv run), or report unmeasured rather than erroring.
  item 7   The frob-suggest hook blocks `sed -i` edits in tests as
           "hand-rename-sed" and blocks direct `ruff check`; both need
           FROB_SUGGEST_ACK=1 every time. The lexical-hook class again -- see
           T-4082 (the secrets hook blocking `import.meta.env` in a ticket) and
           T-4083 (re-indentation read as a directive addition).

GENUINELY NEW, AND THE TWO WORTH ACTING ON:

  item 4 -- THE DOCS THE ERROR MESSAGES CITE ARE NOT IN THE WHEEL.
      "The strata `node` grammar and the vmodel vocabulary are NOT DOCUMENTED IN
       THE INSTALLED PACKAGE; docs/strata/*.md are REFERENCED BY MESSAGES BUT NOT
       SHIPPED IN THE WHEEL, so the syntax had to be RECOVERED BY PROBING
       strata_core."
      A user was reduced to reverse-engineering a grammar from the binary because
      our own diagnostics point at documentation the install does not contain.
      This is T-4020's dead-doc-anchor defect at package scale: there, a runtime
      message cited an anchor that did not resolve; here, messages cite whole
      FILES that are not shipped. DETERMINE FIRST whether docs/ is meant to ship
      in the wheel -- if it is deliberately excluded, then every message citing a
      docs/ path is wrong for installed users and the fix is the messages, not the
      packaging. Answer that before changing either.
      They also report a concrete grammar papercut worth fixing regardless:
      `#` IS NOT A COMMENT CHARACTER in .strata files (`//` is), and the error is
      merely "unexpected character '#'" -- a message that names the construct and
      the real comment syntax would have saved the guesswork.

  item 6 -- `frob check` READS A GRAPH CACHE THAT GOES STALE DURING ITS OWN RUN.
      "edits made to test files DURING a 3-minute check produced findings
       (TEST001, LANDPARITY001) against the PRE-EDIT graph WITH NO STALENESS
       WARNING in the summary."
      Findings reported against a tree that no longer exists, presented as
      current. On a multi-minute check this is not an edge case -- it is what
      happens whenever anyone works while a check runs, which is the normal
      state of an agent fleet. This is the silent-zero family inverted: not a
      measurement that found nothing, but a measurement of something that is gone.
      At minimum the summary must say the graph was built at time T and the tree
      changed since; ideally the affected findings are marked stale rather than
      reported flatly.

  item 5 -- SELFAUDIT/SYS103 fires on every capability-bearing file when the
      design directory contains ONLY vmodel_node declarations, i.e. a repo with a
      V-model but no system model yet. Their proposal: a model with zero `code=`
      globs is "no system model declared" and should be skipped with a note.
      NOTE THIS IS A SUBJECT-COUNT INSTANCE -- a gate whose comparison set is
      empty firing on everything, rather than reporting that it had nothing to
      compare against. Cross-reference T-3985.

  item 8 -- `frob ticket scope --remove` ERRORS on a glob that is not in the
      declared scope; a no-op with a note would be friendlier when repairing a
      scope guessed by a batch script. Small, and a judgement call: an error on a
      no-op removal is defensible, so decide deliberately rather than changing it
      reflexively.

  item 9 -- LANDPARITY001 requires a frob:doc or frob:tests directive directly
      above every new public symbol INCLUDING MODULE CONSTANTS (KIND,
      DESCRIPTION); they added 88 frob:doc lines for constants already documented
      by their module docstring. THIS IS THE WRONG-INCENTIVE CLASS (T-4069): the
      cheapest way to satisfy the rule is 88 lines of boilerplate that make the
      files worse. Add it to that ticket's audit set -- it is a fifth instance.

ACCEPTANCE
- Items 4 and 6 filed as their own children with the questions above answered
  first (does docs/ ship? is the cache staleness knowable at summary time?).
- Items 2, 3, 7, 10 recorded as corroboration on T-3931, T-3887 and the
  lexical-hook tickets rather than refiled.
- Items 5 and 9 cross-referenced to T-3985 and T-4069 respectively.
- Item 8 decided deliberately, either way.