"""MCP handlers for the token-efficient agent tools.

Handlers return compact text rendered by :mod:`openardp.interfaces.agent_render`.
Reference and range problems become :class:`AgentToolError` with a short corrective
hint, which the server returns as an ``isError`` tool result so the model can retry.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Mapping
from typing import Any

from pydantic import JsonValue

from openardp.interfaces.agent_render import (
    render_docs,
    render_find,
    render_outline,
    render_read,
    render_verify,
)
from openardp.interfaces.mcp_protocol import McpErrorCategory, RequestDeadline
from openardp.ports.agent import (
    AgentDocumentAmbiguous,
    AgentDocumentNotFound,
    AgentRangeInvalid,
    AgentRenderUnavailable,
)
from openardp.ports.context import CancellationCheck
from openardp.services.agent_access import (
    DEFAULT_FIND_LIMIT,
    DEFAULT_READ_TOKENS,
    AgentAccessService,
)

AgentHandler = Callable[[dict[str, JsonValue], RequestDeadline, CancellationCheck], str]
_LOGGER = logging.getLogger("openardp.mcp")


class AgentToolError(Exception):
    """A correctable tool failure with a category and a short, safe explanation."""

    def __init__(self, category: McpErrorCategory, detail: str) -> None:
        """Keep the documented category and the model-facing correction hint."""
        super().__init__(detail)
        self.category = category
        self.detail = detail


class AgentWarmup:
    """Prepare the disposable agent index in the background once per server session."""

    def __init__(self, access: AgentAccessService) -> None:
        """Bind the service whose index is refreshed."""
        self._access = access
        self._done = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the background refresh; the session keeps answering meanwhile."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="openardp-agent-warmup", daemon=True)
        self._thread.start()

    def wait(self, deadline: RequestDeadline) -> None:
        """Wait for the initial refresh within the request deadline, then report."""
        if self._thread is None:
            return
        if not self._done.wait(timeout=max(0.0, deadline.remaining_ms / 1_000 - 0.5)):
            raise AgentToolError(
                McpErrorCategory.CONFLICT,
                "Documents are still being prepared for agent access; retry in a few seconds.",
            )

    def _run(self) -> None:
        try:
            self._access.refresh()
        except Exception as error:
            # A failed warmup is retried by the next request; log the class only.
            _LOGGER.warning("agent index warmup failed: %s", type(error).__name__)
        finally:
            self._done.set()


class AgentToolHandlers:
    """Bind the five agent tools to one agent access service."""

    def __init__(self, access: AgentAccessService, warmup: AgentWarmup | None = None) -> None:
        """Bind the service and the optional background warmup."""
        self._access = access
        self._warmup = warmup

    def handlers(self) -> dict[str, AgentHandler]:
        """Return the dispatch table for the agent tool names."""
        return {
            "list_documents": self._list_documents,
            "find": self._find,
            "read": self._read,
            "outline": self._outline,
            "verify_quote": self._verify_quote,
        }

    def _list_documents(
        self,
        arguments: dict[str, JsonValue],
        deadline: RequestDeadline,
        cancel: CancellationCheck,
    ) -> str:
        del arguments, cancel
        return self._run(deadline, lambda: render_docs(self._access.documents()))

    def _find(
        self,
        arguments: dict[str, JsonValue],
        deadline: RequestDeadline,
        cancel: CancellationCheck,
    ) -> str:
        del cancel
        return self._run(
            deadline,
            lambda: render_find(
                self._access.find(
                    _text(arguments, "query"),
                    document=_optional_text(arguments, "document"),
                    limit=_optional_int(arguments, "limit") or DEFAULT_FIND_LIMIT,
                )
            ),
        )

    def _read(
        self,
        arguments: dict[str, JsonValue],
        deadline: RequestDeadline,
        cancel: CancellationCheck,
    ) -> str:
        del cancel
        return self._run(
            deadline,
            lambda: render_read(
                self._access.read(
                    _text(arguments, "document"),
                    page=_optional_text(arguments, "page"),
                    lines=_optional_text(arguments, "lines"),
                    section=_optional_text(arguments, "section"),
                    max_tokens=_optional_int(arguments, "max_tokens") or DEFAULT_READ_TOKENS,
                )
            ),
        )

    def _outline(
        self,
        arguments: dict[str, JsonValue],
        deadline: RequestDeadline,
        cancel: CancellationCheck,
    ) -> str:
        del cancel
        return self._run(
            deadline,
            lambda: render_outline(self._access.outline(_text(arguments, "document"))),
        )

    def _verify_quote(
        self,
        arguments: dict[str, JsonValue],
        deadline: RequestDeadline,
        cancel: CancellationCheck,
    ) -> str:
        del cancel
        return self._run(
            deadline,
            lambda: render_verify(
                self._access.verify(
                    _text(arguments, "quote"),
                    document=_optional_text(arguments, "document"),
                    version=_optional_text(arguments, "version"),
                )
            ),
        )

    def _run(self, deadline: RequestDeadline, action: Callable[[], str]) -> str:
        if self._warmup is not None:
            self._warmup.wait(deadline)
        try:
            return action()
        except AgentDocumentAmbiguous as error:
            choices = "; ".join(error.candidates) or "several documents"
            raise AgentToolError(
                McpErrorCategory.CONFLICT,
                f"The document reference matches {choices}. Pass the id instead.",
            ) from error
        except AgentDocumentNotFound as error:
            raise AgentToolError(
                McpErrorCategory.NOT_FOUND,
                "No prepared document matches. Call list_documents for names and ids.",
            ) from error
        except AgentRangeInvalid as error:
            raise AgentToolError(McpErrorCategory.INVALID_PARAMS, f"{error}.") from error
        except AgentRenderUnavailable as error:
            raise AgentToolError(
                McpErrorCategory.INTEGRITY_OR_WORKSPACE,
                "Rendering this document needs the docling extra on the server.",
            ) from error


def _text(arguments: Mapping[str, Any], name: str) -> str:
    value = arguments[name]
    if not isinstance(value, str):
        raise AgentToolError(McpErrorCategory.INVALID_PARAMS, f"{name} must be a string.")
    return value


def _optional_text(arguments: Mapping[str, Any], name: str) -> str | None:
    value = arguments.get(name)
    if value is None:
        return None
    return _text(arguments, name)


def _optional_int(arguments: Mapping[str, Any], name: str) -> int | None:
    value = arguments.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise AgentToolError(McpErrorCategory.INVALID_PARAMS, f"{name} must be an integer.")
    return int(value)


__all__ = ["AgentHandler", "AgentToolError", "AgentToolHandlers", "AgentWarmup"]
