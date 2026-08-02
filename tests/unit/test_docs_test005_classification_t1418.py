"""Drift-lock for T-1418's TEST005 zero-percent classification deliverable
(`docs/audits/test005-zero-classification-t1418.csv`) -- locks the row
count and the classification totals the Done report claims so a future
edit to that CSV cannot silently drift out of sync with its own summary
table without a test noticing."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

_CSV = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "audits"
    / "test005-zero-classification-t1418.csv"
)


class TestClassificationCsv:
    """Shape/count assertions over the 306-row TEST005 classification
    table T-1418 produced."""

    # frob:tests \
    # tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv.test_\
    # has_exactly_306_rows
    def test_has_exactly_306_rows(self) -> None:
        with _CSV.open(newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter="|"))
        assert len(rows) == 306

    # frob:tests \
    # tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv.test_\
    # every_row_has_a_named_covering_test
    def test_every_row_has_a_named_covering_test(self) -> None:
        with _CSV.open(newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter="|"))
        assert all(row["covering_tests"].strip() for row in rows)

    # frob:tests \
    # tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv.test_\
    # classification_totals_match_the_audit_doc
    def test_classification_totals_match_the_audit_doc(self) -> None:
        with _CSV.open(newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter="|"))
        counts = Counter(row["classification"] for row in rows)
        assert counts["attribution artifact"] == 283
        assert counts["attribution artifact (partial)"] == 23
        assert counts.get("genuine gap", 0) == 0
