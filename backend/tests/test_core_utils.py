from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app.core.utils import resolve_owner_uid
from fastapi import HTTPException


def test_resolve_owner_uid_prefers_uid_from_token():
    assert resolve_owner_uid({"uid": 123}) == "123"


def test_resolve_owner_uid_returns_none_when_auth_disabled():
    with patch(
        "app.core.utils.get_settings",
        return_value=SimpleNamespace(firebase_auth_enabled=False),
    ):
        assert resolve_owner_uid(None) is None


def test_resolve_owner_uid_raises_when_auth_enabled_and_uid_missing():
    with patch(
        "app.core.utils.get_settings",
        return_value=SimpleNamespace(firebase_auth_enabled=True),
    ):
        with pytest.raises(HTTPException) as exc:
            resolve_owner_uid({})
    assert exc.value.status_code == 401
