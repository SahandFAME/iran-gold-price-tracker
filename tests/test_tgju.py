from __future__ import annotations

import httpx

from gold_updater import tgju


def test_current_price_uses_live_geram18_quote_and_converts_rial_to_toman(monkeypatch) -> None:
    requests: list[str] = []
    client_class = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(
            200,
            request=request,
            json={"current": {"geram18": {"p": "256,514,000"}}},
        )

    monkeypatch.setattr(
        tgju.httpx,
        "Client",
        lambda **kwargs: client_class(transport=httpx.MockTransport(handler)),
    )

    assert tgju.fetch_current_tgju_price() == 25_651_400
    assert requests == [tgju.TGJU_LIVE_URLS[0]]


def test_current_price_falls_back_to_next_live_mirror(monkeypatch) -> None:
    requests: list[str] = []
    client_class = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if str(request.url) == tgju.TGJU_LIVE_URLS[0]:
            return httpx.Response(503, request=request)
        return httpx.Response(
            200,
            request=request,
            json={"current": {"geram18": {"p": 256_514_000}}},
        )

    monkeypatch.setattr(
        tgju.httpx,
        "Client",
        lambda **kwargs: client_class(transport=httpx.MockTransport(handler)),
    )

    assert tgju.fetch_current_tgju_price() == 25_651_400
    assert requests == list(tgju.TGJU_LIVE_URLS[:2])
