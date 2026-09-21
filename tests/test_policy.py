"""Tests for frob.policy: forbidden-import, pattern, norm rule kinds."""

from __future__ import annotations

from pathlib import Path

from frob.gitio import Diff, Hunk
from frob.graph import build_graph
from frob.policy import PolicyError, _files_under, load_policy, policy_gate


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _snapshot(root: Path):
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


class TestRules:
    def test_forbidden_import_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/policy/__init__.py::load_policy
        # frob:tests src/frob/policy/__init__.py::policy_gate
        _write(tmp_path, "src/frob/graph/x.py", "import requests\n")
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.forbidden-import]]\n"
            'id = "POL-no-requests"\n'
            'module = "requests"\n'
            'within = "src/frob/graph/**"\n'
            'reason = "graph must stay offline-pure"\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        assert len(rules) == 1
        diff = Diff(base="x", hunks=())
        violations = policy_gate(rules, snap, diff)
        violations_by_rule = {v.rule: v for v in violations}
        assert "POL-no-requests" in violations_by_rule
        assert violations_by_rule["POL-no-requests"].file == "src/frob/graph/x.py"

    def test_forbidden_import_passes_outside_glob(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/frob/other/x.py", "import requests\n")
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.forbidden-import]]\n"
            'id = "POL-no-requests"\n'
            'module = "requests"\n'
            'within = "src/frob/graph/**"\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=())
        violations = policy_gate(rules, snap, diff)
        assert violations == ()

    def test_forbidden_import_malformed_missing_field(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "frob.toml",
            '[[policy.forbidden-import]]\nid = "POL-x"\nmodule = "requests"\n',
        )
        result = load_policy(tmp_path)
        assert result.is_err
        assert result.danger_err == PolicyError.MalformedRule

    def test_pattern_query_matches(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/frob/x.py", "requests.get('http://x')\n")
        (tmp_path / "policy").mkdir()
        (tmp_path / "policy" / "queries").mkdir()
        (tmp_path / "policy" / "queries" / "POL-no-requests-call.scm").write_text(
            "(call function: (attribute) @fn)"
        )
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.pattern]]\n"
            'id = "POL-no-requests-call"\n'
            'language = "python"\n'
            'globs = ["src/**/*.py"]\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=())
        violations = policy_gate(rules, snap, diff)
        assert any(v.rule == "POL-no-requests-call" for v in violations)

    def test_pattern_bad_query_is_err(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.pattern]]\n"
            'id = "POL-bad"\n'
            'language = "python"\n'
            'query = "(this is not (( valid"\n',
        )
        result = load_policy(tmp_path)
        assert result.is_err
        assert result.danger_err == PolicyError.BadQuery

    def test_pattern_missing_query_file_is_err(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "frob.toml",
            '[[policy.pattern]]\nid = "POL-missing"\nlanguage = "python"\n',
        )
        result = load_policy(tmp_path)
        assert result.is_err
        assert result.danger_err == PolicyError.BadQuery

    def test_norm_max_diff_lines_fires(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "frob.toml",
            '[[policy.norm]]\nid = "POL-max-diff"\nmax_diff_lines = 10\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=(Hunk(file="a.py", span=(1, 50)),))
        violations = policy_gate(rules, snap, diff)
        assert any(v.rule == "POL-max-diff" for v in violations)

    def test_norm_passes_under_limit(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "frob.toml",
            '[[policy.norm]]\nid = "POL-max-diff"\nmax_diff_lines = 400\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=(Hunk(file="a.py", span=(1, 5)),))
        violations = policy_gate(rules, snap, diff)
        assert violations == ()

    def test_norm_malformed_missing_max_lines(self, tmp_path: Path) -> None:
        _write(tmp_path, "frob.toml", '[[policy.norm]]\nid = "POL-max-diff"\n')
        result = load_policy(tmp_path)
        assert result.is_err
        assert result.danger_err == PolicyError.MalformedRule

    def test_no_frob_toml_is_ok_empty(self, tmp_path: Path) -> None:
        result = load_policy(tmp_path)
        assert result.is_ok
        assert result.danger_ok == ()

    def test_glob_double_star_matches_file_directly_under_prefix(
        self, tmp_path: Path
    ) -> None:
        """T-4013 must-fire fixture: `app/**/*.py` must cover a file
        directly under `app/`, not just one nested in a subdirectory --
        `fnmatch` degrades `**` to "at least one intervening directory"
        and silently missed exactly this file; gitwildmatch semantics
        (what every policy author actually means by `**`) must not."""
        _write(tmp_path, "app/request_context.py", "import socket\n")
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.forbidden-import]]\n"
            'id = "POL-raw-client-ip"\n'
            'module = "socket"\n'
            'within = "app/**/*.py"\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=())
        violations = policy_gate(rules, snap, diff)
        violations_by_rule = {v.rule: v for v in violations}
        assert "POL-raw-client-ip" in violations_by_rule
        assert violations_by_rule["POL-raw-client-ip"].file == "app/request_context.py"

    def test_glob_stays_quiet_outside_matched_directory(self, tmp_path: Path) -> None:
        """T-4013 must-stay-quiet fixture: the gitwildmatch widening is
        bounded -- a file genuinely outside `app/**/*.py` (a sibling
        directory) still does not match."""
        _write(tmp_path, "other/request_context.py", "import socket\n")
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.forbidden-import]]\n"
            'id = "POL-raw-client-ip"\n'
            'module = "socket"\n'
            'within = "app/**/*.py"\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=())
        violations = policy_gate(rules, snap, diff)
        assert violations == ()

    # frob:ticket T-4280
    def test_backslash_joined_path_matches_a_posix_glob_on_every_platform(
        self, tmp_path: Path
    ) -> None:
        """T-4280: `_compiled_glob(...).match_file` derives its separator-
        normalization set from `os.sep`/`os.altsep` when none is given --
        measured on real Windows vs. Linux, that made the SAME
        `("vendor/**", "vendor\\sub\\mod.py")` pair match on Windows but
        NOT on Linux (the identical class of bug T-4155 fixed for
        `frob.excludes.is_excluded`'s own `match_file` call). Pinning
        `separators=("\\",)` explicitly (this ticket's fix) makes a
        backslash-joined path fold to `/` before matching regardless of
        host, so the answer is identical everywhere -- a real `GraphSnapshot`
        never actually produces a backslash-joined key (every in-repo
        producer emits POSIX-relative paths already), so a real snapshot's
        `file_hashes` is overridden via `model_copy` to exercise the
        boundary case directly rather than reasoning about it."""
        snap = _snapshot(tmp_path)
        snap = snap.model_copy(
            update={
                "file_hashes": {
                    "vendor\\sub\\mod.py": "deadbeef",
                    "other/mod.py": "beef",
                }
            }
        )
        matched = _files_under(tmp_path, snap, "vendor/**")
        assert matched == ("vendor\\sub\\mod.py",)


