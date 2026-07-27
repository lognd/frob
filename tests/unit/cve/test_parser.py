"""Tests for frob.cve: record parsing and mirror walking against real,
committed CVE Record Format v5 fixtures (no network -- docs/modules/cve.md
"No network" is a hard requirement, honored here and in the parser)."""

from __future__ import annotations

from pathlib import Path

from frob.cve import CveError, CveState, iter_mirror, parse_record

_FIXTURES = Path(__file__).parent / "fixtures"


def test_fixtures_are_ascii_and_escaped_unicode_round_trips() -> None:
    # frob:tests src/frob/cve/_parser.py::parse_record kind="unit"
    """The repo's ASCII-only rule applies to fixtures too: every committed
    fixture file must contain only ASCII bytes. Non-ASCII characters in the
    real upstream records (e.g. curly quotes, German umlauts) are preserved
    via JSON \\uXXXX escaping, not dropped or transliterated -- this
    spot-checks one escaped field (CVE-2024-4681's German description)
    round-trips through `parse_record` to the exact original unicode
    string, locking both the ASCII-on-disk rule and semantic fidelity."""
    for path in _FIXTURES.rglob("*.json"):
        raw_bytes = path.read_bytes()
        assert all(b < 0x80 for b in raw_bytes), (
            f"{path} contains non-ASCII bytes; escape with "
            f"json.dump(..., ensure_ascii=True)"
        )

    record = parse_record(_FIXTURES / "CVE-2024-4681.json").danger_ok
    # frob:waive PERF003 reason="one next() lookup over one record's small \
    # descriptions[] list, not a nested join"
    german = next(d.value for d in record.containers.cna.descriptions if d.lang == "de")
    assert german.startswith(
        "Es wurde eine Schwachstelle in Campcodes Legal Case Management System"
    )
    assert "Schwachstelle" in german
    # the escaped umlaut decodes back to the real unicode codepoint U+00FC
    # (constructed via chr() so this source file itself stays pure ASCII)
    assert chr(0xFC) in german


def test_parse_log4shell_multi_adp_and_cwe() -> None:
    # frob:tests src/frob/cve/_parser.py::parse_record kind="unit"
    """CVE-2021-44228 (Log4Shell): multiple ADP containers, CVSS v3.1 on an
    ADP container, and CNA problemTypes carrying real CWE ids."""
    result = parse_record(_FIXTURES / "CVE-2021-44228.json")
    assert result.is_ok
    record = result.danger_ok
    assert record.cveMetadata.cveId == "CVE-2021-44228"
    assert record.cveMetadata.state == CveState.PUBLISHED
    assert len(record.containers.adp) == 2

    # frob:waive PERF003 reason="two flat set/list comprehensions over one record's \
    # small nested lists, not a join"
    cwe_ids = {
        desc.cweId
        for pt in record.containers.cna.problemTypes
        for desc in pt.descriptions
        if desc.cweId is not None
    }
    assert "CWE-502" in cwe_ids
    assert "CWE-400" in cwe_ids
    assert "CWE-20" in cwe_ids

    v3_scores = [
        m.cvssV3_1
        for adp in record.containers.adp
        for m in adp.metrics
        if m.cvssV3_1 is not None
    ]
    assert v3_scores
    assert v3_scores[0].baseScore == 10
    assert v3_scores[0].baseSeverity == "CRITICAL"


def test_parse_version_ranges_with_less_than() -> None:
    # frob:tests src/frob/cve/_parser.py::parse_record kind="unit"
    """CVE-2023-38545 (curl socks5): version ranges via lessThan +
    versionType, both affected and unaffected statuses in one list."""
    result = parse_record(_FIXTURES / "CVE-2023-38545.json")
    assert result.is_ok
    record = result.danger_ok
    affected = record.containers.cna.affected
    assert len(affected) == 1
    assert affected[0].vendor == "curl"
    versions = affected[0].versions
    # frob:waive PERF003 reason="two separate any() assertions over one small \
    # versions[] list, not a nested join"
    assert any(
        v.status == "affected" and v.lessThan == "8.4.0" and v.versionType == "semver"
        for v in versions
    )
    assert any(v.status == "unaffected" and v.lessThan == "7.69.0" for v in versions)


def test_parse_multi_vendor_affected() -> None:
    # frob:tests src/frob/cve/_parser.py::parse_record kind="unit"
    """CVE-2024-3094 (xz backdoor): several affected[] entries across
    vendors, exercising defaultStatus alongside explicit versions."""
    result = parse_record(_FIXTURES / "CVE-2024-3094.json")
    assert result.is_ok
    record = result.danger_ok
    affected = record.containers.cna.affected
    assert len(affected) > 1
    assert any(a.defaultStatus == "unaffected" for a in affected)


def test_parse_cvss_v4() -> None:
    # frob:tests src/frob/cve/_parser.py::parse_record kind="unit"
    """CVE-2024-4681: a record whose CNA metrics carry a cvssV4_0 score."""
    result = parse_record(_FIXTURES / "CVE-2024-4681.json")
    assert result.is_ok
    record = result.danger_ok
    v4_scores = [m.cvssV4_0 for m in record.containers.cna.metrics if m.cvssV4_0]
    assert v4_scores
    assert v4_scores[0].version == "4.0"
    assert v4_scores[0].vectorString.startswith("CVSS:4.0/")


