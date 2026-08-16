---
id: T-2208
title: The rapid sweep files a regression ticket for a quarantine finding and never
  disposes it, so a coordinator must hand-restate the same fact -- 8 manual disposals
  this session, each one blocking the fleet until done
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
evidence_scope:
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_disposes_findings_the_ticket_covers
- tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_leaves_quarantine_raised_when_other_findings_remain_undisposed
- tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_no_quarantine_raised_is_a_silent_no_op
- tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_clear_failure_is_logged_not_raised
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_raises_with_attributed_and_unattributed_findings
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_keeps_finding_when_native_still_broken
designated_repro_test: tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_disposes_findings_the_ticket_covers
acceptance:
- text: 'Measured: _file_regression_ticket (src/frob/app/ticket_runner/_rapid_sweep.py:1259)
    files a regression ticket for a quarantine finding, and clear_quarantine is called
    ONLY from src/frob/app/verify_runner.py and src/frob/app/ticket_runner/_land_cmd.py
    -- never from the sweep. So the system files T-XXXX for finding F and then requires
    a human to run ''frob verify dispose --file-ticket F=T-XXXX'', restating a fact
    it already established. I did that 8 times this session; each time deferred landing
    was OFF fleet-wide until I did, forcing every land onto ~208s synchronous verification.
    This test MUST fail against current main.'
  evidence:
  - tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_disposes_findings_the_ticket_covers
  - tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_leaves_quarantine_raised_when_other_findings_remain_undisposed
  - tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_no_quarantine_raised_is_a_silent_no_op
  - tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_clear_failure_is_logged_not_raised
  - tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_raises_with_attributed_and_unattributed_findings
  - tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_keeps_finding_when_native_still_broken
- text: When the sweep files a regression ticket for a finding, dispose that finding
    with --file-ticket semantics in the same operation, and log it the way a manual
    disposal is logged so the audit trail is identical. Do NOT auto-dispose findings
    the sweep did NOT file a ticket for -- an undisposed finding with no tracking
    ticket is exactly what quarantine exists to surface, and blanket auto-clearing
    reopens the hole T-1693 closed.
  evidence:
  - tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_disposes_findings_the_ticket_covers
  - tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_leaves_quarantine_raised_when_other_findings_remain_undisposed
  - tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_no_quarantine_raised_is_a_silent_no_op
  - tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_clear_failure_is_logged_not_raised
  - tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_raises_with_attributed_and_unattributed_findings
  - tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_keeps_finding_when_native_still_broken
- text: 'SCOPE-PLAUSIBILITY FALSE POSITIVE, recorded deliberately. Filing this ticket
    tripped T-2177''s own warning (''none of the declared scope files contain any
    identifier or string-literal token matching this title/body''). I verified the
    scope IS correct: _file_regression_ticket lives in _rapid_sweep.py at line 1259
    and that file mentions quarantine 33 times. The warning fired because my title
    is entirely prose with ZERO identifier-shaped tokens -- precisely the T-2189-shaped
    limitation T-2192''s author measured and disclosed as not closable by token matching.
    Useful corroboration from a real filing, not a new defect.'
  evidence:
  - tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_disposes_findings_the_ticket_covers
threat: null
component: null
anchor: false
anchor_reason: null
---
