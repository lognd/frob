---
id: T-4306
title: Hook-script design node observes none of its four declared capabilities
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE DESIGN NODE COVERING THE HOOK SCRIPTS DECLARES FOUR CAPABILITIES AND THE
SELF-CONFORMANCE SCANNER NOW OBSERVES NONE OF THEM, TAKING SIX TESTS AND THE
INTEGRATION RUN DOWN WITH IT.

WHAT IS MEASURED. The integration run reports the same four findings from several
independent angles: for the hooks node, each of its four declared capabilities is
"declared but never observed". The mutation audit agrees from the other
direction -- it reports the same four as not load-bearing, and its baseline count
of unobserved declarations is four rather than zero. Six failing tests, one cause.

THE DECLARATIONS ARE NOT OBVIOUSLY WRONG, WHICH IS THE POINT. The node's code
glob covers the hook script directory, those scripts are tracked in version
control and present in the tree, and each capability carries a written reason that
plainly describes what those scripts do -- running commands, reading tree state,
writing lock and log files, reading environment. A hook whose entire job is
running other tools genuinely does execute things. So the likely defect is that
the scanner stopped REACHING those files, not that the declarations became false.

ESTABLISH WHICH IT IS BEFORE CHANGING ANYTHING. Two candidate shapes, and they
have opposite fixes: either the observation walk no longer visits that directory
(an exclusion, an ignore-file glob, or a dot-directory being skipped -- note that
exclusion handling was changed more than once in recent days), or the capability
detection itself no longer recognises the constructs those scripts use. Tell these
apart directly: point the observer at one hook script you have confirmed contains
an obvious command execution, and see whether the file is visited at all versus
visited and found empty. An absent measurement and a zero measurement look
identical in the output, so distinguish them explicitly rather than inferring from
a count.

IF IT IS A REACH REGRESSION, FIX THE REACH, and treat the fact that a whole
declared directory could silently drop out of the scan as the more serious half of
the finding -- a scanner that returns nothing for a directory it is configured to
cover should be able to say so. If instead the declarations are genuinely stale
because the scripts changed, correct the declarations to match what the scripts
now do, and say which script stopped doing what.

DO NOT CLEAR THIS BY DELETING THE DECLARATIONS. Removing a `may` to silence an
unobserved-capability finding would assert these scripts cannot execute commands
or write files, which is false and would disarm the threat obligation that
depends on it.

VERIFY by running the self-conformance and mutation-audit tests named above and
quoting their results. Other failures in the same suite are not yours.
