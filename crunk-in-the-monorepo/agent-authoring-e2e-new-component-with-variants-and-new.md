+++
id = "01M5XCWA3KQZFNDX9F46YNRVA6"
title = "Agent authoring e2e: new component with variants and new screen with states via new and edit --patch report COMP, STATE and CONTENT findings for touched nodes only"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXR6ER06SRMEJGSZ20JD5Q"
reporter = "lognd"
created = "2026-10-27T00:41:33Z"
updated = "2026-10-27T00:41:33Z"
labels = ["area:crunk"]
scope = ["crates/crunk/tests/e2e_agent_authoring.rs, crates/crunk/tests/fixtures/agent_authoring/**"]

[[acceptance]]
text = "Given an empty design dir, when crunk new component then edit --patch add variants, and crunk new screen then edit --patch add states, then each response lists COMP, STATE and CONTENT findings only for the touched nodes; given an untouched node with a known finding, then it is absent from the response; given a patch to a missing id, then exit 2 with the id named"
bound = false
+++

Epic acceptance for phase 3. Test-only over crunk new, edit, the COMP/STATE/CONTENT rules; fix any gap found by filing a bug, not by widening scope.
