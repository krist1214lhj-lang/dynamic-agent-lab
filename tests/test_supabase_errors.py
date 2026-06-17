"""G3: Supabase 레이어 예외처리 표준화.

연결 오류(RequestException)는 502로, PostgREST 에러 응답은 무음 {} 대신
실제 상태코드로 표면화되어야 한다. 읽기는 연결 오류만 502로 올린다.
"""

import pytest
import requests as rq
from fastapi import HTTPException

import main


def _table():
    return main.SupabaseClient("http://example.test", "key").table("comments")


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


# --- insert ---
def test_insert_raises_502_on_connection_error(monkeypatch):
    monkeypatch.setattr(main.requests, "post", _boom)
    with pytest.raises(HTTPException) as exc:
        _table().insert({"content": "hi"})
    assert exc.value.status_code == 502


def test_insert_surfaces_postgrest_error_not_silent(monkeypatch):
    monkeypatch.setattr(main.requests, "post", lambda *a, **k: _Resp(False, 400, {"message": "bad insert"}))
    with pytest.raises(HTTPException) as exc:
        _table().insert({"content": "hi"})
    assert exc.value.status_code == 400
    assert "bad insert" in str(exc.value.detail)


def test_insert_success_returns_body(monkeypatch):
    monkeypatch.setattr(main.requests, "post", lambda *a, **k: _Resp(True, 201, [{"id": "1"}]))
    assert _table().insert({"content": "hi"}) == [{"id": "1"}]


def test_insert_success_empty_body_returns_status(monkeypatch):
    monkeypatch.setattr(main.requests, "post", lambda *a, **k: _Resp(True, 201, None))
    assert _table().insert({"content": "hi"}) == {"status": "success"}


# --- patch ---
def test_patch_raises_502_on_connection_error(monkeypatch):
    monkeypatch.setattr(main.requests, "patch", _boom)
    with pytest.raises(HTTPException) as exc:
        _table().patch("1", {"title": "x"})
    assert exc.value.status_code == 502


def test_patch_surfaces_postgrest_error(monkeypatch):
    monkeypatch.setattr(main.requests, "patch", lambda *a, **k: _Resp(False, 403, {"message": "forbidden"}))
    with pytest.raises(HTTPException) as exc:
        _table().patch("1", {"title": "x"})
    assert exc.value.status_code == 403


# --- delete ---
def test_delete_raises_502_on_connection_error(monkeypatch):
    monkeypatch.setattr(main.requests, "delete", _boom)
    with pytest.raises(HTTPException) as exc:
        _table().delete("1")
    assert exc.value.status_code == 502


def test_delete_surfaces_postgrest_error(monkeypatch):
    monkeypatch.setattr(main.requests, "delete", lambda *a, **k: _Resp(False, 403, {"message": "forbidden"}))
    with pytest.raises(HTTPException) as exc:
        _table().delete("1")
    assert exc.value.status_code == 403


def test_delete_success_returns_status(monkeypatch):
    monkeypatch.setattr(main.requests, "delete", lambda *a, **k: _Resp(True, 204, None))
    assert _table().delete("1") == {"status": "success"}


# --- reads: connection error still surfaces as 502, content errors stay [] ---
def test_select_all_raises_502_on_connection_error(monkeypatch):
    monkeypatch.setattr(main.requests, "get", _boom)
    with pytest.raises(HTTPException) as exc:
        _table().select_all()
    assert exc.value.status_code == 502
