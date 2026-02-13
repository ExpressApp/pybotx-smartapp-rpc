from datetime import datetime, timezone

import pytest
from deepdiff import DeepDiff
from freezegun import freeze_time

from pybotx_smartapp_rpc.exception_handlers import (
    default_exception_handler,
    rpc_exception_handler,
)
from pybotx_smartapp_rpc.exceptions import RPCErrorExc
from pybotx_smartapp_rpc.models.errors import RPCError
from pybotx_smartapp_rpc.models.responses import build_method_not_found_error_response
from tests.factories import RPCRequestFactory


@pytest.mark.parametrize("method_name", ["sum", "notify:user"])
def test_request_factory_with_parametrized_method(method_name: str) -> None:
    request = RPCRequestFactory(method=method_name)

    assert request.method == method_name
    assert request.type == "smartapp_rpc"


def test_method_not_found_payload_deepdiff() -> None:
    payload = build_method_not_found_error_response("missing.method").jsonable_dict()
    expected_payload = {
        "status": "error",
        "type": "smartapp_rpc",
        "errors": [
            {
                "reason": "Method not found",
                "id": "METHOD_NOT_FOUND",
                "meta": {"method": "missing.method"},
            },
        ],
    }

    assert DeepDiff(payload, expected_payload, ignore_order=True) == {}


async def test_default_exception_handler_logs_exception(mocker) -> None:
    logger_mock = mocker.patch("pybotx_smartapp_rpc.exception_handlers.logger")

    response = await default_exception_handler(
        ValueError("boom"),
        smartapp=mocker.MagicMock(),
    )

    logger_mock.exception.assert_called_once()
    assert response.errors[0].id == "VALUEERROR"


async def test_rpc_exception_handler_returns_original_errors(mocker) -> None:
    error = RPCError(reason="Boom", id="BOOM")
    response = await rpc_exception_handler(
        RPCErrorExc(error),
        smartapp=mocker.MagicMock(),
    )

    assert response.errors == [error]


@freeze_time("2026-02-13 15:00:00")
def test_freezegun_is_configured() -> None:
    now_utc = datetime.now(tz=timezone.utc)

    assert now_utc.strftime("%Y-%m-%d %H:%M:%S") == "2026-02-13 15:00:00"
