from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.modules.p3_gestion_simulacion.routes.session_websocket import _identity_still_active


@pytest.mark.parametrize("row,allowed", [(None, False), ((False, 3), False),
    ((True, 4), False), ((True, 3), True)])
def test_live_identity_checks_database_columns_not_cached_user(row, allowed):
    db = Mock()
    db.execute.return_value.first.return_value = row
    user = SimpleNamespace(id="user", auth_version=3, is_active=True)
    assert _identity_still_active(db, user) == allowed
    db.commit.assert_called_once()
