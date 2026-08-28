---
id: T-3069
title: 'Hook: nudge hand-performed renames toward frob refactor, without misfiring
  on ordinary import edits'
state: done
kind: feature
origin: human
created: '2026-08-26'
priority: high
blocked_by:
- T-3066
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/frob-suggest.py
- tests/test_hook_frob_suggest.py
- .claude/settings.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/frob-suggest.py
  reason: extend the existing frob-suggest nudge hook with a rename-detection rule,
    per T-3069 brief
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_hook_frob_suggest.py
  reason: must-fire/must-stay-quiet fixtures for the new rename-detection rule
  actor: logan
  at: '2026-08-27'
- op: add
  glob: .claude/settings.json
  reason: register frob-suggest for the Edit tool matcher, needed to detect the multi-file
    same-module rename signal the brief specifies
  actor: logan
  at: '2026-08-27'
evidence:
- tests/test_hook_frob_suggest.py::test_hand_rename_sed_fires_on_scripted_import_rewrite
- tests/test_hook_frob_suggest.py::test_hand_rename_perl_fires_on_scripted_import_rewrite
- tests/test_hook_frob_suggest.py::test_hand_rename_sed_stays_quiet_without_import_mention
- tests/test_hook_frob_suggest.py::test_hand_rename_sed_stays_quiet_inside_frob_refactor_invocation
- tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_second_file_rewriting_same_module_import_fires
- tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_brand_new_import_never_fires
- tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_single_file_repeated_edits_never_fire
- tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_refactor_residue_prose_fix_never_fires
- tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_frob_suggest_ack_env_var_bypasses_it
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 57d0e601d1d128c6c396e368fa7d4d7216a26240
---
WHY: `frob refactor` exists precisely so that renames/moves rewrite references
symbolically rather than by hand, and the owner has directed that refactors go
through it. But nothing stops an agent from hand-editing imports across files,
and a hand-rename silently misses the non-Python reference surface the verb
handles: `.strata` `code=` globs, ticket `scope` globs, `frob:doc`/`frob:tests`
path citations, and `frob.toml` dotted `module:symbol` config values. T-2989's
real rename touched 60 operations across 20 files including a `design/frob.strata`
binding and 8 archived tickets -- a hand pass would have missed most of it.

WHAT TO BUILD: a PreToolUse nudge that fires when a call looks like a
hand-performed rename/move and points at the right `frob refactor` verb
(`move`, `rename`, `split`, `move-module`).

INFRASTRUCTURE ALREADY PRESENT -- reuse it, do not invent a parallel hook:
  - `.claude/hooks/root-write-guard.py` already intercepts
    `Write|Edit|NotebookEdit|Bash` (`_GUARDED_TOOLS`, `_target_path()`), so an
    Edit-surface hook is an established shape here.
  - `.claude/hooks/frob-suggest.py` is the existing NUDGE hook: a `_RULES` list
    of (id, positive pattern, message, NEGATIVE pattern) tuples, with
    repeat-tracking state and a `FROB_SUGGEST_ACK=1` escape. Its 4th tuple
    element -- the negative pattern that keeps the nudge quiet when the caller
    already did the right thing -- is the design to follow.

PRECISION IS THE WHOLE PROBLEM. Three of `frob-suggest`'s 14 rules were found
MISFIRING today (T-2908) and had to be narrowed; a noisy new rule would be worse
than no rule, and would itself get acked away -- the same way `frob:waive`
reached 2117 uses against `frob:debt`'s 85. Design conservatively.

HIGH-PRECISION SIGNALS (start here):
  - A Bash in-place regex rewrite (`sed -i`, `perl -pi`, similar) whose pattern
    mentions `import` or a dotted module path. A scripted rewrite of import
    lines is unambiguously a hand-rename. Stateless and near-zero
    false-positive.
  - The SECOND-and-later Edit in a session that rewrites the same
    `from <module> import` / `import <module>` prefix in a DIFFERENT file. One
    file is ordinary work; the same module path being rewritten across several
    files is a rename. `frob-suggest` already carries cross-call state for its
    repeat counter, so this is feasible.

MUST STAY QUIET (each needs a fixture -- a guard with no must-stay-quiet case is
how the three misfiring rules shipped):
  - Adding a BRAND-NEW import for newly written code. This is the common case
    and must never nudge.
  - Editing imports in a SINGLE file.
  - Fixing residue the refactor verb deliberately does not rewrite. This is
    real: T-2989 hand-fixed 6 docstring/anchor citations because
    `move-module` intentionally never rewrites `.py` docstring prose -- that is
    the verb's own must-not-fire guard, and the follow-up hand pass is correct
    behaviour, not a violation.
  - Any call already running `frob refactor`.

IT MUST BE A NUDGE, NOT A HARD BLOCK, and must honour the existing
`FROB_SUGGEST_ACK=1` escape. Hand-editing is sometimes right (see the T-2989
residue case above), and a hard block would have prevented completing that
ticket. Blocked-once-then-allow-on-repeat, matching the existing hook's
behaviour, is the correct strength.

MESSAGE QUALITY: name the specific verb for the shape detected, and say WHAT a
hand-rename misses (the non-Python reference surface listed above) rather than
just asserting the tool is preferred. `raw-worktree`'s message was wrong for
months because it recommended a tool that refuses from a subagent -- so verify
the verb you recommend actually works for the caller before recommending it.

NOTE A CURRENT BUG: `frob refactor split`/`move-module` are presently
UNUSABLE for some real cases -- `_shares_line_with_sibling_statement()`
(`src/frob/refactor/_scan.py:57`) uses `ast.walk`, which yields ancestor
compound statements whose line span overlaps their own body, so any
function-local or block-nested import false-refuses as "semicolon-joined"
(T-3066, blocking T-3064). Do NOT ship a hook that pushes agents toward a verb
that will refuse them. Either land after T-3066, or have the message
acknowledge the limitation. State which you chose.

ACCEPTANCE
- The nudge fires on a scripted in-place import rewrite and on a multi-file
  same-module Edit sequence. Must-fire fixture each.
- It stays quiet on: a new import, a single-file import edit, refactor-residue
  prose fixes, and any `frob refactor` invocation. Must-stay-quiet fixture each.
- `FROB_SUGGEST_ACK=1` bypasses it, consistent with the existing hook.
- The recommended verb is verified to actually work for a subagent caller.
- Hooks are MATERIALIZED from `.claude/hooks/` into `~/.claude/` -- edit the
  source and run the sync, then confirm `frob claude sync --check` reports no
  drift.