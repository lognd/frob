+++
id = "01M44YR15KP4G6VYJ0QZ9D8SR7"
title = "Guides: C#/.NET and Unity setup"
type = "story"
category = "todo"
priority = "low"
points = 2
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:37:05Z"
updated = "2026-10-05T02:37:05Z"
idempotency_key = "d94-guide"
scope = ["docs/guides/dotnet.md", "docs/guides/unity.md", "docs/design/dotnet-unity.md", "docs/design/README.md", "docs/reference/fidelity.md"]

[[links]]
kind = "blocked-by"
target = "01M44YQXBGJW1VKDF64YJ5RTJ6"

[[links]]
kind = "blocked-by"
target = "01M44YQZ1A507E2J3JETAWMMAV"

[[links]]
kind = "blocked-by"
target = "01M44YQZF413Z6EMF7GYTBSVVT"

[[links]]
kind = "blocked-by"
target = "01M44YR0AAJ0X0BGXX7F17DMKH"

[[acceptance]]
text = "Given docs/guides/unity.md, when a new Unity repository owner follows it, then every config key and command shown exists and is accurate"
bound = false

[[acceptance]]
text = "Given docs/design/dotnet-unity.md, when read, then its status states what landed and lists any deviation"
bound = false
+++

Write docs/guides/dotnet.md (enable C#, project model, dotnet provider, test selection, fidelity limits) and docs/guides/unity.md (unity pack opt-in, UNITY rules, asmdef model, unity provider config and refusals, goway note), and update docs/design/dotnet-unity.md status from accepted direction to as-built with deviations listed. Links from docs/reference/fidelity.md and the README tables.
