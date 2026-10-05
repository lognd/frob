+++
id = "01M45AYN8TNWRM2NWXW7PER6T9"
title = "After the first real cut, REL001 does not recognise the cut's own tags and a changelog test reads a removed live fragment"
type = "bug"
category = "in-progress"
priority = "critical"
reporter = "lognd"
created = "2026-10-05T06:10:22Z"
updated = "2026-10-05T06:17:49Z"
scope = ["crates/frob-release/tests/rel001.rs", "crates/frob-release/tests/changelog.rs"]

[[acceptance]]
text = "Given this repository after frob release cut 0.532.0, when REL001 runs, then the three tags are recognised as cut and no finding is reported"
bound = true

[[acceptance]]
text = "Given the changelog tests, when they run after a cut removed every live fragment, then they pass from their own fixtures"
bound = true
+++

The first real release cut (frob release cut 0.532.0 --push, commit 8612ab142, tags frob-v0.532.0, grimble-v0.532.0 and crunk-v0.532.0, ledger events milestone-cut 66d1fe4ab and milestone-transition 49baad66c) turned CI red on experimental, reproducible locally:
(1) frob-release::rel001 this_repository_is_clean_or_not_applicable: REL001 reports each of the three tags as "has no recorded release cut; record it with frob release adopt", although the cut event was recorded by the cut itself. The fixture test tags_made_by_release_cut_itself_are_silent passes, so the real ledger differs from the fixture: find exactly why (annotated tag object oid versus peeled commit oid, tag name form, which ledger ref or milestone the rule reads, the event shape the cut wrote) and fix the root cause in REL001 or the cut, with a regression test built from this repository's actual event and tag shapes. Do not run frob release adopt to paper over it.
(2) frob-release::changelog the_v2_notice_fragment_is_a_lead_notice reads a fragment from the live changelog.d directory, which the cut correctly compiled and removed; the test must use its own fixture.
