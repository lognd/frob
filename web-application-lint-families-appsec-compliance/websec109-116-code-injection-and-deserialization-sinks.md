+++
id = "01M336K75XB9MWR703KDKCPD1E"
title = "WEBSEC109-116: code-injection and deserialization sinks"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0NVJMAC21FPVPYYSEE"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5309"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_websec_deser.py", "tests/fixtures/webapp/websec1xx/deser/**", "docs/modules/webapp-websec-deser.md", "tests/unit/test_websec_deser.py"]

[[links]]
kind = "blocked-by"
target = "01M336K75VAADETHRZ71MT5J2W"
+++

SSTI (render_template_string/Template(userInput)), eval/exec/new Function, yaml.load without SafeLoader, pickle.load(s) on untrusted data, subprocess shell=True/os.system with interpolated input, LDAP filter string concatenation, NoSQL/Mongo operator-key injection (unsanitized $where/$gt/$ne from request JSON), LaTeX --shell-escape. Python AST (SEC005 substrate reuse) for most; LaTeX is a build-step regex scan of the compile invocation. Fixture per rule id.
