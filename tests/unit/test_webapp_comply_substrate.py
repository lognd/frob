"""frob.webapp._comply_substrate coverage: signal detection plus
required-page presence, positive and negative controls.

frob:ticket T-5360
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.webapp import FrameworkKind
from frob.webapp._comply_substrate import (
    ComplyScanError,
    ComplySignal,
    RequiredPage,
    detect_required_pages,
    detect_signals,
)

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "comply1xx"
)

_SIGNAL_CASES = [
    ("signal_email", ComplySignal.EMAIL_COLLECTION),
    ("signal_ai", ComplySignal.AI_ON_USER_DATA),
    ("signal_subscriptions", ComplySignal.SUBSCRIPTIONS),
    ("signal_data_sale", ComplySignal.DATA_SALE_OR_SHARE),
    ("signal_sms", ComplySignal.SMS),
    ("signal_session_replay", ComplySignal.SESSION_REPLAY_OR_PIXEL),
    ("signal_health", ComplySignal.HEALTH_DATA),
]


@pytest.mark.parametrize("fixture_dir,expected", _SIGNAL_CASES)
# frob:tests src/frob/webapp/_comply_substrate.py::detect_signals kind="unit"
# frob:tests src/frob/webapp/_comply_substrate.py::ComplySignal kind="unit"
def test_detect_signals_positive_control(fixture_dir: str, expected: ComplySignal):
    """MUST-FIRE: each signal fixture's manifest detects as exactly that one signal."""
    root = _FIXTURE_ROOT / fixture_dir
    assert detect_signals(root) == frozenset({expected})


# frob:tests src/frob/webapp/_comply_substrate.py::detect_signals kind="unit"
def test_detect_signals_plain_is_empty():
    """MUST-FIRE: a plain repo with no COMPLY-relevant packages detects no signal --
    the empty-set short-circuit COMPLY rules rely on."""
    root = _FIXTURE_ROOT / "plain"
    assert detect_signals(root) == frozenset()


# frob:tests src/frob/webapp/_comply_substrate.py::detect_signals kind="unit"
def test_detect_signals_missing_root_is_empty(tmp_path: Path):
    """A root with no files at all detects no signal (no crash on absent manifests)."""
    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    assert detect_signals(empty_root) == frozenset()


# frob:tests src/frob/webapp/_comply_substrate.py::detect_required_pages kind="unit"
# frob:tests src/frob/webapp/_comply_substrate.py::RequiredPage kind="unit"
def test_detect_required_pages_nextjs_present():
    """MUST-FIRE: a Next.js fixture with all three page files detects all three pages."""
    root = _FIXTURE_ROOT / "pages_nextjs_present"
    result = detect_required_pages(root, frozenset({FrameworkKind.NEXTJS}))
    assert result.is_ok
    assert result.ok == frozenset(
        {RequiredPage.PRIVACY, RequiredPage.TERMS, RequiredPage.ACCESSIBILITY}
    )


# frob:tests src/frob/webapp/_comply_substrate.py::detect_required_pages kind="unit"
def test_detect_required_pages_nextjs_missing():
    """A Next.js fixture with no page files detects none present."""
    root = _FIXTURE_ROOT / "pages_nextjs_missing"
    result = detect_required_pages(root, frozenset({FrameworkKind.NEXTJS}))
    assert result.is_ok
    assert result.ok == frozenset()


# frob:tests src/frob/webapp/_comply_substrate.py::detect_required_pages kind="unit"
def test_detect_required_pages_flask_present():
    """MUST-FIRE: a Flask fixture whose app.py routes all three slugs detects all three pages."""
    root = _FIXTURE_ROOT / "pages_flask_present"
    result = detect_required_pages(root, frozenset({FrameworkKind.FLASK}))
    assert result.is_ok
    assert result.ok == frozenset(
        {RequiredPage.PRIVACY, RequiredPage.TERMS, RequiredPage.ACCESSIBILITY}
    )


# frob:tests src/frob/webapp/_comply_substrate.py::detect_required_pages kind="unit"
def test_detect_required_pages_flask_missing():
    """A Flask fixture whose app.py routes none of the three slugs detects none present."""
    root = _FIXTURE_ROOT / "pages_flask_missing"
    result = detect_required_pages(root, frozenset({FrameworkKind.FLASK}))
    assert result.is_ok
    assert result.ok == frozenset()


# frob:tests src/frob/webapp/_comply_substrate.py::detect_required_pages kind="unit"
def test_detect_required_pages_no_frameworks_is_empty_ok():
    """A plain CLI repo (no detected framework) has no router to check -- Ok(empty), not Err."""
    root = _FIXTURE_ROOT / "plain"
    result = detect_required_pages(root, frozenset())
    assert result.is_ok
    assert result.ok == frozenset()


# frob:tests src/frob/webapp/_comply_substrate.py::detect_required_pages kind="unit"
# frob:tests src/frob/webapp/_comply_substrate.py::ComplyScanError kind="unit"
def test_detect_required_pages_missing_root_is_err(tmp_path: Path):
    """A root that does not exist at all is a scan error, not a silent empty Ok."""
    missing_root = tmp_path / "does-not-exist"
    result = detect_required_pages(missing_root, frozenset({FrameworkKind.NEXTJS}))
    assert result.is_err
    assert result.err == ComplyScanError.ROOT_NOT_READABLE
