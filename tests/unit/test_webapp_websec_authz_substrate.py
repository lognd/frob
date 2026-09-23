"""WEBSEC401 (T-5356): route/handler owner-check heuristic -- positive
and negative control per framework (Flask/FastAPI/Django/Rails).

# frob:ticket T-5356
"""

from __future__ import annotations

from pathlib import Path

from frob.lang import raw_tree
from frob.webapp._websec_authz_substrate import (
    AUTH_IDENTIFIER_NAMES,
    scan_python_handlers,
    scan_rails_controller,
)

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "websec4xx"
)


def _findings(rel: str):
    """`scan_python_handlers`'s findings for a python fixture path under
    `_FIXTURE_ROOT` -- panics (via `.danger_ok`) on a genuine parse
    failure, which would be a fixture bug, not an expected outcome."""
    path = _FIXTURE_ROOT / rel
    tree, source, language = raw_tree(path).danger_ok
    return scan_python_handlers(str(path), tree.root_node, source, language).danger_ok


class TestAuthIdentifierVocabulary:
    """`AUTH_IDENTIFIER_NAMES` is the exact vocabulary T-5356's ticket
    body names -- a change here is a deliberate heuristic change, not an
    accident, so it gets its own assertion."""

    def test_matches_ticket_vocabulary(self) -> None:
        assert AUTH_IDENTIFIER_NAMES == {"current_user", "request.user", "g.user"}


class TestFlask:
    """Flask: `@app.route(...)` decorator, `.filter_by(...)` ORM call."""

    # frob:tests src/frob/webapp/_websec_authz_substrate.py::scan_python_handlers
    def test_owner_filtered_route_is_clean(self) -> None:
        findings = _findings("flask/app.py")
        assert not any(f.handler == "get_order" for f in findings)

    # frob:tests src/frob/webapp/_websec_authz_substrate.py::scan_python_handlers
    # frob:tests src/frob/webapp/_websec_authz_substrate.py::AuthzFinding  # noqa: E501
    def test_unfiltered_route_is_flagged(self) -> None:
        findings = _findings("flask/app.py")
        assert any(f.handler == "get_order_unsafe" for f in findings)


class TestFastAPI:
    """FastAPI: `@app.get(...)` decorator, `.filter(...)` ORM call."""

    # frob:tests src/frob/webapp/_websec_authz_substrate.py::scan_python_handlers
    def test_owner_filtered_handler_is_clean(self) -> None:
        findings = _findings("fastapi/main.py")
        assert not any(f.handler == "get_invoice" for f in findings)

    # frob:tests src/frob/webapp/_websec_authz_substrate.py::scan_python_handlers
    def test_unfiltered_handler_is_flagged(self) -> None:
        findings = _findings("fastapi/main.py")
        assert any(f.handler == "get_invoice_unsafe" for f in findings)


class TestDjango:
    """Django: bare `request` first parameter, `get_object_or_404(...)`."""

    # frob:tests src/frob/webapp/_websec_authz_substrate.py::scan_python_handlers
    def test_owner_filtered_view_is_clean(self) -> None:
        findings = _findings("django/views.py")
        assert not any(f.handler == "get_profile" for f in findings)

    # frob:tests src/frob/webapp/_websec_authz_substrate.py::scan_python_handlers
    def test_unfiltered_view_is_flagged(self) -> None:
        findings = _findings("django/views.py")
        assert any(f.handler == "get_profile_unsafe" for f in findings)


class TestRailsController:
    """Rails: no tree-sitter grammar for `.rb` -- `scan_rails_controller`
    takes raw source text directly (module docstring)."""

    def _text(self) -> str:
        return (_FIXTURE_ROOT / "rails" / "orders_controller.rb").read_text()

    # frob:tests src/frob/webapp/_websec_authz_substrate.py::scan_rails_controller
    def test_owner_filtered_action_is_clean(self) -> None:
        findings = scan_rails_controller("orders_controller.rb", self._text())
        assert not any(f.handler == "show" for f in findings)

    # frob:tests src/frob/webapp/_websec_authz_substrate.py::scan_rails_controller
    def test_unfiltered_action_is_flagged(self) -> None:
        findings = scan_rails_controller("orders_controller.rb", self._text())
        assert any(f.handler == "show_unsafe" for f in findings)

    # frob:tests src/frob/webapp/_websec_authz_substrate.py::scan_rails_controller
    def test_non_controller_file_yields_nothing(self) -> None:
        text = "class Order\n  def show\n    Order.where(id: 1).first\n  end\nend\n"
        assert scan_rails_controller("order.rb", text) == ()


class TestNonHandlerHelpersAreIgnored:
    """A plain helper function (no route decorator, no `request` param)
    reaching an ORM lookup is NOT a handler candidate, even with no auth
    identifier in sight -- the false-positive gate this heuristic relies
    on."""

    # frob:tests src/frob/webapp/_websec_authz_substrate.py::scan_python_handlers
    def test_plain_helper_is_not_flagged(self, tmp_path: Path) -> None:
        src = (
            "def load_by_id(record_id):\n"
            "    return Model.objects.filter(id=record_id).first()\n"
        )
        path = tmp_path / "helpers.py"
        path.write_text(src)
        tree, source, language = raw_tree(path).danger_ok
        findings = scan_python_handlers(
            str(path), tree.root_node, source, language
        ).danger_ok
        assert findings == ()


class TestUnsupportedLanguage:
    """A non-python `language` argument is an `Err`, not a silent empty
    result -- `scan_rails_controller` is the `.rb` entry point instead."""

    # frob:tests src/frob/webapp/_websec_authz_substrate.py::scan_python_handlers
    # frob:tests src/frob/webapp/_websec_authz_substrate.py::AuthzSubstrateError  # noqa: E501
    def test_non_python_language_is_an_error(self, tmp_path: Path) -> None:
        # `language` is checked before `root` is ever touched, so any
        # real Node stands in here -- an arbitrary python parse is the
        # simplest one available without a second grammar.
        path = tmp_path / "app.rb"
        path.write_text("class Foo\nend\n")
        stand_in = tmp_path / "stand_in.py"
        stand_in.write_text("pass\n")
        tree, source, _language = raw_tree(stand_in).danger_ok
        result = scan_python_handlers(str(path), tree.root_node, source, "ruby")
        assert result.is_err