# frob:ticket T-4030
class TestDangerousInnerHtmlJsonStringify:
    """T-4030: policy.pattern can express the dangerouslySetInnerHTML +
    direct JSON.stringify(...) XSS shape as a real tree-sitter query,
    purely structural (a JSX attribute containing a specific call-
    expression shape), no data-flow analysis required. MUST SEQUENCE
    AFTER T-4013's fnmatch-glob fix (done -- `_files_under` already uses
    gitwildmatch semantics, see `TestRules`'s T-4013 tests above)."""

    _QUERY = (
        "(jsx_attribute\n"
        "  (property_identifier) @_attr\n"
        "  (jsx_expression\n"
        "    (object\n"
        "      (pair\n"
        "        value: (call_expression\n"
        "          function: (member_expression\n"
        "            object: (identifier) @_json\n"
        "            property: (property_identifier) @_stringify))))) @danger\n"
        '  (#eq? @_attr "dangerouslySetInnerHTML")\n'
        '  (#eq? @_json "JSON")\n'
        '  (#eq? @_stringify "stringify"))\n'
    )

    # frob:ticket T-4030
    def _write_rule(self, tmp_path: Path) -> None:
        """Write the shared `frob.toml` + `.scm` query-file fixture."""
        (tmp_path / "policy").mkdir()
        (tmp_path / "policy" / "queries").mkdir()
        (
            tmp_path / "policy" / "queries" / "POL-danger-html-json-stringify.scm"
        ).write_text(self._QUERY)
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.pattern]]\n"
            'id = "POL-danger-html-json-stringify"\n'
            'language = "tsx"\n'
            'globs = ["src/**/*.tsx"]\n',
        )

    # frob:ticket T-4030
    def test_fires_on_direct_json_stringify(self, tmp_path: Path) -> None:
        """Positive control: `dangerouslySetInnerHTML={{__html:
        JSON.stringify(data)}}` -- unescaped HTML built from a JSON
        serialization that does not escape `</script>`-breaking
        sequences -- must fire."""
        _write(
            tmp_path,
            "src/Widget.tsx",
            "const X = () => <div "
            "dangerouslySetInnerHTML={{__html: JSON.stringify(data)}} />;\n",
        )
        self._write_rule(tmp_path)
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=())
        violations = policy_gate(rules, snap, diff)
        assert any(v.rule == "POL-danger-html-json-stringify" for v in violations)

    # frob:ticket T-4030
    def test_stays_quiet_on_sanitized_value(self, tmp_path: Path) -> None:
        """Near-miss control: the SAME attribute with a call to something
        other than `JSON.stringify` (e.g. a real sanitizer) must not
        fire -- the query is structural on the exact call shape, not on
        `dangerouslySetInnerHTML` alone. A sibling file with a real hit
        keeps the rule's overall match count nonzero (T-3986's POL000 is
        deliberately a SEPARATE concern -- an all-near-miss glob set is
        covered by `TestPol000`, not here)."""
        _write(
            tmp_path,
            "src/Widget.tsx",
            "const X = () => <div "
            "dangerouslySetInnerHTML={{__html: sanitize(data)}} />;\n",
        )
        _write(
            tmp_path,
            "src/Other.tsx",
            "const Y = () => <div "
            "dangerouslySetInnerHTML={{__html: JSON.stringify(data)}} />;\n",
        )
        self._write_rule(tmp_path)
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=())
        violations = policy_gate(rules, snap, diff)
        violated_files = {
            v.file for v in violations if v.rule == "POL-danger-html-json-stringify"
        }
        assert violated_files == {"src/Other.tsx"}


