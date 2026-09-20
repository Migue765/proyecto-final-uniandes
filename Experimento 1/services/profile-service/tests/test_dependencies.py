import json
from decimal import Decimal

import httpx
import pytest

from app.dependencies import (
    DependencyUnavailable,
    ProfileCache,
    WireMockClient,
    read_bounded_response,
)
from app.models import ProfileInputs
from app.observability import Metrics


class ChunkedStream(httpx.SyncByteStream):
    def __iter__(self):
        yield b"12345678"
        yield b"abcdefgh"


def test_cache_key_does_not_expose_synthetic_references() -> None:
    key = ProfileCache.cache_key(
        "partner-01", "profile-00000000-0000-4000-8000-000000000101"
    )

    assert key.startswith("profile:v1:")
    assert "partner-01" not in key
    assert "00000000" not in key


def test_profile_inputs_serialize_for_redis() -> None:
    profile = ProfileInputs(
        age=35,
        monthly_income=Decimal("5000000"),
        debt_ratio=Decimal("0.25"),
        claims_count=1,
        account_age_months=36,
        inflow_stability=Decimal("0.82"),
        delinquency_count=0,
    )

    assert ProfileInputs.model_validate_json(profile.model_dump_json()) == profile


def test_streamed_wiremock_response_stops_at_memory_cap() -> None:
    response = httpx.Response(200, stream=ChunkedStream())

    try:
        with pytest.raises(DependencyUnavailable):
            read_bounded_response(response, maximum_bytes=10)
    finally:
        response.close()


def test_compressed_wiremock_response_is_rejected() -> None:
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


def test_wiremock_client_requests_uncompressed_stream() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["accept-encoding"] == "identity"
        body = json.dumps(
            {
                "account_age_months": 36,
                "inflow_stability": 0.82,
                "delinquency_count": 0,
            }
        ).encode("utf-8")
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            stream=httpx.ByteStream(body),
        )

    wiremock_client = WireMockClient.__new__(WireMockClient)
    wiremock_client._client = httpx.Client(  # noqa: SLF001
        base_url="http://wiremock:8080",
        transport=httpx.MockTransport(handler),
    )
    wiremock_client._metrics = Metrics()  # noqa: SLF001

    try:
        result = wiremock_client.fetch(
            "partner-01",
            "profile-00000000-0000-4000-8000-000000000101",
        )
    finally:
        wiremock_client.close()

    assert result.account_age_months == 36
