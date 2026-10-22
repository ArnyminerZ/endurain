import uuid
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import core.exceptions as core_exceptions
import core.router as core_router
import modules.live_tracking.share_token as share_token


def test_share_link_is_served_the_app_not_treated_as_a_static_file():
    """A dotted last segment is answered as a file lookup and 404s; the viewer link must not have one."""
    app = FastAPI()
    app.include_router(core_router.router)
    core_exceptions.register_exception_handlers(app)
    token = share_token.build_token(str(uuid.uuid4()), "unit-secret")

    with patch.object(core_router.core_utils, "return_frontend_index", return_value=None) as lookup:
        response = TestClient(app).get(f"/live/{token}")

    # The app index is requested (and is missing in the test environment); a static-file
    # lookup of the token itself would have been asked for ``/live/<token>`` instead.
    lookup.assert_called_once_with("index.html")
    assert response.status_code == 404
