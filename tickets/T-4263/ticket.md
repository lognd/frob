---
id: T-4263
title: split the release upload job per distribution so each new pypi project can
  register its own pending trusted publisher
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/release.yml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given three distributions that do not yet exist on the index, when their pending
    trusted publishers are registered, then each claims a distinct configuration and
    none is refused as a duplicate
  evidence: []
- text: given the split upload jobs, when either kernel distribution fails to publish,
    then the application distribution does not publish at all
  evidence: []
- text: given the approval gates, when the split lands, then the decision about which
    distributions require a reviewer is recorded in the workflow itself
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE RELEASE WORKFLOW CANNOT BOOTSTRAP THREE NEW PYPI PROJECTS FROM A SINGLE
UPLOAD JOB, BECAUSE PYPI REFUSES A SECOND PENDING TRUSTED PUBLISHER WITH THE
SAME CONFIGURATION. Owner-reported, with the exact refusal text:

  A pending trusted publisher matching this configuration has already been
  registered for a different project name.

WHY IT HAPPENS HERE. The upload job publishes all three distributions from one
job, under one GitHub Environment. A pending publisher is identified by the
repository owner, the repository, the workflow filename, and the environment
name, so all three projects would claim an identical tuple. The first
registration succeeded; the second was refused as a duplicate. This is not a
naming problem and would have happened with any second package name.

THIS IS RELEASE-BLOCKING AND ITS FAILURE MODE IS LATE. Nothing detects it until
the publish step of a real release, after the build matrix, the green-CI check,
the artifact smoke test, and a human approval have all passed. The first attempt
at the first release is exactly when it fires.

THE FIX. Give each distribution its own GitHub Environment so each pending
publisher claims a distinct configuration. Because an environment is declared
per job, that means splitting the single upload job into one job per
distribution.

PRESERVE THE ORDERING CONTRACT WHILE SPLITTING IT. The current job publishes the
two kernel crates before the application, and the manifest's comments record why:
the application pins both kernels by exact version, so an application published
without them is uninstallable for everyone. After the split, that ordering must
be expressed as an explicit dependency between the new jobs rather than as step
order inside one job. Confirm that a failure to publish either kernel still
prevents the application from publishing at all.

CHECK WHAT THE SPLIT COSTS IN APPROVALS. Each environment can carry its own
required reviewer, so three environments can mean three separate approval
prompts for one release. Decide deliberately whether every distribution needs a
gate or only the application does, and write the decision down where the next
person reads it.

VERIFY WITHOUT PUBLISHING. Do not test this by publishing to the real index. The
workflow can be exercised far enough to prove the OIDC claim is accepted without
uploading, and the ordering can be proven by forcing a kernel job to fail and
observing that the application job does not run.
