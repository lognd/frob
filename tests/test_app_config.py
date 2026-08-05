"""Direct-call coverage for `frob.app.config.AppConfig`'s enum-field
validators (T-1271): every enum-valued CLI flag whose value flows through
`AppConfig` must reject an invalid value with every legal value listed
inline, not a bare `'x' is not a valid TicketState`-shaped `ValueError`
raised downstream with no indication of what would have been valid
(the ticket's acceptance criterion 0, mined from real `frob ticket list
--status open` usage).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from frob.app.config import AppConfig


class TestEnumFieldValidation:
    def test_invalid_ticket_state_lists_valid_values(self) -> None:
        # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_state_lists_valid_values  # noqa: E501
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(ticket_state="open")
        message = str(exc_info.value)
        assert "'open' is not a valid ticket state" in message
        for valid in ("queued", "planned", "in-progress", "blocked", "done", "dropped"):
            assert valid in message

    def test_valid_ticket_state_passes_through(self) -> None:
        # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_valid_ticket_state_passes_through  # noqa: E501
        cfg = AppConfig(ticket_state="queued")
        assert cfg.ticket_state == "queued"

    def test_none_ticket_state_passes_through(self) -> None:
        # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_none_ticket_state_passes_through  # noqa: E501
        cfg = AppConfig()
        assert cfg.ticket_state is None

    def test_invalid_ticket_kind_lists_valid_values(self) -> None:
        # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_kind_lists_valid_values  # noqa: E501
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(ticket_kind="nope")
        message = str(exc_info.value)
        assert "'nope' is not a valid ticket kind" in message
        assert "feature" in message and "bug" in message

    def test_invalid_ticket_kind_value_lists_valid_values(self) -> None:
        # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_kind_value_lists_valid_values  # noqa: E501
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(ticket_kind_value="nope")
        assert "is not a valid ticket kind" in str(exc_info.value)

    def test_invalid_ticket_tier_lists_valid_values(self) -> None:
        # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_tier_lists_valid_values  # noqa: E501
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(ticket_tier="nope")
        message = str(exc_info.value)
        assert "is not a valid ticket tier" in message
        assert "epic" in message and "story" in message and "ticket" in message

    def test_invalid_ticket_tier_value_lists_valid_values(self) -> None:
        # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_tier_value_lists_valid_values  # noqa: E501
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(ticket_tier_value="nope")
        assert "is not a valid ticket tier" in str(exc_info.value)

    def test_invalid_ticket_priority_level_lists_valid_values(self) -> None:
        # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_priority_level_lists_valid_values  # noqa: E501
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(ticket_priority_level="urgent")
        message = str(exc_info.value)
        assert "is not a valid ticket priority" in message
        assert "low" in message and "medium" in message and "high" in message
        assert "critical" in message

    def test_invalid_ticket_origin_lists_valid_values(self) -> None:
        # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_origin_lists_valid_values  # noqa: E501
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(ticket_origin="robot")
        message = str(exc_info.value)
        assert "is not a valid ticket origin" in message
        assert "human" in message and "agent" in message

    def test_invalid_ticket_review_verdict_lists_valid_values(self) -> None:
        # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_review_verdict_lists_valid_values  # noqa: E501
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(ticket_review_verdict="maybe")
        assert "is not a valid ticket review verdict" in str(exc_info.value)
