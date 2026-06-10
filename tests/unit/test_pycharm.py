"""
Tests for the PyCharm inspection output parser.

Covers:
  - parse_pycharm_xml: unit tests with sample XML strings
  - parse_pycharm_dir: temp directory with multiple XML files
  - File path normalization (Windows paths, relative paths)
  - Severity mapping
  - Malformed XML handling
  - frob parse pycharm <dir> via subprocess
"""

from __future__ import annotations

import json
import subprocess
import sys

from frob.process.parsers import parse_pycharm_dir, parse_pycharm_xml
from frob.process.parsers.common import Diagnostic

FROB = [sys.executable, "-m", "frob"]

# ---------------------------------------------------------------------------
# Sample XML fixtures
# ---------------------------------------------------------------------------

UNRESOLVED_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<problems version="1.0">
  <problem>
    <file>file:///C:/Users/user/project/src/module.py</file>
    <line>42</line>
    <offset>12</offset>
    <highlighted_element>some_identifier</highlighted_element>
    <description><![CDATA[Unresolved reference 'some_var']]></description>
    <problem_class id="PyUnresolvedReferences" severity="WARNING" attribute_key="WARNING_ATTRIBUTES">
      Unresolved references
    </problem_class>
    <hints>
      <hint value="Create function 'some_var'"/>
    </hints>
  </problem>
</problems>
"""

UNUSED_IMPORT_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<problems version="1.0">
  <problem>
    <file>file:///C:/Users/user/project/src/other.py</file>
    <line>10</line>
    <description><![CDATA[Unused import 'os']]></description>
    <problem_class id="PyUnusedImport" severity="WARNING" attribute_key="WARNING_ATTRIBUTES">
      Unused imports
    </problem_class>
  </problem>
</problems>
"""

ERROR_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<problems version="1.0">
  <problem>
    <file>file:///C:/Users/user/project/src/bad.py</file>
    <line>5</line>
    <description><![CDATA[Type error]]></description>
    <problem_class id="PyTypeChecker" severity="ERROR">Type checker</problem_class>
  </problem>
</problems>
"""

WEAK_WARNING_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<problems version="1.0">
  <problem>
    <file>file:///C:/Users/user/project/src/foo.py</file>
    <line>1</line>
    <description><![CDATA[Weak warning here]]></description>
    <problem_class id="SomeCheck" severity="WEAK WARNING">Weak</problem_class>
  </problem>
</problems>
"""

INFORMATION_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<problems version="1.0">
  <problem>
    <file>file:///C:/project/src/info.py</file>
    <line>3</line>
    <description><![CDATA[Info message]]></description>
    <problem_class id="InfoCheck" severity="INFORMATION">Info</problem_class>
  </problem>
</problems>
"""

SERVER_PROBLEM_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<problems version="1.0">
  <problem>
    <file>file:///C:/project/src/srv.py</file>
    <line>7</line>
    <description><![CDATA[Server issue]]></description>
    <problem_class id="ServerCheck" severity="SERVER PROBLEM">Server</problem_class>
  </problem>
</problems>
"""

