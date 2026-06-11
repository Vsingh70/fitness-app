from httpx import AsyncClient


async def test_health_ok(client: AsyncClient) -> None:
    response = await client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert isinstance(body["version"], str)


async def test_health_returns_request_id_header(client: AsyncClient) -> None:
    response = await client.get("/v1/health")
    assert "x-request-id" in {k.lower() for k in response.headers}


async def test_openapi_contains_health(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "/v1/health" in spec["paths"]


async def test_unknown_route_uses_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert isinstance(body["error"]["message"], str)
