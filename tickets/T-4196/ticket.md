---
id: T-4196
title: 'allow several ticket ids in one frob:ticket directive: 217 stacks of three
  or more exist, two of them fourteen lines deep'
state: queued
kind: feature
origin: human
created: '2026-09-07'
priority: medium
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
  reason: 'answers the owner''s question with a measurement across every directive
    kind: frob:tests is the largest win (2143 lines, 45 deep), frob:enforces has the
    worst concentration (73 deep), doc and waive are not worth it, and four never
    stack. Records the hard constraint that changes the design -- 8913 of 13689 test
    bindings contain a space, so a space separator is unambiguous for ticket ids and
    genuinely ambiguous for test bindings'
  actor: logan
  at: '2026-09-07'
  old_length: 3721
  new_length: 7266
- mode: set
  reason: 'corrects my own measurement, which scanned only python files: the owner
    was right that describes stacks, and it is the third largest win at 1121 lines
    and 60 deep, with 1591 of its 1673 occurrences in markdown. Reframes the ticket
    as a blanket directive-family capability per the owner''s ask, while keeping the
    separator question per-directive because most test bindings contain spaces'
  actor: logan
  at: '2026-09-07'
  old_length: 7266
  new_length: 10790
designated_repro_test: null
acceptance:
- text: given a directive naming several ticket ids, when it is parsed, then the symbol
    binds to all of them and each resolves as it would alone
  evidence: []
- text: given an existing single-id directive, when it is parsed, then behaviour is
    identical to today
  evidence: []
- text: given a renumber of one ticket, when it rewrites a multi-id directive, then
    the other ids on that line are undisturbed
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
ALLOW SEVERAL TICKET IDS IN ONE `frob:ticket` DIRECTIVE, so a symbol touched by
many tickets does not accumulate a stack of near-identical comment lines above it.
Owner request.

MEASURED ACROSS EVERY TRACKED PYTHON FILE, counting runs of consecutive
`frob:ticket` comment lines:

    run length   occurrences
        1            7979
        2             760
        3             143
        4              48
        5              19
        6               2
        7               2
        9               1
       14               2

    stacks of three or more: 217
    worst offenders: 14 consecutive lines in the waiver gate module and 14 in
                     the application config module, 9 in the sys runner,
                     7 in the land module and 7 in the CLI entry point

Collapsing every multi-id stack to one line removes roughly 1,300 lines of pure
bookkeeping from the source. That is the quality-of-life case, and it is real: a
reader scrolling past fourteen consecutive directive lines to reach a function is
being taxed for the tool's convenience.

WHAT TO BUILD
  1. Accept several ids after the verb, space separated. Decide explicitly
     whether commas are also accepted and say so -- this repo already has a
     defect where one separator was defended and another silently was not, and
     the inconsistency produced a scope entry that matched nothing.
  2. Keep the single-id form working unchanged. Nearly eight thousand existing
     directives use it and none should need touching.
  3. MAKE THE MARKDOWN FORM AGREE. The markdown variant is parsed by its own
     pattern that captures exactly one id. If the comment form learns multiple
     ids and the markdown form does not, the two spellings of the same directive
     diverge -- which is the desync this project exists to prevent.

THE PART MOST LIKELY TO BE MISSED, AND IT IS THE DANGEROUS ONE: the renumber path
rewrites ticket ids inside directives, matching on the directive keyword. If it
is not taught about multiple ids on one line, renumbering will either miss the
trailing ids or corrupt the line. This repo has a recorded incident where a bare
renumber invocation rewrote every ticket id in the queue, so this path deserves
its own fixture rather than an assumption. Check every consumer that parses or
rewrites these directives, not only the reader.

DO NOT SHIP AN AUTO-COLLAPSE OF EXISTING STACKS IN THIS TICKET. A separate open
ticket records that the land's auto-fix currently rewraps directive comments and
SPLIT A NODE ID ACROSS A LINE BREAK, silently breaking the binding while the
comment still reads correctly. Until that is fixed, a bulk rewrite of directive
comments is the last thing this repository should run. Land the parser support
first; collapse the stacks later, deliberately, once the wrapper is safe.

MUST-FIRE FIXTURE:   a directive naming several ids binds the symbol to all of
                     them, and each id resolves exactly as it would alone.
MUST-STAY-QUIET:     every existing single-id directive behaves identically, and
                     a stack of single-id directives still works -- this is
                     additive, not a migration.
THIRD FIXTURE:       renumbering a ticket rewrites its id inside a multi-id
                     directive without disturbing the other ids on that line.

ACCEPTANCE
- Several ids accepted in one directive, with the separator question decided
  explicitly.
- The markdown form accepts the same shape as the comment form.
- Every parser and rewriter of this directive enumerated and updated, renumber
  included, each with a fixture.
- No bulk auto-collapse of existing stacks in this ticket.
- All three fixtures committed.

WHICH OTHER DIRECTIVES DESERVE THE SAME TREATMENT -- MEASURED, NOT GUESSED. Owner
asked. Counting consecutive runs of each directive across every tracked python
file:

    directive          total   stacked   lines saved   worst stack
    frob:tests         13689      1026          2143       45 deep
    frob:ticket        10278       977          1322       14 deep
    frob:enforces        604        70           290       73 deep
    frob:doc            3007        51            67        5 deep
    frob:waive          1546        14            14        2 deep
    frob:invariant       153         0             0        1
    frob:todo              4         0             0        1
    frob:describes        46         0             0        1
    frob:used-by           1         0             0        1

