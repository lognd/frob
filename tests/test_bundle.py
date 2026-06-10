import pytest
from pathlib import Path

from frob.bundle import build_bundle, BundleError


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


@pytest.fixture
def py_project(tmp_path, py_sample):
    """sample.py imports from helper_mod.py."""
    (tmp_path / "sample.py").write_bytes(py_sample)
    (tmp_path / "helper_mod.py").write_text(
        "def utility(x: int) -> str:\n    return str(x)\n\ndef other() -> None:\n    pass\n"
    )
    # Patch sample to import from helper_mod
    src = py_sample.decode().replace(
        "import os\n", "import os\nfrom helper_mod import utility\n"
    )
    (tmp_path / "sample.py").write_text(src)
    return tmp_path


# ---------------------------------------------------------------------------
# Basic bundle
# ---------------------------------------------------------------------------


def test_bundle_ok(py_file):
    result = build_bundle(py_file, "helper")
    assert result.is_ok


def test_bundle_has_focus_section(py_file):
    bundle = build_bundle(py_file, "helper").danger_ok
    focus = [s for s in bundle.sections if s.role == "focus"]
    assert len(focus) == 1


def test_bundle_focus_contains_target_body(py_file):
    bundle = build_bundle(py_file, "helper").danger_ok
    focus = next(s for s in bundle.sections if s.role == "focus")
    assert 'return str(x)' in focus.content


def test_bundle_focus_stubs_non_target(py_file):
    bundle = build_bundle(py_file, "helper").danger_ok
    focus = next(s for s in bundle.sections if s.role == "focus")
    assert "do_something" not in focus.content


def test_bundle_total_tokens_correct(py_file):
    bundle = build_bundle(py_file, "helper").danger_ok
    assert bundle.total_tokens == sum(s.tokens for s in bundle.sections)


def test_bundle_total_tokens_positive(py_file):
    bundle = build_bundle(py_file, "helper").danger_ok
    assert bundle.total_tokens > 0


# ---------------------------------------------------------------------------
# Import depth
# ---------------------------------------------------------------------------


def test_bundle_depth1_includes_imports(py_project):
    sample = py_project / "sample.py"
    bundle = build_bundle(sample, "helper", depth=1).danger_ok
    import_sections = [s for s in bundle.sections if s.role == "import"]
    assert len(import_sections) > 0


def test_bundle_import_section_has_signatures(py_project):
    sample = py_project / "sample.py"
    bundle = build_bundle(sample, "helper", depth=1).danger_ok
    imp = next((s for s in bundle.sections if s.role == "import"), None)
    assert imp is not None
    # Signatures present, bodies stubbed
    assert "def utility" in imp.content
    assert "return str(x)" not in imp.content


def test_bundle_depth0_no_imports(py_file):
    bundle = build_bundle(py_file, "helper", depth=0).danger_ok
    import_sections = [s for s in bundle.sections if s.role == "import"]
    assert import_sections == []


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_bundle_target_not_found(py_file):
    result = build_bundle(py_file, "nonexistent")
    assert result.is_err
    assert result.danger_err == BundleError.TargetNotFound


def test_bundle_unsupported_language(tmp_path):
    f = tmp_path / "script.rb"
    f.write_text("def foo; end")
    result = build_bundle(f, "foo")
    assert result.is_err
    assert result.danger_err == BundleError.UnsupportedLanguage


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def test_bundle_as_markdown(py_file):
    bundle = build_bundle(py_file, "helper").danger_ok
    md = bundle.as_markdown()
    assert "# Bundle" in md
    assert "FOCUS" in md
    assert "helper" in md
    assert "```" in md


def test_bundle_as_json(py_file):
    import json
    bundle = build_bundle(py_file, "helper").danger_ok
    data = json.loads(bundle.as_json())
    assert data["target"] == "helper"
    assert isinstance(data["sections"], list)


# ---------------------------------------------------------------------------
# C++ bundle
# ---------------------------------------------------------------------------


def test_cpp_bundle_ok(cpp_file):
    result = build_bundle(cpp_file, "helper")
    assert result.is_ok


def test_cpp_bundle_focus_body(cpp_file):
    bundle = build_bundle(cpp_file, "helper").danger_ok
    focus = next(s for s in bundle.sections if s.role == "focus")
    assert "return;" in focus.content
