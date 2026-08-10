---
id: T-1990
title: make frob PATH-vs-repo version skew self-announcing at the repo level, not
  one machine's hook config
state: dropped
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Filed while working T-1980 (frob global-install version policy). This
repo already detects and reports the exact condition -- a bare `frob`
on PATH being older than the repo's own build -- via a local Claude
Code project hook (`.claude/settings.json`'s frob-suggest family), which
fired correctly and named both versions during T-1980's own session.

That detection is machine-local Claude tooling config, not portable: a
human running the bare `frob` binary directly, a CI job, or an agent on
a different machine gets no warning at all. T-1980's FIX DIRECTION (c)
asks for this to become a real frob-level check instead (e.g. a startup
warning frob's own CLI entrypoint prints when it detects `sys.version`/
`__version__` skew against a repo's `pyproject.toml`-declared frob
dependency, mirroring the exact warning line already observed from the
GLOBAL 0.184.0 build when run inside this checkout: "running installed
frob 0.184.0 ... inside a checkout whose pyproject.toml declares frob
0.438.0" -- that message already exists in the 0.184.0 codebase for the
bare-binary-in-a-dev-checkout case; the missing piece is the reverse
direction (an agent/human on a SIBLING repo with no local editable
build at all, where there is no "declares" pyproject.toml frob pin to
compare against) and making it fire for every one of the 8 sibling
repos' invocations, not just this repo's own.

ACCEPTANCE: first test must FAIL before the fix -- assert that a
frob-wired repo running a PATH build older than the repo's own build is
reported, with both versions named, from frob's own code (not a Claude
Code hook). Out of scope for T-1980 itself (docs-only ticket, policy +
measurement deliverable); this is the code follow-up.

## Drop reason
- 2026-08-10: Duplicate of already-shipped T-1218 (stale_binary_warning, src/frob/app/_config_meta.py:261, wired at src/frob/__main__.py:470 and src/frob/doctor.py:1215). T-1218 is exactly this: a repo declares frob.toml min_frob_version, and ANY invoked frob binary below that floor gets a loud warning naming both versions, from frob own code, not a Claude Code hook -- confirmed live via tests/unit/test_config.py::test_stale_binary_warning_flags_version_below_floor (0.9.0 vs 0.277.0 incident, passing today, 3/3 stale_binary_warning tests green). It explicitly targets "any repo, no dependency on [project] name = frob" (its own docstring), i.e. exactly the sibling-repo case T-1990 describes as missing. The REAL remaining gap is not code: none of the 9 repos (this one plus 8 siblings, checked directly) have ever populated min_frob_version in their own frob.toml, so the mechanism is live but dormant everywhere. That is a per-repo config/rollout task, not a src/frob/app/** code change -- out of this ticket declared scope and shape, worth a narrow follow-up (adding min_frob_version to each frob.toml) rather than reimplementing an existing, tested, wired mechanism under this id.
