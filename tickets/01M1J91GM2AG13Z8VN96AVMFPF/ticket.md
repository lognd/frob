+++
id = "01M1J91GM2AG13Z8VN96AVMFPF"
title = "vet --hook vets whole resolution instead of delta"
type = "bug"
category = "triage"
priority = "low"
reporter = "human"
created = "2026-09-03T00:00:00Z"
updated = "2026-10-04T21:08:12Z"
aliases = ["T-3714"]
labels = ["v1-cluster:E1", "triage:accepted"]
scope = ["src/frob/vet/_hook.py", "src/frob/vet/_scan.py"]
+++

apollo FROBLEMS.md 2026-09-03: frob vet --hook 'uv add tinycss2' blocked on uv@0.12.9 and build@1.6.0, neither in tinycss2's dependency closure (tinycss2 -> webencodings only). The hook appears to vet the whole prospective resolution / tool universe rather than the delta the command introduces, so any fresh release of unrelated tooling blocks every install command.