EMPTY_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<problems version="1.0">
</problems>
"""

MALFORMED_XML = "not xml at all <<<"

NO_PROBLEMS_ELEMENT = """\
<?xml version="1.0"?>
<root><something/></root>
"""

# ---------------------------------------------------------------------------
# parse_pycharm_xml unit tests
# ---------------------------------------------------------------------------


class TestParsePycharmXml:
    def test_returns_list(self):
        diags = parse_pycharm_xml(UNRESOLVED_XML)
        assert isinstance(diags, list)

    def test_single_problem_parsed(self):
        diags = parse_pycharm_xml(UNRESOLVED_XML)
        assert len(diags) == 1

    def test_code_extracted(self):
        diags = parse_pycharm_xml(UNRESOLVED_XML)
        assert diags[0].code == "PyUnresolvedReferences"

    def test_message_extracted(self):
        diags = parse_pycharm_xml(UNRESOLVED_XML)
        assert "some_var" in diags[0].message

    def test_line_number(self):
        diags = parse_pycharm_xml(UNRESOLVED_XML)
        assert diags[0].line == 42

    def test_file_element_present(self):
        diags = parse_pycharm_xml(UNRESOLVED_XML)
        assert diags[0].file is not None
        assert "module.py" in diags[0].file

    def test_severity_warning(self):
        diags = parse_pycharm_xml(UNRESOLVED_XML)
        assert diags[0].severity == "warning"

    def test_severity_error(self):
        diags = parse_pycharm_xml(ERROR_XML)
        assert diags[0].severity == "error"

    def test_severity_weak_warning(self):
        diags = parse_pycharm_xml(WEAK_WARNING_XML)
        assert diags[0].severity == "warning"

    def test_severity_information(self):
        diags = parse_pycharm_xml(INFORMATION_XML)
        assert diags[0].severity == "info"

    def test_severity_server_problem(self):
        diags = parse_pycharm_xml(SERVER_PROBLEM_XML)
        assert diags[0].severity == "warning"

    def test_empty_problems(self):
        diags = parse_pycharm_xml(EMPTY_XML)
        assert diags == []

    def test_malformed_xml_no_raise(self):
        diags = parse_pycharm_xml(MALFORMED_XML)
        assert isinstance(diags, list)

    def test_malformed_xml_returns_empty(self):
        diags = parse_pycharm_xml(MALFORMED_XML)
        assert diags == []

    def test_no_problems_element_no_raise(self):
        diags = parse_pycharm_xml(NO_PROBLEMS_ELEMENT)
        assert isinstance(diags, list)

    def test_multiple_problems(self):
        xml = """\
<?xml version="1.0"?>
<problems version="1.0">
  <problem>
    <file>file:///C:/project/a.py</file>
    <line>1</line>
    <description><![CDATA[first]]></description>
    <problem_class id="Check1" severity="WARNING">x</problem_class>
  </problem>
  <problem>
    <file>file:///C:/project/b.py</file>
    <line>2</line>
    <description><![CDATA[second]]></description>
    <problem_class id="Check2" severity="ERROR">y</problem_class>
  </problem>
</problems>
"""
        diags = parse_pycharm_xml(xml)
        assert len(diags) == 2
        codes = {d.code for d in diags}
        assert "Check1" in codes
        assert "Check2" in codes

    def test_missing_line_element(self):
        xml = """\
<?xml version="1.0"?>
<problems version="1.0">
  <problem>
    <file>file:///C:/project/a.py</file>
    <description><![CDATA[no line]]></description>
    <problem_class id="Check" severity="WARNING">x</problem_class>
  </problem>
</problems>
"""
        diags = parse_pycharm_xml(xml)
        assert len(diags) == 1
        assert diags[0].line is None

    def test_returns_diagnostic_instances(self):
        diags = parse_pycharm_xml(UNRESOLVED_XML)
        assert all(isinstance(d, Diagnostic) for d in diags)


# ---------------------------------------------------------------------------
# File path normalization tests
# ---------------------------------------------------------------------------


class TestPathNormalization:
    def test_strips_file_prefix_via_dir(self, tmp_path):
        (tmp_path / "A.xml").write_text(UNRESOLVED_XML)
        result = parse_pycharm_dir(tmp_path)
        assert not result.diagnostics[0].file.startswith("file://")

    def test_windows_path_forward_slashes_via_dir(self, tmp_path):
        (tmp_path / "A.xml").write_text(UNRESOLVED_XML)
        result = parse_pycharm_dir(tmp_path)
        assert "\\" not in result.diagnostics[0].file

    def test_relative_to_project_root(self, tmp_path):
        # Write a single XML with an absolute path matching tmp_path
        project = tmp_path / "myproject"
        project.mkdir()
        src_file = project / "src" / "module.py"
        xml = f"""\
