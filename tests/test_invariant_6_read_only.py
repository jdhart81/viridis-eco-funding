"""Invariant 6 - Read-only externally: the code only reads public data and writes nothing
to VergeCommon or any other service.

Three layers: (1) static scan of the source for any HTTP client, write verb or request
body; (2) runtime spy on every request the VergeCommon hook issues; (3) the MCP tools
all carry read-only annotations and never write files.
"""

from __future__ import annotations

import ast
import io
import json
import re

import pytest
from conftest import ROOT

from viridis_eco_funding.vergecommon import (
    ReadOnlyVergeCommonClient,
    VergeCommonError,
    fetch_and_bind,
)

SRC = ROOT / "src" / "viridis_eco_funding"


FORBIDDEN_MODULES = {"requests", "httpx", "httpx2", "aiohttp", "urllib3", "http", "socket",
                     "smtplib", "ftplib", "paramiko", "boto3", "botocore", "websockets", "grpc",
                     "subprocess", "asyncssh"}


def test_static_no_write_capable_network_code():
    forbidden = [
        r"method\s*=\s*['\"](?:POST|PUT|PATCH|DELETE)['\"]",
        r"\.(?:post|put|patch|delete)\s*\(",
    ]
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            match = re.search(pattern, text)
            assert not match, f"{path.name}: {match.group(0)!r}"
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                roots = {node.module.split(".")[0]}
            else:
                continue
            assert not roots & FORBIDDEN_MODULES, f"{path.name} imports {roots & FORBIDDEN_MODULES}"


def test_static_only_vergecommon_module_opens_urls_and_never_with_a_body():
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "attr", getattr(node.func, "id", ""))
                if name in {"urlopen", "Request", "build_opener"}:
                    assert path.name == "vergecommon.py", f"{path.name} calls {name}"
                    keywords = {kw.arg: kw.value for kw in node.keywords}
                    if name == "Request":
                        assert isinstance(keywords.get("method"), ast.Constant)
                        assert keywords["method"].value == "GET"
                        assert isinstance(keywords.get("data"), ast.Constant)
                        assert keywords["data"].value is None
                        assert len(node.args) == 1  # url only; no positional body


def test_static_no_file_writes_in_source():
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in (r"open\([^)]*['\"][wax]\+?b?['\"]", r"\.write_text\(", r"\.write_bytes\(",
                        r"\bos\.remove\b", r"\bshutil\b"):
            assert not re.search(pattern, text), f"{path.name}: {pattern}"


class _Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Spy:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append(request)
        if "id=" in request.full_url:
            return _Response(self.payload)
        return _Response(b'{"coops": []}')


def test_runtime_every_request_is_a_bodiless_https_get(synthetic_record, woodland_site):
    spy = Spy(synthetic_record)
    client = ReadOnlyVergeCommonClient(opener=spy)
    source = fetch_and_bind(woodland_site, client)
    client.list_public_coops(5)
    assert len(spy.requests) == 2
    for request in spy.requests:
        assert request.get_method() == "GET"
        assert request.data is None
        assert request.full_url.startswith("https://vergecommon.com/api/network?")
        headers = {k.lower() for k in request.headers}
        assert "authorization" not in headers and "cookie" not in headers
    assert source["project_kind"] == "woodland"


def test_runtime_rejects_non_allowlisted_hosts_and_plain_http():
    with pytest.raises(VergeCommonError, match="allowlist"):
        ReadOnlyVergeCommonClient(base_url="https://evil.example")
    with pytest.raises(VergeCommonError, match="https"):
        ReadOnlyVergeCommonClient(base_url="http://vergecommon.com")


def test_global_urlopen_never_called_with_write_methods(monkeypatch, synthetic_record, woodland_site):
    """Even through the default opener path, only GET reaches urllib."""
    import urllib.request

    seen = []

    def fake_urlopen(request, timeout=None):
        seen.append((request.get_method(), request.data))
        return _Response(json.dumps(synthetic_record).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    fetch_and_bind(woodland_site, ReadOnlyVergeCommonClient())
    assert seen == [("GET", None)]


def test_mcp_tools_are_annotated_read_only():
    pytest.importorskip("mcp")
    import asyncio

    from viridis_eco_funding.mcp_server import build_server

    tools = asyncio.run(build_server().list_tools())
    assert len(tools) == 5
    for tool in tools:
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False
        assert tool.annotations.idempotent_hint is True
