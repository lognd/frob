"""Unit tests for the TypeScript-toolchain parsers (tsc, eslint)."""

from __future__ import annotations

import json

from frob.process.parsers import parse_eslint, parse_tsc


class TestParseTsc:
    def test_clean_output(self):
        # frob:tests src/frob/process/parsers/tsc.py::parse_tsc kind="unit"
        r = parse_tsc("", exit_code=0)
        assert r.tool == "tsc"
        assert r.exit_code == 0
        assert r.diagnostics == []
        assert r.summary == "no issues"

    def test_single_error(self):
        out = (
            "src/App.tsx(10,5): error TS2322: "
            "Type 'string' is not assignable to type 'number'.\n"
            "Found 1 error.\n"
        )
        r = parse_tsc(out, exit_code=2)
        assert r.exit_code == 2
        assert len(r.diagnostics) == 1
        d = r.diagnostics[0]
        assert d.file == "src/App.tsx"
        assert d.line == 10
        assert d.col == 5
        assert d.severity == "error"
        assert d.code == "TS2322"
        assert "not assignable" in d.message
        assert r.summary == "Found 1 error."

    def test_multiple_diagnostics(self):
        out = (
            "a.ts(1,1): error TS2304: Cannot find name 'foo'.\n"
            "b.ts(2,2): error TS2304: Cannot find name 'bar'.\n"
        )
        r = parse_tsc(out, exit_code=2)
        assert len(r.diagnostics) == 2
        assert r.summary == "2 errors, 0 warnings"

    def test_malformed_lines_ignored(self):
        out = "this is not a tsc diagnostic line\nneither is this\n"
        r = parse_tsc(out, exit_code=0)
        assert r.diagnostics == []
        assert r.summary == "no issues"


class TestParseEslint:
    def test_empty_output(self):
        # frob:tests src/frob/process/parsers/eslint.py::parse_eslint kind="unit"
        r = parse_eslint("", exit_code=0)
        assert r.tool == "eslint"
        assert r.summary == "no output"
        assert r.diagnostics == []

    def test_no_issues(self):
        r = parse_eslint(json.dumps([]), exit_code=0)
        assert r.diagnostics == []
        assert r.summary == "no issues"

    def test_errors_and_warnings(self):
        payload = [
            {
                "filePath": "/repo/src/App.tsx",
                "messages": [
                    {
                        "ruleId": "no-unused-vars",
                        "severity": 2,
                        "line": 3,
                        "column": 7,
                        "message": "'x' is defined but never used.",
                    },
                    {
                        "ruleId": "react-hooks/exhaustive-deps",
                        "severity": 1,
                        "line": 10,
                        "column": 1,
                        "message": "missing dependency",
                    },
                ],
            }
        ]
        r = parse_eslint(json.dumps(payload), exit_code=1)
        assert len(r.diagnostics) == 2
        errs = [d for d in r.diagnostics if d.severity == "error"]
        warns = [d for d in r.diagnostics if d.severity == "warning"]
        assert len(errs) == 1
        assert len(warns) == 1
        assert errs[0].code == "no-unused-vars"
        assert errs[0].line == 3
        assert r.summary == "1 errors, 1 warnings"

    def test_malformed_json_does_not_crash(self):
        r = parse_eslint("not json at all {{{", exit_code=1)
        assert r.tool == "eslint"
        assert "malformed JSON" in r.summary
        assert r.diagnostics == []
