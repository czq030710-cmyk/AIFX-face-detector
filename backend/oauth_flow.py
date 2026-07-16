from __future__ import annotations

from dataclasses import dataclass
import secrets
from threading import Lock
import time
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


@dataclass(frozen=True)
class PendingOAuthFlow:
    client: Any
    app_redirect: str
    expires_at: float


@dataclass(frozen=True)
class PendingOAuthTicket:
    auth_payload: dict[str, Any]
    expires_at: float


class OAuthFlowStore:
    def __init__(
        self,
        *,
        flow_ttl_seconds: int = 600,
        ticket_ttl_seconds: int = 120,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.flow_ttl_seconds = flow_ttl_seconds
        self.ticket_ttl_seconds = ticket_ttl_seconds
        self.clock = clock
        self._flows: dict[str, PendingOAuthFlow] = {}
        self._tickets: dict[str, PendingOAuthTicket] = {}
        self._lock = Lock()

    def new_state(self) -> str:
        return secrets.token_urlsafe(32)

    def save_flow(self, state: str, client: Any, app_redirect: str) -> None:
        with self._lock:
            self._prune_locked()
            self._flows[state] = PendingOAuthFlow(
                client=client,
                app_redirect=app_redirect,
                expires_at=self.clock() + self.flow_ttl_seconds,
            )

    def consume_flow(self, state: str) -> PendingOAuthFlow | None:
        with self._lock:
            self._prune_locked()
            return self._flows.pop(state, None)

    def issue_ticket(self, auth_payload: dict[str, Any]) -> str:
        ticket = secrets.token_urlsafe(32)
        with self._lock:
            self._prune_locked()
            self._tickets[ticket] = PendingOAuthTicket(
                auth_payload=auth_payload,
                expires_at=self.clock() + self.ticket_ttl_seconds,
            )
        return ticket

    def consume_ticket(self, ticket: str) -> dict[str, Any] | None:
        with self._lock:
            self._prune_locked()
            pending = self._tickets.pop(ticket, None)
        return pending.auth_payload if pending else None

    def _prune_locked(self) -> None:
        now = self.clock()
        self._flows = {
            key: value
            for key, value in self._flows.items()
            if value.expires_at > now
        }
        self._tickets = {
            key: value
            for key, value in self._tickets.items()
            if value.expires_at > now
        }


def validate_app_redirect(candidate: str, allowed_redirects: list[str]) -> str:
    normalized_candidate = _normalize_redirect(candidate)
    normalized_allowed = {_normalize_redirect(value) for value in allowed_redirects if value.strip()}
    if normalized_candidate not in normalized_allowed:
        raise ValueError("OAuth app redirect is not allowed.")
    return normalized_candidate


def append_query_params(url: str, **params: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update(params)
    return urlunparse(parsed._replace(query=urlencode(query)))


def _normalize_redirect(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("OAuth app redirect must be an absolute HTTP(S) URL.")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("OAuth app redirect contains unsupported URL components.")
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", parsed.query, ""))
