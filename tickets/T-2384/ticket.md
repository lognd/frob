---
id: T-2384
title: frob's enforcement surface is hardcoded to this repo's layout and sync-skills
  is not multi-repo safe
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Given a src-layout project whose package is NOT named frob, when every gate
    that currently hardcodes the "src/frob/" prefix is run against it, then each gate
    scans that project's declared source roots and reports the violations present,
    where previously it reported zero; proven per gate by a must-now-fire fixture,
    with the frob repo's own pre-change finding count unchanged as the must-still-pass
    control.
  evidence: []
- text: Given two different frob-enabled repos that both sync agents/ and skills/
    into the same ~/.claude, when each runs frob sync-skills in turn, then neither
    run removes or overwrites an entry installed by the other, and running either
    repo's sync twice in a row produces no further change on the second run.
  evidence: []
- text: Given a ~/.claude containing hand-maintained agents and skills that no frob
    repo installed, when frob sync-skills runs against it for the first time, then
    nothing is deleted and nothing pre-existing is overwritten.
  evidence: []
- text: Given the source-root resolution logic, when the retarget is complete, then
    exactly one public resolver exists (promoted from frob.lang._nodes._declared_python_source_roots,
    T-2195) and no second implementation of source-root discovery has been added,
    verified by a frob-dup / grep check for surviving "src/frob/" literals outside
    frob's own self-referential gates.
  evidence: []
threat: null
component: portability
labels:
- cross-project
- idempotence
anchor: false
anchor_reason: null
land_commit: null
---
frob is deployed to sibling repos (lograder, feldspar, and others), but a
large part of its enforcement surface is hardcoded to THIS repo's own
layout and naming. Off-repo those checks do not error -- they silently
match nothing, which is the [[catalogued-is-not-enforced]] failure mode:
the gate is present, listed, and documented, while enforcing nothing.

MEASURED SURFACE (git grep, code-only, 2026-08-17):

  22 files contain a literal "src/frob/" path prefix; 14 of them are in
  src/frob/gates/.

Two distinct failure directions, both wrong:

  1. SILENT PASS. `_env_var_docs.py:72` skips every tracked path that
     does not start with "src/frob/". In a repo whose package is
     `src/lograder/`, the candidate set is empty and ENVDOC reports a
     clean zero. Same shape at `_root_asset_dirs.py:112` and in
     `tickets/_models.py:474`'s OVER_BROAD_LITERAL_GLOBS, where the
     over-broad-scope nudge cannot fire for any non-frob package.

  2. FALSE POSITIVE. `_root_asset_dirs.py::_referenced_in_src` answers
     "is this asset dir referenced in source?" by scanning only
     src/frob/**. Off-repo it always answers False, so legitimately
     referenced directories get reported as unreferenced.

`_env_var_docs.py` additionally hardcodes the `FROB_` env-var prefix,
which is the same class of assumption one level up: the project's own
name.

THE FIX ALREADY EXISTS FOR ONE CONSUMER. T-2195 solved exactly this for
the `frob.lang` package: `frob.lang._nodes._declared_python_source_roots(root)` reads
the project's OWN declared packaging config (setuptools
packages.find.where, package-dir, hatch wheel packages) to discover
source roots, explicitly rejecting "hardcoding the `src/` convention as a
lexical special case". It is private and has one caller.

The work is to promote that resolver to a single public home, give it a
repo-relative-prefix form suitable for the `startswith` sites, retarget
the hardcoded literals to it, and derive the env-var prefix from the
project name rather than the `FROB_` literal. One home, per NO
DUPLICATION -- do not add a second resolver.

VERIFICATION REQUIREMENT (non-negotiable, see
[[positive-control-or-it-proves-nothing]]): a portability fix whose only
evidence is "the frob repo still passes" proves nothing, because the
frob repo passes under the hardcoded literal too. Every retargeted gate
needs BOTH:
  - a must-now-fire fixture: a src-layout project whose package is NOT
    named frob, containing a real violation, where the gate previously
    reported zero and must now report it;
  - a must-still-pass control: the same gate on this repo, with the same
    finding count as before the change.

COOPERATION AND IDEMPOTENCE (user directive, 2026-08-17): every one of
these commands must be safe to run repeatedly and safe to run from
SEVERAL repos against the same shared target. Re-running must not
duplicate, and must not clobber what another project put there. This
promotes `frob sync-skills` from "already fine" to a DEFECT, which is
how it was found:

  `scaffold/_skills_sync.py::_sync_one_kind` removes every entry under
  `~/.claude/<kind>/` with no counterpart in the CURRENT repo
  (`shutil.rmtree`). That is correct for a single-repo mirror and
  actively destructive the moment a second frob-enabled repo syncs into
  the same `~/.claude`: each run deletes the other project's agents and
  skills, and alternating runs flap them in and out. It is idempotent
  standalone and mutually destructive cooperatively -- exactly the case
  this epic exists to fix.

  FROB ALREADY HAS TWO COOPERATIVE CONVENTIONS AND THIS COMMAND USES
  NEITHER (verified by reading both, not assumed):
    - refuse-without-force: `scaffold/project.py` guards BOTH its
      manifest writer (line 374) and `install_worktree_lease_hook`
      (line 659) with an `exists()` check returning
      `ScaffoldError.OutputExists`, with a regression test
      (`test_refuses_existing_hook_without_force`).
    - managed-block markers: `scaffold/_managed.py` (T-0736) inserts
      between `# frob:managed-block BEGIN/END <id>` pairs -- matching is
      left alone, differing is replaced in place, absent is appended,
      and "a repo's own content outside the markers is never touched".
  Reuse one of these; do not invent a third mechanism.

  The sync must become provenance-aware: it may only remove an entry it
  can attribute to the syncing repo (a recorded manifest of what this
  repo installed), and must leave unattributed or other-repo entries
  untouched. A first run against a hand-maintained `~/.claude` must
  delete nothing. Copy-in must also stop being a blind
  `copytree(dirs_exist_ok=True)` over a destination another project may
  own -- detect the collision and refuse or report it rather than
  silently winning.

Deliberately NOT in scope: `strata/_compliance.py`'s owner="logan" is frob's own
registry DATA, not a mechanism. `src/frob/repo_meta.py`'s
`project.get("name") != "frob"` is a deliberate self-identification
check for the version floor. Neither of these two is a defect.
