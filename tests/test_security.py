from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from pybotx_smartapp_rpc.fastapi_utils.security import RPCAuth


@pytest.mark.asyncio
async def test_rpcauth_with_full_header_parses_values(request_factory):
    # Arrange
    default_bot_id = uuid4()  # shouldn't be used when provided in header
    ra = RPCAuth(bot_id=default_bot_id)

    bot_id = uuid4()
    sender_huid = uuid4()
    sender_udid = uuid4()
    chat_id = uuid4()

    header_value = (
        f"bot_id={bot_id}&sender_huid={sender_huid}"
        f"&sender_udid={sender_udid}&chat_id={chat_id}"
    )
    req = request_factory({"X-RPC-AUTH": header_value})

    # Act
    cfg = await ra(req)

    # Assert
    assert cfg.bot_id == bot_id
    assert cfg.sender_huid == sender_huid
    assert cfg.sender_udid == sender_udid
    assert cfg.chat_id == chat_id


@pytest.mark.asyncio
async def test_rpcauth_with_invalid_format_raises_403(request_factory):
    # Arrange
    ra = RPCAuth(bot_id=uuid4())
    # Invalid format: no key=value pairs
    req = request_factory({"X-RPC-AUTH": "not-a-key-value-pair"})

    # Act / Assert
    with pytest.raises(HTTPException) as ei:
        await ra(req)

    exc = ei.value
    assert exc.status_code == HTTP_403_FORBIDDEN
    assert exc.detail == "Invalid RPC Auth format"


@pytest.mark.asyncio
async def test_rpcauth_with_invalid_uuid_values_raises_403(request_factory):
    # Arrange
    ra = RPCAuth(bot_id=uuid4())

    # bot_id invalid UUID
    req = request_factory({"X-RPC-AUTH": "bot_id=not-a-uuid"})

    # Act / Assert
    with pytest.raises(HTTPException) as ei:
        await ra(req)

    exc = ei.value
    assert exc.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_rpcauth_header_without_bot_id_uses_default_from_constructor(
    request_factory,
):
    # This test documents the intended behavior that if the header is present but
    # bot_id is not specified,
    # the RPCAuth should fall back to the configured default bot_id.

    # Arrange
    default_bot_id = uuid4()
    ra = RPCAuth(bot_id=default_bot_id)

    sender_huid = uuid4()
    header_value = f"sender_huid={sender_huid}"
    req = request_factory({"X-RPC-AUTH": header_value})

    # Act
    cfg = await ra(req)

    # Assert
    assert cfg.bot_id == default_bot_id  # expected fallback
    assert cfg.sender_huid == sender_huid
    # Others should be auto-filled UUIDs
    assert isinstance(cfg.sender_udid, UUID)
    assert isinstance(cfg.chat_id, UUID)


@pytest.mark.asyncio
async def test_rpcauth_with_empty_bot_id_in_header_raises_400(request_factory):
    ra = RPCAuth(bot_id=uuid4())
    # bot_id is present but empty -> should NOT fallback, should raise 400
    req = request_factory(
        {"X-RPC-AUTH": "bot_id=&sender_huid=00000000-0000-0000-0000-000000000000"}
    )

    with pytest.raises(HTTPException) as ei:
        await ra(req)

    exc = ei.value
    assert exc.status_code == HTTP_400_BAD_REQUEST