# frob:ticket T-3986
class TestPol000:
    """T-3986: policy.pattern matching zero nodes is a config error."""

    # frob:ticket T-3986
    def test_pol000_fires_on_zero_match_pattern(self, tmp_path: Path) -> None:
        """Positive control: a compiling query for a node type that never
        occurs anywhere in the declared glob set (a malformed/over-narrow
        pattern) must fire POL000, distinct from a clean pass."""
        _write(tmp_path, "src/frob/x.py", "x = 1\n")
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.pattern]]\n"
            'id = "POL-no-classes"\n'
            'language = "python"\n'
            'query = "(class_definition) @cls"\n'
            'globs = ["src/**/*.py"]\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=())
        violations = policy_gate(rules, snap, diff)
        pol000 = [v for v in violations if v.rule == "POL000"]
        assert len(pol000) == 1
        assert "POL-no-classes" in pol000[0].message

    # frob:ticket T-3986
    def test_pol000_stays_quiet_on_real_match(self, tmp_path: Path) -> None:
        """Negative control: a pattern that matches at least one node (and
        produces a real violation) must NOT fire POL000 -- a clean pass over
        genuinely no violations is not what this test exercises; this
        confirms a firing pattern stays quiet on POL000 itself."""
        _write(tmp_path, "src/frob/x.py", "requests.get('http://x')\n")
        (tmp_path / "policy").mkdir()
        (tmp_path / "policy" / "queries").mkdir()
        (tmp_path / "policy" / "queries" / "POL-no-requests-call.scm").write_text(
            "(call function: (attribute) @fn)"
        )
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.pattern]]\n"
            'id = "POL-no-requests-call"\n'
            'language = "python"\n'
            'globs = ["src/**/*.py"]\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=())
        violations = policy_gate(rules, snap, diff)
        assert any(v.rule == "POL-no-requests-call" for v in violations)
        assert not any(v.rule == "POL000" for v in violations)

    # frob:ticket T-3986
    def test_pol000_stays_quiet_when_underscore_capture_only_matches(
        self, tmp_path: Path
    ) -> None:
        """A query that matches real structure via an underscore-prefixed
        (anchor-only, not reported) capture has a nonzero match count even
        though it produces zero violations -- POL000 must stay quiet, since
        this is a legitimate clean pass, not a config error."""
        _write(tmp_path, "src/frob/x.py", "requests.get('http://x')\n")
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.pattern]]\n"
            'id = "POL-anchor-only"\n'
            'language = "python"\n'
            'query = "(call function: (attribute) @_fn)"\n'
            'globs = ["src/**/*.py"]\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=())
        violations = policy_gate(rules, snap, diff)
        assert not any(v.rule == "POL-anchor-only" for v in violations)
        assert not any(v.rule == "POL000" for v in violations)

    # frob:ticket T-3986
    def test_pol000_stays_quiet_for_warn_severity(self, tmp_path: Path) -> None:
        """A non-enforcing (`severity = "warn"`) pattern matching zero nodes
        is not treated as a config error by POL000 -- only an enforcing
        pattern is."""
        _write(tmp_path, "src/frob/x.py", "x = 1\n")
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.pattern]]\n"
            'id = "POL-no-classes-warn"\n'
            'language = "python"\n'
            'query = "(class_definition) @cls"\n'
            'globs = ["src/**/*.py"]\n'
            'severity = "warn"\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=())
        violations = policy_gate(rules, snap, diff)
        assert not any(v.rule == "POL000" for v in violations)
