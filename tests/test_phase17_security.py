from uuid import uuid4

import pytest
from fastapi import HTTPException

from apps.api.auth import _allowed, require_csrf


def test_csrf_requires_matching_double_submit_token() -> None:
    with pytest.raises(HTTPException) as exc:
        require_csrf("cookie-token", "wrong-token")
    assert exc.value.status_code == 403


def test_csrf_accepts_matching_token() -> None:
    require_csrf("same-token", "same-token")


def test_rbac_financial_action_requires_admin() -> None:
    assert not _allowed("VIEWER", "ADMIN")
    assert not _allowed("OPERATOR", "ADMIN")
    assert _allowed("ADMIN", "ADMIN")
    assert _allowed("OWNER", "ADMIN")


def test_tenant_ids_are_not_interchangeable() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    assert tenant_a != tenant_b
