from __future__ import annotations

import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from .config import Settings
from .service import (
    ConflictError,
    InputError,
    NotFoundError,
    PathLexService,
    PlayerError,
)


UNIT_RE = re.compile(r"^/api/units/([0-9a-f]{32})$")
PUBLISH_RE = re.compile(r"^/api/units/([0-9a-f]{32})/publish$")
REPAIR_RE = re.compile(r"^/api/units/([0-9a-f]{32})/repair$")
SESSION_RE = re.compile(r"^/api/sessions/([0-9a-f]{32})$")
ANSWER_RE = re.compile(r"^/api/sessions/([0-9a-f]{32})/answer$")
CHOOSE_RE = re.compile(r"^/api/sessions/([0-9a-f]{32})/choose$")
COMPLETE_RE = re.compile(r"^/api/sessions/([0-9a-f]{32})/complete$")
LANGUAGE_RE = re.compile(r"^/api/sessions/([0-9a-f]{32})/language$")


class PathLexHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], service: PathLexService):
        super().__init__(address, PathLexHandler)
        self.service = service
        self.settings = service.settings


class PathLexHandler(BaseHTTPRequestHandler):
    server: PathLexHTTPServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format_string: str, *args: Any) -> None:

        super().log_message(format_string, *args)

    @property
    def path_only(self) -> str:
        return unquote(urlsplit(self.path).path)

    def _headers(self, content_type: str, content_length: int, *, cache: str = "no-store") -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )

    def _json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self._headers("application/json; charset=utf-8", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _error(
        self, status: int, code: str, message: str, details: list[str] | None = None
    ) -> None:
        payload: dict[str, Any] = {"error": {"code": code, "message": message}}
        if details:
            payload["error"]["details"] = details
        self._json(status, payload)

    def _read_json(self) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
        if content_type != "application/json":
            raise InputError("Use Content-Type: application/json")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise InputError("Content-Length must be an integer") from exc
        if length <= 0:
            raise InputError("The request body is empty")
        if length > self.server.settings.max_request_bytes:
            raise InputError("The request body exceeds the configured size limit")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InputError("The request body is not valid UTF-8 JSON") from exc
        if not isinstance(payload, dict):
            raise InputError("The request body must be a JSON object")
        return payload

    def do_GET(self) -> None:
        try:
            self._get()
        except Exception as exc:
            self._handle_exception(exc)

    def _get(self) -> None:
        path = self.path_only
        if path == "/api/health":
            self._json(HTTPStatus.OK, self.server.service.health())
            return
        if path == "/api/units":
            self._json(HTTPStatus.OK, {"items": self.server.service.list_units()})
            return
        if match := UNIT_RE.match(path):
            self._json(HTTPStatus.OK, self.server.service.get_unit(match.group(1)))
            return
        if path == "/api/library":
            self._json(HTTPStatus.OK, {"items": self.server.service.library()})
            return
        if match := SESSION_RE.match(path):
            self._json(HTTPStatus.OK, self.server.service.get_session(match.group(1)))
            return
        if path == "/" or path == "/index.html":
            self._static("index.html", cache="no-cache")
            return
        if path.startswith("/static/"):
            self._static(path[len("/static/") :], cache="public, max-age=300")
            return
        self._error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "The requested route does not exist")

    def do_POST(self) -> None:
        try:
            self._post()
        except Exception as exc:
            self._handle_exception(exc)

    def _post(self) -> None:
        path = self.path_only
        payload = self._read_json()
        if path == "/api/units":
            unit = self.server.service.create_unit(payload, background=True)
            self._json(HTTPStatus.ACCEPTED, unit)
            return
        if match := PUBLISH_RE.match(path):
            self._json(HTTPStatus.OK, self.server.service.publish_unit(match.group(1)))
            return
        if match := REPAIR_RE.match(path):
            self._json(HTTPStatus.OK, self.server.service.repair_unit(match.group(1)))
            return
        if path == "/api/sessions":
            unit_id = str(payload.get("unit_id") or "")
            if not unit_id:
                raise InputError("unit_id is required")
            language = "zh" if (
                payload.get("language") == "zh"
                or payload.get("interface_language") == "zh"
            ) else "en"
            self._json(
                HTTPStatus.CREATED, self.server.service.start_session(unit_id, language)
            )
            return
        if match := ANSWER_RE.match(path):
            self._json(
                HTTPStatus.OK,
                self.server.service.answer(match.group(1), str(payload.get("answer") or "")),
            )
            return
        if match := CHOOSE_RE.match(path):
            choice_id = str(payload.get("choice_id") or "")
            if not choice_id:
                raise InputError("choice_id is required")
            self._json(
                HTTPStatus.OK, self.server.service.choose(match.group(1), choice_id)
            )
            return
        if match := COMPLETE_RE.match(path):
            self._json(
                HTTPStatus.OK,
                self.server.service.complete_session(match.group(1)),
            )
            return
        if match := LANGUAGE_RE.match(path):
            language = "zh" if payload.get("interface_language") == "zh" else "en"
            self._json(
                HTTPStatus.OK,
                self.server.service.set_session_language(match.group(1), language),
            )
            return
        self._error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "The requested route does not exist")

    def _static(self, relative_name: str, *, cache: str) -> None:
        static_root = self.server.settings.static_path.resolve()
        candidate = (static_root / relative_name).resolve()
        if not candidate.is_relative_to(static_root) or not candidate.is_file():
            self._error(HTTPStatus.NOT_FOUND, "ASSET_NOT_FOUND", "Static asset not found")
            return
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {
            "application/javascript",
            "application/json",
        }:
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self._headers(content_type, len(body), cache=cache)
        self.end_headers()
        self.wfile.write(body)

    def _handle_exception(self, exc: Exception) -> None:
        if isinstance(exc, InputError):
            self._error(HTTPStatus.BAD_REQUEST, "INVALID_INPUT", str(exc), exc.details)
        elif isinstance(exc, PlayerError):
            self._error(HTTPStatus.BAD_REQUEST, "PLAYER_ERROR", str(exc))
        elif isinstance(exc, NotFoundError):
            self._error(HTTPStatus.NOT_FOUND, "NOT_FOUND", str(exc))
        elif isinstance(exc, ConflictError):
            self._error(HTTPStatus.CONFLICT, "CONFLICT", str(exc))
        elif isinstance(exc, ValueError):
            self._error(HTTPStatus.BAD_REQUEST, "INVALID_INPUT", str(exc))
        else:

            self._error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "INTERNAL_ERROR",
                "The server could not complete this request. Check the server log.",
            )


def serve(settings: Settings | None = None, service: PathLexService | None = None) -> None:
    runtime_settings = settings or Settings.from_env()
    runtime_service = service or PathLexService(runtime_settings)
    server = PathLexHTTPServer((runtime_settings.host, runtime_settings.port), runtime_service)
    print(f"PathLex listening on http://{runtime_settings.host}:{runtime_settings.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        runtime_service.close()


__all__ = ["PathLexHTTPServer", "PathLexHandler", "serve"]

