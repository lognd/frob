"""Unit tests for new parsers: cargo, clang-tidy, valgrind."""

from frob.process.parsers.cargo import parse_cargo
from frob.process.parsers.clang_tidy import parse_clang_tidy
from frob.process.parsers.valgrind import parse_valgrind


class TestParseCargo:
    def test_clean_build(self):
        r = parse_cargo("", exit_code=0)
        assert r.passed
        assert r.error_count == 0

    def test_json_error(self):
        json_msg = (
            '{"reason":"compiler-message","message":{"level":"error",'
            '"message":"type mismatch","code":{"code":"E0308"},'
            '"rendered":"error[E0308]: type mismatch\\n",'
            '"spans":[{"file_name":"src/main.rs","line_start":10,'
            '"column_start":5,"is_primary":true}]}}\n'
        )
        r = parse_cargo(json_msg, exit_code=1)
        assert r.error_count == 1
        assert r.diagnostics[0].code == "E0308"
        assert r.diagnostics[0].file == "src/main.rs"
        assert r.diagnostics[0].line == 10

    def test_json_warning(self):
        json_msg = (
            '{"reason":"compiler-message","message":{"level":"warning",'
            '"message":"unused variable","code":{"code":"unused_variables"},'
            '"rendered":"warning: unused variable\\n",'
            '"spans":[{"file_name":"src/lib.rs","line_start":3,'
            '"column_start":9,"is_primary":true}]}}\n'
        )
        r = parse_cargo(json_msg, exit_code=0)
        assert r.warning_count == 1
        assert r.diagnostics[0].severity == "warning"

    def test_text_tests_passing(self):
        text = (
            "test foo::bar ... ok\n"
            "test foo::baz ... ok\n"
            "test result: ok. 2 passed; 0 failed; 0 ignored\n"
        )
        r = parse_cargo(text, exit_code=0)
        assert r.passed
        assert len(r.tests) == 2
        assert all(t.passed for t in r.tests)

    def test_text_tests_failing(self):
        text = (
            "test foo::bar ... ok\n"
            "test foo::bad ... FAILED\n"
            "---- foo::bad stdout ----\n"
            "thread 'foo::bad' panicked at 'assertion failed'\n"
            "\n"
        )
        r = parse_cargo(text, exit_code=101)
        assert not r.passed
        failed = [t for t in r.tests if not t.passed]
        assert len(failed) == 1
        assert failed[0].name == "foo::bad"

    def test_text_ignored(self):
        text = "test slow_test ... ignored\n"
        r = parse_cargo(text, exit_code=0)
        assert r.tests[0].skipped


class TestParseClangTidy:
    def test_clean(self):
        # frob:tests src/frob/process/parsers/clang_tidy.py::parse_clang_tidy \
        # kind="unit"
        r = parse_clang_tidy("", exit_code=0)
        assert r.error_count == 0
        assert r.warning_count == 0

    def test_warning(self):
        text = "src/foo.cpp:10:5: warning: use nullptr [modernize-use-nullptr]\n"
        r = parse_clang_tidy(text, exit_code=1)
        assert r.warning_count == 1
        d = r.diagnostics[0]
        assert d.file == "src/foo.cpp"
        assert d.line == 10
        assert d.code == "modernize-use-nullptr"

    def test_error(self):
        text = "src/bar.cpp:5:3: error: expected ';' []\n"
        r = parse_clang_tidy(text, exit_code=1)
        assert r.error_count == 1
        assert r.diagnostics[0].severity == "error"

    def test_notes_skipped(self):
        text = (
            "src/foo.cpp:10:5: warning: bad thing [check-name]\n"
            "src/foo.cpp:8:1: note: declared here\n"
        )
        r = parse_clang_tidy(text)
        assert r.warning_count == 1
        assert r.error_count == 0

    def test_deduplication(self):
        # Same location/check should only appear once
        line = "src/foo.cpp:10:5: warning: bad thing [check-name]\n"
        r = parse_clang_tidy(line * 3)
        assert r.warning_count == 1

    def test_ansi_stripped(self):
        text = "\x1b[1;35msrc/x.cpp\x1b[0m:3:1: warning: something [my-check]\n"
        r = parse_clang_tidy(text)
        assert r.warning_count == 1
        assert r.diagnostics[0].file == "src/x.cpp"


class TestParseValgrind:
    _SUMMARY = (
        "==12==\n"
        "==12== HEAP SUMMARY:\n"
        "==12==   definitely lost: 24 bytes in 1 blocks\n"
        "==12==   indirectly lost: 0 bytes in 0 blocks\n"
        "==12==   possibly lost: 0 bytes in 0 blocks\n"
        "==12==   still reachable: 72,704 bytes in 1 blocks\n"
        "==12== ERROR SUMMARY: 1 errors from 1 contexts\n"
    )

    def test_clean(self):
        # frob:tests src/frob/process/parsers/valgrind.py::parse_valgrind kind="unit"
        text = "==1== ERROR SUMMARY: 0 errors from 0 contexts\n"
        r = parse_valgrind(text, exit_code=0)
        assert r.error_count == 0

    def test_definite_leak_is_error(self):
        r = parse_valgrind(self._SUMMARY, exit_code=1)
        assert r.error_count >= 1
        msgs = [d.message for d in r.diagnostics]
        assert any("definitely lost" in m for m in msgs)

    def test_summary_in_output(self):
        r = parse_valgrind(self._SUMMARY, exit_code=1)
        assert r.summary  # non-empty

    def test_xml_clean(self):
        xml = '<?xml version="1.0"?><valgrindoutput></valgrindoutput>'
        r = parse_valgrind(xml, exit_code=0)
        assert r.error_count == 0

    def test_xml_error(self):
        xml = (
            '<?xml version="1.0"?>'
            "<valgrindoutput>"
            "<error>"
            "<kind>DefinitelyLost</kind>"
            "<what>24 bytes in 1 blocks are definitely lost</what>"
            "<stack><frame><file>foo.c</file><line>10</line></frame></stack>"
            "</error>"
            "</valgrindoutput>"
        )
        r = parse_valgrind(xml, exit_code=1)
        assert r.error_count == 1
        assert r.diagnostics[0].file == "foo.c"
        assert r.diagnostics[0].line == 10
