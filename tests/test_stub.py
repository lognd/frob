import pytest
from pathlib import Path

from frob.stub import stub_file, StubError
from typani import Ok, Err


@pytest.fixture
def py_file(tmp_path, py_sample):
    p = tmp_path / "sample.py"
    p.write_bytes(py_sample)
    return p


@pytest.fixture
def cpp_file(tmp_path, cpp_sample):
    p = tmp_path / "sample.cpp"
    p.write_bytes(cpp_sample)
    return p


def test_stub_py_method(py_file):
    result = stub_file(py_file, "MyClass.process")
    assert result.is_ok
    out = result.danger_ok
    assert "return data.decode().splitlines()" in out
    assert "return str(x)" not in out


def test_stub_py_top_level(py_file):
    result = stub_file(py_file, "helper")
    assert result.is_ok
    assert "return str(x)" in result.danger_ok


def test_stub_cpp_method(cpp_file):
    result = stub_file(cpp_file, "Engine::run")
    assert result.is_ok
    assert "i < cycles" in result.danger_ok
    assert "return 0" not in result.danger_ok


def test_stub_target_not_found(py_file):
    result = stub_file(py_file, "nonexistent")
    assert result.is_err
    assert result.danger_err == StubError.TargetNotFound


def test_stub_unsupported_language(tmp_path):
    f = tmp_path / "file.rb"
    f.write_text("def foo; end")
    result = stub_file(f, "foo")
    assert result.is_err
    assert result.danger_err == StubError.UnsupportedLanguage
