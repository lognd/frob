## Done report

Changed:
- src/frob/arch/_python.py::_body_fingerprint (new)
- src/frob/arch/_python.py::_extract_signatures (now returns a 5-tuple including a normalized body fingerprint)
- src/frob/arch/_python.py::_type_is_generic (new)
- src/frob/arch/_python.py::_signature_is_specific (new, SIGNATURE-SPECIFICITY discriminator)
- src/frob/arch/_python.py::_near_duplicate_cluster (new, BODY-SIMILARITY discriminator; reuses frob.dup._legacy_py._collect_locals_py/_serialize_py_body)
- src/frob/arch/_python.py::_abstraction_group_evidence (new, per-group evidence selector)
- src/frob/arch/_python.py::_emit_abstraction_suggestion (new, extracted to keep _check_abstraction_opportunities under the long-function threshold)
- src/frob/arch/_python.py::_check_abstraction_opportunities (now requires signature-specificity OR body-similarity, not a bare shared signature)
- src/frob/arch/__init__.py (all_py_sigs type threaded through as a 5-tuple)
- docs/modules/arch.md (new subsection: "abstraction-opportunity requires signature-specificity or body-similarity, not a bare shared signature (T-0370)")
- tests/unit/test_arch.py: new TestAbstractionOpportunityDiscriminators class (4 new tests); TestDispatchFamilySuppression's 3 existing generic-`(str)->str` fixtures updated with near-duplicate-shaped bodies so they still exercise dispatch-family suppression, not signature-specificity (their prior bodies were 5-6 normalized tokens -- one-line `text.strip()`/`.lower()`/`.title()` calls -- correctly no longer flagged as "an extractable abstraction" under the new discriminators; the dispatch-family behavior they test needed a body shape that passes body-similarity to stay a valid fixture for that specific concern)

Discriminators implemented: BOTH.
1. Signature-specificity (`_signature_is_specific`): a shared signature with at least one type outside `_GENERIC_TYPE_NAMES` (ubiquitous primitives, containers, `Optional`/`Union`/`Callable`, and `AppConfig` -- the App/AppConfig pattern's by-design uniform CLI-dispatch contract) is specific enough on its own; the whole group is reported.
2. Body-similarity (`_near_duplicate_cluster`): reuses `frob.dup._legacy_py._collect_locals_py`/`_serialize_py_body` (locals alpha-renamed, literals collapsed) to normalize each function body, then `difflib.SequenceMatcher.ratio() >= 0.9` pairwise, with bodies under 8 normalized tokens excluded (too short for similarity to mean anything -- prevents one-line-predicate false positives). Only the near-duplicate SUBSET of a generic-signature group is reported, not the whole group.

Before/after: `uv run frob check --only arch 2>&1 | grep -c abstraction-opportunity` dropped from 67 to 37. The two residue groups explicitly named in the ticket are gone entirely: the 39-member `(AppConfig) -> None` run-entrypoint group and the 31-member `(str) -> str` group both vanish (no near-duplicate bodies among their members, and the shared type is generic). The 8-member `(Path) -> str | None` group in src/frob/gates/_coverage.py shrank from 8 to 3 (`_sha_of` x2 + `_content_hash`, a genuine near-duplicate cluster found via body-similarity -- `_sha_of` is a literal name collision with an identical body defined twice, a real finding the old detector buried in 5 unrelated neighbors).

Examples now suppressed: 39-fn `(AppConfig) -> None` (gitlog_runner.py/vet_runner.py/perf_runner.py/dup_runner.py/deploy_runner.py per-command `run` entrypoints -- App/AppConfig pattern, by-design uniform contract, unrelated bodies); 31-fn `(str) -> str` (name-munging helpers across excludes.py/gates/__init__.py -- generic signature, unrelated bodies); most of the former `(Path) -> str | None` group (5 of 8 members had unrelated bodies).

Examples still flagged: `(Path) -> tuple[Violation, ...]` in gates/_pii_structural.py (specific `Violation` return type); `(Path) -> Result[tuple[Dependency, ...], VetError]` in vet/_lockfile.py (specific domain types); `(str) -> bool` in gates/__init__.py reduced to the 4-member cluster containing the literal-duplicate `_has_done_report` (defined identically twice) found via body-similarity, versus the old detector's 33-member undifferentiated list.

Filed: none (all work fit inside the extended ticket scope).

Gates: `uv run frob check --ticket T-0370` clean (0 errors, 0 SCOPE001/PRE001/ARCH001 against this ticket's files; remaining warnings are pre-existing repo-wide noise unrelated to this change -- TEST006 no-coverage-stamp is the coordinator's `make coverage` step per the playbook, not this ticket's). Ticket scope extended to include `tests/unit/test_arch.py` and `docs/modules/arch.md` (the ticket's own instructions required test and doc changes) and the pre-work sweep re-run (`frob ticket sweep T-0370`) after the scope extension.

### Round 2: reviewer-caught vacuous test fix

The reviewer rejected round 1 for one issue: `TestDispatchFamilySuppression::test_dispatch_family_no_abstraction_opportunity` had `pass`-only handler bodies, so its generic `(Path, dict) -> None` signature never cleared `_BODY_MIN_TOKENS` (8 tokens) either way -- the group was suppressed by the body-similarity gate regardless of `_is_dispatch_family`'s answer, making its `frob:tests ..._is_dispatch_family` directive false. Confirmed independently: giving the handlers merely-long-but-mutually-DISSIMILAR bodies (>=8 tokens, ratio well under 0.9) still left the test vacuous, because a generic-signature group with no near-duplicate subset is never flagged by EITHER discriminator regardless of dispatch-family -- the fixture had to make the group flaggable on `_signature_is_specific` alone so `_is_dispatch_family` becomes the sole remaining suppressor.

Fix: changed the fixture's second parameter from `cfg: dict` to `cfg: RunnerConfig` (a domain type defined in the same fixture file, not one of `_GENERIC_TYPE_NAMES`), so the group is specific-signature-flaggable independent of body content, and gave the three handlers substantial (>=8-token), mutually dissimilar bodies (distinct per-handler logic: scan/iterdir, stamp/write_text, sweep/glob+unlink) so no body-similarity confounder exists either. Verified live: temporarily forced `_is_dispatch_family` to `return False` (one-line edit to `src/frob/arch/_python.py`, reverted immediately after, `git diff src/frob/arch/_python.py` confirmed clean) and re-ran the single test -- it FAILED (`assert 'abstraction-opportunity' not in {'abstraction-opportunity'}`), proving the test now genuinely depends on `_is_dispatch_family`. Reverted the break, re-ran with the real implementation -- passes again.

Production code (`src/frob/arch/_python.py`, `src/frob/arch/__init__.py`) is unchanged from round 1 -- this fix is test-only, confined to `tests/unit/test_arch.py`.

Verification: `uv run pytest tests/unit/test_arch.py -q -p no:cacheprovider -o addopts=""` -- 35 passed. `uv run frob check --only arch 2>&1 | grep -c abstraction-opportunity` -- still 37. `uv run frob check --ticket T-0370` -- 0 errors (re-swept prework after the edit). No evidence-id changes: the fixed test's node id (`tests/unit/test_arch.py::TestDispatchFamilySuppression::test_dispatch_family_no_abstraction_opportunity`) was not among T-0370's previously recorded evidence ids (it is bound via its own `frob:tests` directive, already recorded as evidence under sibling ticket T-0371), so no re-recording was needed.