SO THE ANSWER IS THREE DIRECTIVES, NOT ONE, and this ticket was filed on the
second-biggest of them:

  frob:tests IS THE LARGEST WIN -- 2143 lines, and a worst case of 45 consecutive
  directive lines above a single symbol. It is also the most natural fit: one
  symbol legitimately has many tests, so stacking is the EXPECTED shape rather
  than an accident of history.

  frob:enforces HAS THE WORST CONCENTRATION -- 73 consecutive lines in the
  evasion-coverage module, the deepest stack of any directive in the repository,
  though a smaller total.

  frob:doc and frob:waive ARE NOT WORTH IT. Fifty-one and fourteen stacked
  occurrences, saving 67 and 14 lines. Adding multi-value parsing to them buys
  almost nothing and widens the surface that every parser and rewriter must
  handle. Leave them single-valued and say so, so the next reader does not
  re-litigate it.

  THE REMAINING FOUR NEVER STACK AT ALL. Their worst run is one. They are
  single-valued by nature and should stay that way.

A HARD CONSTRAINT THAT CHANGES THE DESIGN, AND THE REASON THIS MEASUREMENT
MATTERED: THE SEPARATOR CANNOT BE A SPACE FOR EVERY DIRECTIVE.

    of 13689 frob:tests values, 8913 CONTAIN A SPACE

They are not bare tokens. A test binding carries trailing attributes and
suppression comments after the node id, so the value is an id followed by more
text. Space-separating several ids on one line would be genuinely ambiguous --
a parser could not tell where one binding's attributes end and the next id
begins. And test node ids in some ecosystems legitimately contain spaces inside
the id itself, which this repository has already seen from a consumer whose
node ids embed a describe-block name with spaces around a separator.

By contrast a ticket id is a short fixed shape with no attributes and no spaces,
so space separation is unambiguous there. Twelve enforces values contain a
space, so it sits with tests rather than with ticket.

THEREFORE: do not design one separator for all three. Either use a separator that
cannot occur inside a value (a comma is the obvious candidate, but CONFIRM against
real values before committing to it), or keep per-directive rules and document
them. What must not happen is a space-separated implementation for ticket being
extended to tests by analogy -- that would silently mis-split most of the bindings
in the repository.

SEQUENCING
  1. This ticket, for frob:ticket, with space separation.
  2. A separate ticket for frob:tests and frob:enforces, whose separator question
     is genuinely different and must be settled against real values first.
Do not fold them together: the id shapes differ, the ambiguity differs, and the
renumber and rewrite paths differ per directive.

CORRECTION -- MY MEASUREMENT ABOVE SCANNED ONLY PYTHON FILES AND IS WRONG FOR AT
LEAST ONE DIRECTIVE. The owner said they had seen the describes directive
stacked; my table reported it as never stacking. They were right and I was
measuring a subset. Re-measured across EVERY tracked file, and counting the
markdown comment form as well as the python comment form:

    directive               total   stacked   saved   worst
    frob:tests              13822      1030    2155    45 deep
    frob:ticket             10466       992    1339    14 deep
    frob:describes           1673       212    1121    60 deep
    frob:enforces             616        70     290    73 deep
    frob:doc                 3197        52      68     5 deep
    frob:waive               2083        40      56    11 deep
    frob:used-by               78        10      15     7 deep
    frob:invariant            232         1       1     2 deep
    frob:todo / enumerates     37         2       2     2 deep
    frob:external-reader       13         0       0     1
    frob:no-behavior-change    13         0       0     1

frob:describes is the THIRD LARGEST WIN, not a non-participant: 1121 lines and a
sixty-deep worst case. The reason my first pass missed it entirely is that 1591
of its 1673 occurrences live in markdown files and only 73 in python -- I scanned
python and reported a conclusion about the directive. Same error I have made
repeatedly today in a different costume: a true measurement of a subset promoted
to a claim about the whole. The lesson for anyone working this ticket is to
enumerate the directive's real file types before drawing any conclusion about it.

THE OWNER'S ASK IS THEREFORE THE RIGHT ONE: treat this as a BLANKET capability
rather than a per-directive feature. Four directives clear a thousand lines each
or better -- tests, ticket, describes, enforces -- and the remainder cost nothing
extra once the parser is generic. Roughly 4900 lines of pure directive stacking
disappear.

BUT THE SEPARATOR QUESTION IS STILL PER-DIRECTIVE, and it is the whole
engineering problem. Values differ in shape:

  UNAMBIGUOUS WITH A SPACE: ticket ids are a short fixed shape with no attributes
  and no internal spaces.

  AMBIGUOUS WITH A SPACE: 8913 of 13822 test bindings contain a space, because
  the value is a node id followed by attributes and suppression comments. Test
  node ids in some ecosystems also contain spaces INSIDE the id. Enforces and
  waive values carry attributes too.

  NEEDS CHECKING: describes and used-by target paths and anchors. Measure whether
  any real value contains a space before choosing, rather than assuming.

So a blanket capability does NOT mean a blanket separator. Either pick one
delimiter that cannot occur inside any value -- measure it against every real
value first, do not reason about it -- or define it per directive and document
each. The failure to avoid is implementing space separation because it works for
ticket ids and extending it by analogy, which would silently mis-split the
majority of the test bindings in this repository.

REVISED SCOPE FOR THIS TICKET: it now covers the directive family, not just the
ticket verb. Keep the sequencing though -- land the parser and the separator
decision first, and do NOT bulk-collapse existing stacks here, because a sibling
ticket records that the land's auto-fix currently rewraps directive comments and
splits a node id across the break, silently breaking the binding while the
comment still reads correctly.
