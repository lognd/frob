---
id: T-0208
title: vet obfuscation scan pathologically slow -- high_entropy_strings dominates,
  no progress/timeout
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/**
- tests/**
- docs/modules/vet.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _obfuscation.py'
  actor: logan
  at: '2026-09-19'
  old_length: 662
  new_length: 3016
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _obfuscation.py'
  actor: logan
  at: '2026-09-19'
  old_length: 3015
  new_length: 4823
evidence:
- tests/vet_suite/test_fingerprint.py::TestObfuscationEnsemble::test_high_entropy_string_flagged
- tests/vet_suite/test_fingerprint.py::TestObfuscationEnsemble::test_plain_string_not_flagged
- tests/vet_suite/test_fingerprint.py::TestObfuscationEnsemble::test_bidi_override_is_fatal
- tests/vet_suite/test_fingerprint.py::TestObfuscationEnsemble::test_clean_text_no_bidi
- tests/vet_suite/test_fingerprint.py::TestObfuscationEnsemble::test_hex_identifier_ratio_flagged
- tests/vet_suite/test_fingerprint.py::TestObfuscationEnsemble::test_normal_identifiers_not_flagged
- tests/vet_suite/test_fingerprint.py::TestObfuscationEnsemble::test_high_entropy_strings_returns_the_literal
- tests/vet_suite/test_fingerprint.py::TestObfuscationEnsemble::test_high_entropy_strings_empty_for_plain_text
- tests/vet_suite/test_fingerprint.py::TestObfuscationEnsemble::test_scan_directory_obfuscation_finds_signal_in_one_file
- tests/vet_suite/test_scan_tree.py::TestScanTreeTimeout::test_slow_package_returns_within_timeout_not_task_duration
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (all 3 repos): frob vet unusable -- lograder killed at 11m47s with 15/30 packages (101MB venv); aprog-public stuck on numpy at 120s. cProfile+SIGALRM around scan_tree(fetch=False): _obfuscation.py:70 high_entropy_strings consumed 82 of 120 profiled seconds (785 calls); tree-sitter/capability scans fine. Fix: cap candidate string count/length per file, skip literal-table files over a size threshold, optimize the entropy loop, add per-package progress lines and --timeout/--jobs. Acceptance: frob vet completes on lograder's venv under 2 minutes with progress output.

T-4718 sweep (condensed from src/frob/vet/_obfuscation.py:36-67, trimmed
for DOCARCH002's 12-line cap): the trimmed block's full original text,
kept verbatim below.

# T-0208: `_high_entropy_strings` used to scan with a regex whose alternation
# `(?:\\.|(?!\1).)*` catastrophically backtracks on real files -- a 9.6KB
# fixture (blib2to3/pgen2/conv.py, stdlib-adjacent, nothing adversarial in
# it) profiled at ~90ms in the regex alone vs ~0.3ms for the entropy math
# over the same matches, and the pilot-repo profile that filed this ticket
# showed 82 of 120 profiled seconds inside this function across 785 calls.
# `_iter_string_literals` below replaces it with a single left-to-right scan
# (no backtracking, no lookahead) that is O(len(text)) by construction.
#
# T-0208 review round 2: a 4096-char truncation of the CONTENT fed to the
# entropy check (rather than just the returned/logged snippet) is WRONG,
# not just a perf tradeoff -- Shannon entropy is a property of the whole
# sample, and truncating a real hit can pull its score back under
# threshold. Measured on a real file (cryptography's pkcs7.py, a
# mismatched-quote span, not even a real payload): entropy(full 7575-char
# span) = 4.602 (fires, matches the old regex), entropy(same span
# truncated to 4096) = 4.472 (silent -- a genuine detection loss, not the
# disclosed "truncating a base64 blob still trips on its opening bytes"
# case that reasoning assumed). `_iter_string_literals` therefore no
# longer truncates content: the O(n) argument for the underlying scan
# does not depend on a length cap -- every successful (closing) literal's
# scan consumes its own span once and the outer loop never revisits those
# characters, so total scan work across ALL successful literals in a file
# is bounded by `len(text)` regardless of how any single literal's length
# is distributed; only a FAILED open needs to be O(1) (the
# `last_single`/`last_double` reject below already guarantees that). What
# remains is a pure memory/DoS safety ceiling, `_MAX_CANDIDATE_LEN`,
# raised to 1MB so it is never reached by a real source string and only
# guards against a single-file OOM from an adversarial multi-hundred-MB
# "string". The candidate-COUNT cap remains a distinct, still-needed
# safety valve against files with huge numbers of small quoted tokens
# (generated data tables).

T-4718 sweep (condensed from src/frob/vet/_obfuscation.py:78-103,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

# Escapes (`\\x`) are skipped as a pair. Entropy is computed over the FULL
# literal, never truncated (review round 2 -- see the T-0208 note above:
# truncating changes the entropy score and can hide a real hit).
# `_MAX_CANDIDATE_LEN` is a 1MB memory-safety ceiling, not a normal-path
# cap; the file is capped at `_MAX_CANDIDATES_PER_FILE` literals.
#
# UNTERMINATED CANDIDATES (review round 1 caught this): a quote char with
# no matching close anywhere later in the file is NOT a literal -- it
# matches the OLD regex's actual behavior (a failed match attempt at that
# start position, retried one char later), not "run to end of text".
# Treating it as a literal was an undisclosed behavior change: after a
# mismatched-quote region consumes the file's last `'`, the old regex
# gives up on that open quote and correctly re-syncs on the next
# docstring's triple-quote; the old (buggy) version of this function
# instead swallowed that docstring into one giant unterminated "literal",
# silently DROPPING it from the entropy check -- a detection gap, not a
# disclosed false-positive tradeoff.
#
# Detecting "no closing quote anywhere later" naively (scan-to-EOF, then
# discard and retry one char over) reintroduces the exact quadratic
# blowup T-0208 fixed, for a file with many trailing unmatched quote
# chars. Fixed with an O(1) reject: `last_single`/`last_double` are each
# quote type's LAST raw occurrence in the text, computed once; if a
# candidate opens at or after that position, it can never close and is
# rejected without scanning -- one linear pre-pass plus O(1) per
# rejection keeps the whole function O(len(text)).