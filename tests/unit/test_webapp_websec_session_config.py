"""frob.webapp._websec_session_config coverage: one compliant/violating
fixture pair per framework (T-5349), plus the unsupported-framework and
missing-config-file negative controls.

frob:ticket T-5349
"""

from __future__ import annotations

from pathlib import Path

from frob.webapp import FrameworkKind
from frob.webapp._websec_session_config import (
    SessionConfigError,
    read_session_config,
)

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "websec2xx"
)


# frob:tests src/frob/webapp/_websec_session_config.py::read_session_config kind="unit"
# frob:tests src/frob/webapp/_websec_session_config.py::SessionConfig kind="unit"
def test_django_compliant_reads_secure_posture():
    """MUST-FIRE: the compliant Django fixture reads secure=True/httponly=True,
    a samesite value, and CSRF middleware present."""
    result = read_session_config(
        _FIXTURE_ROOT / "django_compliant", FrameworkKind.DJANGO
    )
    assert result.is_ok
    config = result.danger_ok
    assert config.framework == FrameworkKind.DJANGO
    assert config.secure is True
    assert config.httponly is True
    assert config.samesite == "Strict"
    assert config.csrf_middleware_present is True
    assert config.absolute_timeout == 1800


# frob:waive DUP002 reason="T-5349: the four *_violating_reads_insecure_posture tests \
# are deliberately near-identical (one negative-control fixture per framework, \
# asserting the same secure=False/httponly=False/csrf_middleware_present=False shape) \
# -- the positive/negative control pair convention this ticket's brief requires, not \
# accidental duplication; extracting a shared assert helper would hide which framework \
# a failing assertion belongs to."
# frob:tests src/frob/webapp/_websec_session_config.py::read_session_config kind="unit"
def test_django_violating_reads_insecure_posture():
    """The violating Django fixture reads secure=False/httponly=False and no
    CSRF middleware in MIDDLEWARE -- the negative control for the compliant case."""
    result = read_session_config(
        _FIXTURE_ROOT / "django_violating", FrameworkKind.DJANGO
    )
    assert result.is_ok
    config = result.danger_ok
    assert config.secure is False
    assert config.httponly is False
    assert config.csrf_middleware_present is False


# frob:tests src/frob/webapp/_websec_session_config.py::read_session_config kind="unit"
def test_flask_compliant_reads_secure_posture():
    """MUST-FIRE: the compliant Flask fixture reads secure cookie flags and
    CSRFProtect wiring."""
    result = read_session_config(_FIXTURE_ROOT / "flask_compliant", FrameworkKind.FLASK)
    assert result.is_ok
    config = result.danger_ok
    assert config.secure is True
    assert config.httponly is True
    assert config.samesite == "Lax"
    assert config.csrf_middleware_present is True
    assert config.idle_timeout == 900


# frob:waive DUP002 reason="T-5349: see test_django_violating_reads_insecure_posture's \
# own DUP002 waiver above -- same deliberate negative-control-per-framework shape."
# frob:tests src/frob/webapp/_websec_session_config.py::read_session_config kind="unit"
def test_flask_violating_reads_insecure_posture():
    """The violating Flask fixture has no CSRFProtect call and insecure cookie flags."""
    result = read_session_config(_FIXTURE_ROOT / "flask_violating", FrameworkKind.FLASK)
    assert result.is_ok
    config = result.danger_ok
    assert config.secure is False
    assert config.httponly is False
    assert config.csrf_middleware_present is False


# frob:tests src/frob/webapp/_websec_session_config.py::read_session_config kind="unit"
def test_express_compliant_reads_secure_posture():
    """MUST-FIRE: the compliant Express fixture reads the session() cookie
    object's secure/httpOnly/sameSite/maxAge and a csurf() call."""
    result = read_session_config(
        _FIXTURE_ROOT / "express_compliant", FrameworkKind.VITE
    )
    assert result.is_ok
    config = result.danger_ok
    assert config.secure is True
    assert config.httponly is True
    assert config.samesite == "strict"
    assert config.csrf_middleware_present is True
    assert config.idle_timeout == 1800000


# frob:waive DUP002 reason="T-5349: see test_django_violating_reads_insecure_posture's \
# own DUP002 waiver above -- same deliberate negative-control-per-framework shape."
# frob:tests src/frob/webapp/_websec_session_config.py::read_session_config kind="unit"
def test_express_violating_reads_insecure_posture():
    """The violating Express fixture has no csurf()/csrf() call and insecure cookie flags."""
    result = read_session_config(
        _FIXTURE_ROOT / "express_violating", FrameworkKind.VITE
    )
    assert result.is_ok
    config = result.danger_ok
    assert config.secure is False
    assert config.httponly is False
    assert config.csrf_middleware_present is False


# frob:tests src/frob/webapp/_websec_session_config.py::read_session_config kind="unit"
def test_rails_compliant_reads_secure_posture():
    """MUST-FIRE: the compliant Rails fixture reads session_store's secure/httponly/
    same_site/expire_after keyword arguments and a protect_from_forgery call."""
    result = read_session_config(_FIXTURE_ROOT / "rails_compliant", FrameworkKind.RAILS)
    assert result.is_ok
    config = result.danger_ok
    assert config.secure is True
    assert config.httponly is True
    assert config.samesite == "strict"
    assert config.csrf_middleware_present is True
    assert config.idle_timeout == 1800


# frob:tests src/frob/webapp/_websec_session_config.py::read_session_config kind="unit"
def test_rails_violating_reads_insecure_posture():
    """The violating Rails fixture has no protect_from_forgery call and insecure
    session_store keyword arguments."""
    result = read_session_config(_FIXTURE_ROOT / "rails_violating", FrameworkKind.RAILS)
    assert result.is_ok
    config = result.danger_ok
    assert config.secure is False
    assert config.httponly is False
    assert config.csrf_middleware_present is False


# frob:tests src/frob/webapp/_websec_session_config.py::read_session_config kind="unit"
# frob:tests src/frob/webapp/_websec_session_config.py::SessionConfigError kind="unit"
def test_missing_config_file_is_err(tmp_path: Path):
    """A root with no settings.py at all returns Err(ConfigFileNotFound), not a crash."""
    result = read_session_config(tmp_path, FrameworkKind.DJANGO)
    assert result.is_err
    assert result.danger_err == SessionConfigError.ConfigFileNotFound


# frob:tests src/frob/webapp/_websec_session_config.py::read_session_config kind="unit"
def test_unsupported_framework_is_err():
    """A FrameworkKind with no registered reader (FastAPI has no single
    canonical session-config file) returns Err(UnsupportedFramework)."""
    result = read_session_config(
        _FIXTURE_ROOT / "django_compliant", FrameworkKind.FASTAPI
    )
    assert result.is_err
    assert result.danger_err == SessionConfigError.UnsupportedFramework