def test_parse_rejected_record() -> None:
    # frob:tests src/frob/cve/_parser.py::parse_record kind="unit"
    """CVE-2024-7039: a REJECTED-state record parses fully -- state alone
    tells callers to skip it, the parse itself never fails for that
    reason."""
    result = parse_record(_FIXTURES / "CVE-2024-7039.json")
    assert result.is_ok
    record = result.danger_ok
    assert record.cveMetadata.state == CveState.REJECTED
    assert record.cveMetadata.dateRejected != ""


def test_parse_missing_file() -> None:
    # frob:tests src/frob/cve/_parser.py::parse_record kind="unit"
    """A record path that does not exist is `Err(CveError.NotFound)`, never
    an exception."""
    result = parse_record(_FIXTURES / "CVE-0000-00000.json")
    assert result.is_err
    assert result.danger_err == CveError.NotFound


def test_parse_truncated_json() -> None:
    # frob:tests src/frob/cve/_parser.py::parse_record kind="unit"
    """Truncated/corrupt JSON is `Err(CveError.NotJson)`."""
    result = parse_record(
        _FIXTURES / "mirror" / "cves" / "2024" / "9xxx" / "CVE-2024-9999.json"
    )
    assert result.is_err
    assert result.danger_err == CveError.NotJson


def test_parse_missing_required_field() -> None:
    # frob:tests src/frob/cve/_parser.py::parse_record kind="unit"
    """Valid JSON that lacks a required field (here `cveMetadata.state`) is
    a typed `Err(CveError.MalformedRecord)`, not a silently partial
    `CveRecord`."""
    result = parse_record(
        _FIXTURES / "mirror" / "cves" / "2024" / "8xxx" / "CVE-2024-8888.json"
    )
    assert result.is_err
    assert result.danger_err == CveError.MalformedRecord


def test_iter_mirror_yields_records_and_errors() -> None:
    # frob:tests src/frob/cve/_parser.py::iter_mirror kind="unit"
    """`iter_mirror` walks the whole `cves/YYYY/NNNxxx/` layout and yields
    every file's `(path, Result)` -- both the five valid records and the
    two deliberately broken ones, with none silently dropped."""
    root = _FIXTURES / "mirror"
    results = list(iter_mirror(root))
    assert len(results) == 7

    # frob:waive PERF003 reason="one set comprehension plus one dict comprehension \
    # over 7 fixture results, not a join"
    ok_ids = {r.danger_ok.cveMetadata.cveId for _, r in results if r.is_ok}
    assert ok_ids == {
        "CVE-2021-44228",
        "CVE-2023-38545",
        "CVE-2024-3094",
        "CVE-2024-4681",
        "CVE-2024-7039",
    }

    err_paths = {path.name: r.danger_err for path, r in results if r.is_err}
    assert err_paths == {
        "CVE-2024-9999.json": CveError.NotJson,
        "CVE-2024-8888.json": CveError.MalformedRecord,
    }


def test_iter_mirror_invalid_root() -> None:
    # frob:tests src/frob/cve/_parser.py::iter_mirror kind="unit"
    """A mirror root that is not a directory yields a single typed error
    entry rather than raising or yielding nothing (vacuous-pass
    doctrine)."""
    root = _FIXTURES / "not-a-real-mirror-dir"
    results = list(iter_mirror(root))
    assert len(results) == 1
    path, result = results[0]
    assert path == root
    assert result.is_err
    assert result.danger_err == CveError.MirrorPathInvalid


def test_cve_module_end_to_end_over_mirror() -> None:
    # frob:tests src/frob/cve kind="integration"
    """End-to-end: walk a real mirror layout with `iter_mirror`, and for
    every successfully parsed record touch the full model graph this
    module exposes (metadata, both container kinds, affected/versions,
    problemTypes/CWE, CVSS metrics, references, descriptions) -- catches
    breakage across the parser/model boundary that a single-fixture unit
    test would miss."""
    root = _FIXTURES / "mirror"
    records = [r.danger_ok for _, r in iter_mirror(root) if r.is_ok]
    assert len(records) == 5

    # frob:waive PERF003 reason="a walk over 5 fixture records' small nested model \
    # graph, not a join"
    for record in records:
        assert record.cveMetadata.cveId.startswith("CVE-")
        assert record.cveMetadata.state in (CveState.PUBLISHED, CveState.REJECTED)
        for container in (record.containers.cna, *record.containers.adp):
            for affected in container.affected:
                for version in affected.versions:
                    assert version.version != ""
                    assert version.status != ""
            for problem_type in container.problemTypes:
                for description in problem_type.descriptions:
                    assert description.lang != "" or description.description == ""
            for metric in container.metrics:
                if metric.cvssV3_1 is not None:
                    assert metric.cvssV3_1.version != ""
                if metric.cvssV4_0 is not None:
                    assert metric.cvssV4_0.version != ""
            for reference in container.references:
                assert reference.url.startswith(("http://", "https://"))
            for description in container.descriptions:
                assert isinstance(description.value, str)
