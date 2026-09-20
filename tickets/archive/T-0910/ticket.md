---
id: T-0910
title: 'arch: declare exec/net/fetch_url capabilities for _logging_checks.py graphlang
  node (SELFAUDIT001)'
state: done
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_logging_checks.py
- design/frob.strata
- src/frob/vet/_capability.py
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability.py
  reason: root cause is the SYS100-family scanner's self-pattern-path exclusion missing
    this file, same class T-0729 fixed for _srp.py -- fixing scope per dispatch instruction
    rather than declaring fake capabilities
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/test_vet.py
  reason: regression tests for the is_self_pattern_path exclusion fix
  actor: logan
  at: '2026-07-26'
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_scan.py'
  actor: logan
  at: '2026-09-19'
  old_length: 575
  new_length: 3610
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_scan.py'
  actor: logan
  at: '2026-09-19'
  old_length: 3609
  new_length: 4938
evidence:
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_self_pattern_exclusion_covers_logging_checks_needle_tuples
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_line_effects_reports_no_capability_on_logging_checks_module
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
gates-security's SELFAUDIT001 stage flags src/frob/arch/_logging_checks.py:67,70,71,73 (exec/net capability markers, T-0622's own _LOG_CALLEE_MARKERS/_BOUNDARY_CALLEE_MARKERS text-matching heuristics) and a fetch_url capability as observed-but-undeclared on the graphlang design node. Discovered while verifying T-0625's gates-security stage; out of scope there (file untouched by T-0625, pre-existing since T-0622 landed on main). Declare the capabilities on the design node or waive with a reason if these are false-positive text matches, not actual exec/net/fetch_url use.

T-4718 sweep (condensed from src/frob/vet/_capability_scan.py:100-143,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

# T-0253: `_SELF_PATH`/`_REGISTRY_PATH`/`_FINGERPRINT_CATALOG_PATH` above are
# identity anchors for THIS running package's own files -- correct only when
# the scanned tree and the running package are the SAME checkout (editable
# install: `uv run frob ...`). Under a non-editable global install (`uv tool
# install frob`), the running package's files resolve to a `site-packages`
# copy, so identity comparison against a SCANNED tree that is frob's own
# repo checkout never matches and every pattern-catalog needle self-matches
# again (36 false SYS100s under `frob sys audit` vs. 0 under `uv run frob
# sys audit`).
#
# Round 1 fix (REJECTED on review): matching by bare PATH SUFFIX (the last
# three path components: package dir / subpackage / filename) with no
# further check. That closed the false-positive but opened a real hole:
# `is_self_pattern_path` is reached from `_scan_directory_capabilities`/
# `_scan_directory_fingerprints`, the SAME public entrypoints `frob vet` uses
# to scan a VENDORED/THIRD-PARTY dependency tree. A malicious dependency
# that places a file at a path ending in `frob/vet/_capability.py` (trivial:
# nest it under any vendor path, or name the package `frob` outright) would
# be silently excluded from capability scanning by suffix alone --
# `is_self_pattern_path` cannot tell "we are auditing frob's own checkout"
# from "we are vetting someone else's tree that happens to mimic frob's
# layout" using the scanned PATH alone.
#
# Round 2 fix (this one): the suffix match stays as the within-frob file
# check, but it is only REACHABLE when a separate SCAN-TARGET discriminator,
# `_is_frob_repo_root`, says the tree actually being scanned is frob's own
# repository -- not the running package's install location (round 1's
# mistake), not the scanned FILE's path alone (round 1 REJECT's mistake),
# but the scanned tree's ROOT identity: `root/pyproject.toml` declares
# `name = "frob"` AND the root also has the `frob-core`/`strata-core` Rust
# crate directories this monorepo actually ships. Requiring both the name
# and the crate directories raises the forgery bar well past "name a PyPI
# package frob" -- a typosquat sdist would also need to vendor two dummy
# top-level directories with those exact names purely to fool this check,
# and gains nothing from doing so since `frob vet`'s dependency scan target
# is the DEPENDENCY's own extracted source root, not frob's repo root,
# in every real invocation. Self-conformance (`_selfconform.py`/
# `_effects.py`) always passes frob's own repo root as `root` by
# construction (self-conformance audits ITS OWN tree), so the discriminator
# is a no-op there; `frob vet` scanning a dependency passes that
# dependency's own source root, which is never frob's repo, so the
# discriminator (correctly) refuses the exclusion and the file gets scanned
# like any other.

T-4718 sweep (condensed from src/frob/vet/_capability_scan.py:203-218,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

    # T-0910: `frob.arch._logging_checks`'s ARCH1xx logging-discipline
    # checks store the same class of I/O-classifier signal as `_srp.py`
    # above -- `_BOUNDARY_CALLEE_MARKERS` (`subprocess.`, `requests.`,
    # `httpx.`, `socket.`, ...) is a bare-text needle tuple this module's
    # `_is_boundary_call` compares a CALLEE STRING against, not code that
    # itself execs/opens a socket/fetches a URL. The scanner (by design,
    # for evasion detection) keys on string-literal CONTENT, so a
    # classifier table that merely *names* these substrings as data reads
    # as live net/exec/fetch_url capability USAGE on the `graphlang` node,
    # which is dishonest -- `_logging_checks.py` does no such I/O itself
    # (module docstring: it is written once against `NormalizedModule`,
    # a parsed-fact model, and never touches subprocess/network/sockets
    # directly). Declaring `may net`/`may exec` on `graphlang` to silence
    # this would be an equally dishonest fix in the other direction, so
    # this file is excluded from self-conformance's capability scan the
    # same way `_srp.py` is, not given a capability it does not have.