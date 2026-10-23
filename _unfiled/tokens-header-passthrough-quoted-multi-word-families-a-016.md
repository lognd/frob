+++
id = "01M1QDTV1NG0HWSF3WFG89K2JT"
title = "tokens header passthrough + quoted multi-word families (A-016)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0053"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/spec/models.py", "src/crunk/spec/load.py", "src/crunk/tokens/render.py", "tests/unit/test_spec.py", "tests/unit/test_tokens.py", "tests/system/test_e2e_23_header.py"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV1K47NCWQG23QET33X2"

[[acceptance]]
text = "given [tokens] header set to a CSS comment block and a family 'JetBrains Mono', when tokens renders, then the header is the file's first bytes verbatim, repeated renders are byte-identical, and the family value is double-quoted (E2E-23)"
bound = false
+++

Per r5 spec.md/tokens.md: TokensConfig gains header: str = '' validated as a complete CSS comment block (starts /*, ends */, no interior */) when non-empty; [tokens] section accepts prefixes and header. render_css/render_json emit the header first (json: skip -- json has no comments; header applies to the css render only, token values unchanged -- state that in tokens.md if the doc is ambiguous). Family VALUES quote any name containing whitespace in both renderers' value strings. Goldens updated; INV-006 anchors untouched.
