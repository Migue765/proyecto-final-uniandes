import json

import httpx
import pytest

from app.dependencies import DependencyUnavailable, ProfileClient, read_bounded_response
from app.observability import Metrics


class ChunkedStream(httpx.SyncByteStream):
    def __iter__(self):
        yield b"12345678"
        yield b"abcdefgh"


def test_streamed_profile_response_stops_at_memory_cap() -> None:
    response = httpx.Response(200, stream=ChunkedStream())

    try:
        with pytest.raises(DependencyUnavailable):
            read_bounded_response(response, maximum_bytes=10)
    finally:
        response.close()


def test_declared_profile_response_over_cap_is_rejected_before_read() -> None:
    response = httpx.Response(
        200,
        headers={"content-length": "16385"},
        stream=httpx.ByteStream(b""),
    )

    try:
        with pytest.raises(DependencyUnavailable):
            read_bounded_response(response, maximum_bytes=16_384)
    finally:
        response.close()


def test_compressed_profile_response_is_rejected() -> None:
    response = httpx.Response(
        200,
        headers={"content-encoding": "gzip"},
        stream=httpx.ByteStream(b"compressed"),
    )

    try:
        with pytest.raises(DependencyUnavailable):
            read_bounded_response(response, maximum_bytes=16_384)
    finally:
        response.close()


def test_profile_client_requests_uncompressed_stream() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["accept-encoding"] == "identity"
        body = json.dumps(
            {
                "partner_ref": "partner-01",
                "profile_ref": "profile-00000000-0000-4000-8000-000000000101",
                "risk_score": 420,
                "risk_band": "MEDIUM",
                "cache_status": "hit",
                "profile_version": "synthetic-v1",
            }
        ).encode("utf-8")
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            stream=httpx.ByteStream(body),
        )

    profile_client = ProfileClient.__new__(ProfileClient)
    profile_client._client = httpx.Client(  # noqa: SLF001
        base_url="http://profile-service:8080",
        transport=httpx.MockTransport(handler),
    )
    profile_client._metrics = Metrics()  # noqa: SLF001

    try:
        result = profile_client.get_score(
            partner_ref="partner-01",
            profile_ref="profile-00000000-0000-4000-8000-000000000101",
        )
    finally:
        profile_client.close()

    assert result.risk_score == 420
