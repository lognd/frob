import pytest
from pathlib import Path

from frob.tokens import count_file, count_paths, estimate_tokens, TokenResult


def test_estimate_tokens_basic():
    # 350 chars of code -> ~100 tokens
    text = "x" * 350
    assert estimate_tokens(text) == 100


def test_estimate_tokens_bytes():
    assert estimate_tokens(b"hello world") > 0


def test_count_file_returns_nonzero(tmp_path, py_sample):
    p = tmp_path / "sample.py"
    p.write_bytes(py_sample)
    cost = count_file(p)
    assert cost.tokens > 0
    assert cost.chars == len(py_sample)


def test_count_file_detail_has_regions(tmp_path, py_sample):
    p = tmp_path / "sample.py"
    p.write_bytes(py_sample)
    cost = count_file(p, detail=True)
    assert len(cost.regions) > 0
    names = [r.name for r in cost.regions]
    assert "helper" in names or "MyClass" in names


def test_count_file_region_tokens_sum_le_total(tmp_path, py_sample):
    p = tmp_path / "sample.py"
    p.write_bytes(py_sample)
    cost = count_file(p, detail=True)
    region_sum = sum(r.tokens for r in cost.regions)
    # Regions don't cover imports/module-level code, so sum <= total
    assert region_sum <= cost.tokens


def test_count_paths_single_file(tmp_path, py_sample):
    p = tmp_path / "sample.py"
    p.write_bytes(py_sample)
    result = count_paths([p])
    assert result.total_tokens > 0
    assert len(result.files) == 1


def test_count_paths_directory(tmp_path, py_sample, cpp_sample):
    (tmp_path / "a.py").write_bytes(py_sample)
    (tmp_path / "b.cpp").write_bytes(cpp_sample)
    result = count_paths([tmp_path])
    assert len(result.files) == 2
    assert result.total_tokens > 0


def test_count_paths_total_equals_sum(tmp_path, py_sample, cpp_sample):
    (tmp_path / "a.py").write_bytes(py_sample)
    (tmp_path / "b.cpp").write_bytes(cpp_sample)
    result = count_paths([tmp_path])
    assert result.total_tokens == sum(f.tokens for f in result.files)


def test_as_text_contains_tokens(tmp_path, py_sample):
    p = tmp_path / "sample.py"
    p.write_bytes(py_sample)
    result = count_paths([p])
    text = result.as_text()
    assert "tokens" in text
    assert "sample.py" in text
