---
id: T-2385
title: frob --help renders grouped-subcommand section headers at the same indent as
  the commands they label
state: in-progress
kind: ux
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/__main__.py
- src/frob/_cli_parsers/_ops.py
- tests/unit/test_main_entry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ops.py
  reason: 'T-2385 acceptance[0]: narrower description column from the header-indent
    fix breaks ops help mid-word; shortening that help string is the ticket''s own
    second-order nit'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: test coverage for the header-indent fix lives here per existing frob:tests
    directives on this class
  actor: logan
  at: '2026-08-18'
designated_repro_test: null
acceptance:
- text: Given frob --help, when the grouped subcommand listing renders, then each
    section header sits at a strictly smaller indent than every command entry beneath
    it, and no help-text line breaks inside a word.
  evidence: []
- text: Given the two header-emitting branches, when the fix lands, then they are
    a single loop rather than two near-identical blocks, and the existing WIRE001/DEAD001
    waivers on both methods are preserved unchanged.
  evidence: []
threat: null
component: cli
anchor: false
anchor_reason: null
land_commit: null
---
User-reported, 2026-08-17. `frob --help`'s grouped subcommand listing
renders its two section headers at the SAME indent as the command
entries they label, so they read as if they were commands themselves:

    positional arguments:
      verb groups (each also usable standalone):
      explore               navigation: map/outline/xref/docs-search ...
      quality               correctness/hygiene gates: ...
      ...
      also available directly:
      scaffold              scaffold a new project from a template

CAUSE. `frob.__main__._GroupedHelpFormatter._format_grouped_subparsers`
(src/frob/__main__.py:306 and :309) appends each header with a
hardcoded two-space prefix, which is exactly the indent
`argparse.HelpFormatter._format_action` already renders the choice
pseudo-actions at. Nothing distinguishes header from entry.

VERIFIED FIX (prototyped against the real parser, output confirmed --
not a guess). Emit each header at the formatter's OWN current indent
rather than a hardcoded two spaces, and render that section's entries
one level deeper by bracketing them in `self._indent()` /
`self._dedent()`:

    for header, acts in (("verb groups (each also usable standalone):", group_acts),
                         ("also available directly:", rest_acts)):
        if not acts:
            continue
        parts.append("%*s%s\n" % (self._current_indent, "", header))
        self._indent()
        parts.extend(base_format_action(self, a) for a in acts)
        self._dedent()

This also collapses the two near-identical branches into one loop.
argparse recomputes the description column from the deeper indent
automatically, so help text re-wraps correctly with no manual width
arithmetic.

SECOND-ORDER NIT, in scope. The now-narrower description column makes
argparse break `ops`'s long slash-run mid-word:
"release/natives/doctor/c lean/fleet/...". Shorten that one help string
(or drop the exhaustive sub-verb enumeration from it) so no line breaks
inside a word. Check the other group help strings for the same.

Keep the existing frob:waive WIRE001/DEAD001 blocks on these two methods
intact -- they document a real callgraph gap (the formatter is reached
only through argparse's internal formatter_class chain), and T-1831 is a
deliberate never-close WIRE001 anchor.
