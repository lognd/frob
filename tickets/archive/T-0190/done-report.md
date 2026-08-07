## Done report

Made the current tree structurally un-flaggable by GitHub push protection
and drift-locked it:
- Every real-shaped fixture token in tests/test_secrets_gate.py (and the
  three doc-example tokens in src/frob/gates/_secrets.py comments) is now
  runtime-constructed by concatenating string pieces (e.g. `"sk_live_" +
  "abcdef...")` so no contiguous GitHub-flaggable literal exists in the
  source bytes, while the token still evaluates to a gate-firing value at
  runtime -- frob's own detection is NOT weakened (full secrets-gate suite,
  60 tests, still passes).
- Meta-test class TestGitHubPushProtectionUnflaggable: coarse re-encodings
  of GitHub's published Stripe/AWS/GitHub-token/Slack patterns, checked
  against this test file's AND _secrets.py's on-disk source text, so a
  future fixture that reintroduces a contiguous flaggable literal fails
  locally before it can ever re-trip GH013.

Evidence (2 ids, pass): test_this_file_contains_no_github_flaggable_literal,
test_pattern_source_module_contains_no_github_flaggable_literal. Reviewed
by coordinator (implementer stalled on a block-and-stall background test
wait, the T-0322 antipattern -- work was complete; coordinator verified
detection intact and finalized).

IMPORTANT remaining coordinator step (out of this ticket's scope, per the
ticket body): the already-committed flagged Stripe literal still lives in
git history at 48aeed1 (T-0157). Push protection scans the whole push
range, so `git push` of main will STILL be blocked by that historical
commit until the unpushed range is rewritten to scrub it, OR the user
clears it via GitHub's push-protection unblock URL. This ticket does not
claim main is immediately pushable -- only that the current tree is safe
and a regression is now statically prevented. A repo-wide scan found the
only other literal-shaped matches are AWS's canonical allowlisted example
("AKIA" + "IOSFODNN7EXAMPLE", split here per T-0968 so this note no longer
trips that ticket's own tightened SEC001 gate) and dictionary-word
placeholders in tickets-archive.md (not entropy-bearing credentials).
