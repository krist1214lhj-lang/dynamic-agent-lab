"""인증 엔드포인트가 연결오류(502)를 400으로 삼키지 않는지 + Pydantic v2 정리 확인."""

from pathlib import Path

import pytest
import requests as rq
from fastapi.testclient import TestClient

import main


class _Resp:
    def __init__(self, ok, status_code, json_data=None, text=""):
        self.ok = ok
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("no json body")
        return self._json


def _boom(*args, **kwargs):
    raise rq.exceptions.ConnectionError("supabase unreachable")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "sb", main.SupabaseClient("http://example.test", "key"))
    return TestClient(main.app, raise_server_exceptions=False)


def test_signup_endpoint_502_on_connection_error(client, monkeypatch):
    monkeypatch.setattr(main.requests, "post", _boom)
    r = client.post("/auth/signup", json={"email": "a@b.c", "password": "pw"})
    assert r.status_code == 502


def test_login_endpoint_502_on_connection_error(client, monkeypatch):
    monkeypatch.setattr(main.requests, "post", _boom)
    r = client.post("/auth/login", json={"email": "a@b.c", "password": "pw"})
    assert r.status_code == 502


def test_login_endpoint_400_on_bad_credentials(client, monkeypatch):
    # 자격증명 실패는 연결오류(502)와 구분되어 400으로 유지된다.
    monkeypatch.setattr(main.requests, "post", lambda *a, **k: _Resp(False, 400, {"error_description": "bad creds"}))
    r = client.post("/auth/login", json={"email": "a@b.c", "password": "pw"})
    assert r.status_code == 400


def test_no_pydantic_v1_dict_calls():
    # Pydantic v2: deprecated .dict() 대신 model_dump() 사용.
    src = Path(main.__file__).read_text(encoding="utf-8")
    assert ".dict()" not in src, "use model_dump() instead of deprecated Pydantic .dict()"