<?xml version="1.0"?>
<problems version="1.0">
  <problem>
    <file>file:///{str(src_file).replace(chr(92), "/")}</file>
    <line>1</line>
    <description><![CDATA[test]]></description>
    <problem_class id="Check" severity="WARNING">x</problem_class>
  </problem>
</problems>
"""
        xml_file = tmp_path / "Check.xml"
        xml_file.write_text(xml)
        result = parse_pycharm_dir(tmp_path, project_root=project)
        assert len(result.diagnostics) == 1
        f = result.diagnostics[0].file
        assert not f.startswith(str(project))
        assert "src" in f

    def test_no_project_root_keeps_absolute(self, tmp_path):
        (tmp_path / "A.xml").write_text(UNRESOLVED_XML)
        result = parse_pycharm_dir(tmp_path)
        assert "/" in result.diagnostics[0].file

    def test_backslash_path_in_file_element(self, tmp_path):
        xml = """\
<?xml version="1.0"?>
<problems version="1.0">
  <problem>
    <file>file:///C:\\Users\\user\\project\\src\\mod.py</file>
    <line>1</line>
    <description><![CDATA[backslash test]]></description>
    <problem_class id="Check" severity="WARNING">x</problem_class>
  </problem>
</problems>
"""
        (tmp_path / "A.xml").write_text(xml)
        result = parse_pycharm_dir(tmp_path)
        assert len(result.diagnostics) == 1
        assert "\\" not in result.diagnostics[0].file


# ---------------------------------------------------------------------------
# parse_pycharm_dir unit tests
# ---------------------------------------------------------------------------


class TestParsePycharmDir:
    def test_empty_dir_returns_ok(self, tmp_path):
        result = parse_pycharm_dir(tmp_path)
        assert result.tool == "pycharm"
        assert result.diagnostics == []
        assert "ok" in result.summary

    def test_single_xml_file(self, tmp_path):
        (tmp_path / "PyUnresolvedReferences.xml").write_text(UNRESOLVED_XML)
        result = parse_pycharm_dir(tmp_path)
        assert len(result.diagnostics) == 1

    def test_multiple_xml_files_aggregated(self, tmp_path):
        (tmp_path / "PyUnresolvedReferences.xml").write_text(UNRESOLVED_XML)
        (tmp_path / "PyUnusedImport.xml").write_text(UNUSED_IMPORT_XML)
        result = parse_pycharm_dir(tmp_path)
        assert len(result.diagnostics) == 2

    def test_error_sets_exit_code_1(self, tmp_path):
        (tmp_path / "PyTypeChecker.xml").write_text(ERROR_XML)
        result = parse_pycharm_dir(tmp_path)
        assert result.exit_code == 1

    def test_warning_only_exit_code_0(self, tmp_path):
        (tmp_path / "PyUnusedImport.xml").write_text(UNUSED_IMPORT_XML)
        result = parse_pycharm_dir(tmp_path)
        assert result.exit_code == 0

    def test_tool_name_is_pycharm(self, tmp_path):
        result = parse_pycharm_dir(tmp_path)
        assert result.tool == "pycharm"

    def test_summary_has_counts(self, tmp_path):
        (tmp_path / "A.xml").write_text(UNRESOLVED_XML)
        (tmp_path / "B.xml").write_text(ERROR_XML)
        result = parse_pycharm_dir(tmp_path)
        assert "errors" in result.summary or "warnings" in result.summary

    def test_summary_has_file_count(self, tmp_path):
        (tmp_path / "A.xml").write_text(UNRESOLVED_XML)
        result = parse_pycharm_dir(tmp_path)
        assert "files" in result.summary

    def test_malformed_xml_file_skipped(self, tmp_path):
        (tmp_path / "bad.xml").write_text(MALFORMED_XML)
        result = parse_pycharm_dir(tmp_path)
        assert result.diagnostics == []

    def test_non_xml_files_ignored(self, tmp_path):
        (tmp_path / "readme.txt").write_text("not xml")
        result = parse_pycharm_dir(tmp_path)
        assert result.diagnostics == []

    def test_as_text_contains_tool_header(self, tmp_path):
        (tmp_path / "A.xml").write_text(UNRESOLVED_XML)
        result = parse_pycharm_dir(tmp_path)
        assert "[pycharm]" in result.as_text()

    def test_as_text_shows_errors(self, tmp_path):
        (tmp_path / "A.xml").write_text(ERROR_XML)
        result = parse_pycharm_dir(tmp_path)
        text = result.as_text()
        assert "error" in text

    def test_as_text_shows_warnings(self, tmp_path):
        (tmp_path / "A.xml").write_text(UNRESOLVED_XML)
        result = parse_pycharm_dir(tmp_path)
        text = result.as_text()
        assert "warn" in text

    def test_as_json_valid(self, tmp_path):
        (tmp_path / "A.xml").write_text(UNRESOLVED_XML)
        result = parse_pycharm_dir(tmp_path)
        data = json.loads(result.as_json())
        assert data["tool"] == "pycharm"
        assert len(data["diagnostics"]) == 1

    def test_code_in_diagnostic(self, tmp_path):
        (tmp_path / "A.xml").write_text(UNRESOLVED_XML)
        result = parse_pycharm_dir(tmp_path)
        assert result.diagnostics[0].code == "PyUnresolvedReferences"

    def test_line_number_preserved(self, tmp_path):
        (tmp_path / "A.xml").write_text(UNRESOLVED_XML)
        result = parse_pycharm_dir(tmp_path)
        assert result.diagnostics[0].line == 42


# ---------------------------------------------------------------------------
# frob parse pycharm <dir> -- system tests via subprocess
# ---------------------------------------------------------------------------


def _run(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        FROB + list(args),
        capture_output=True,
        text=True,
    )


class TestParsePycharmCli:
    def test_exits_zero_on_warnings_only(self, tmp_path):
        (tmp_path / "PyUnusedImport.xml").write_text(UNUSED_IMPORT_XML)
        r = _run("parse", "pycharm", str(tmp_path))
        assert r.returncode == 0

    def test_shows_pycharm_in_output(self, tmp_path):
        (tmp_path / "PyUnusedImport.xml").write_text(UNUSED_IMPORT_XML)
        r = _run("parse", "pycharm", str(tmp_path))
        assert "pycharm" in r.stdout.lower()

    def test_shows_warning_code(self, tmp_path):
        (tmp_path / "PyUnusedImport.xml").write_text(UNUSED_IMPORT_XML)
        r = _run("parse", "pycharm", str(tmp_path))
        assert "PyUnusedImport" in r.stdout

    def test_json_output(self, tmp_path):
        (tmp_path / "PyUnusedImport.xml").write_text(UNUSED_IMPORT_XML)
        r = _run("parse", "pycharm", str(tmp_path), "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["tool"] == "pycharm"

    def test_error_requires_dir_arg(self):
        r = _run("parse", "pycharm")
        assert r.returncode != 0

    def test_non_dir_arg_exits_nonzero(self, tmp_path):
        f = tmp_path / "not_a_dir.txt"
        f.write_text("hi")
        r = _run("parse", "pycharm", str(f))
        assert r.returncode != 0

    def test_empty_dir_ok_output(self, tmp_path):
        r = _run("parse", "pycharm", str(tmp_path))
        assert r.returncode == 0
        assert "ok" in r.stdout.lower() or "pycharm" in r.stdout.lower()

    def test_multiple_xml_files(self, tmp_path):
        (tmp_path / "PyUnresolvedReferences.xml").write_text(UNRESOLVED_XML)
        (tmp_path / "PyUnusedImport.xml").write_text(UNUSED_IMPORT_XML)
        r = _run("parse", "pycharm", str(tmp_path))
        assert r.returncode == 0
        assert "2" in r.stdout

    def test_malformed_xml_does_not_crash(self, tmp_path):
        (tmp_path / "bad.xml").write_text(MALFORMED_XML)
        r = _run("parse", "pycharm", str(tmp_path))
        assert r.returncode == 0
