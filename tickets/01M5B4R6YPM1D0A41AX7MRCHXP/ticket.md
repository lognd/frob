+++
id = "01M5B4R6YPM1D0A41AX7MRCHXP"
title = "evidence/test runners: declare a per-runner report field in frob.toml; runners without one are UNMEASURED for granular evidence; extend executed-and-passed to the command provider and land re-verification"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-19T22:33:10Z"
updated = "2026-10-19T22:33:10Z"
+++

Follow-up of ~46VKHER (deliver items 2 and the command-provider/land-verify part of 1): the structured providers now refuse green runs that executed nothing (E-EVIDENCE-NOT-EXECUTED), but the generic command provider and land-time evidence re-verification remain exit-code-only.
