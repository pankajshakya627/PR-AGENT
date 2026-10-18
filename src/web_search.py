"""Public documentation lookup for PR questions, using anonymous Search MCP."""

import asyncio
import hashlib
import ipaddress
import json
import math
import os
from urllib.parse import urlsplit

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from src.tenant import require_current_tenant_id

MCP_URL = "https://search.parallel.ai/mcp"
USER_AGENT = "PR-Agent (+https://github.com/pankajshakya627/PR-AGENT)"
MAX_CONTEXT_CHARS = 16000


class WebLookupError(ValueError):
    """A safe message that can be returned to the caller without provider details."""


def _public_url(value: str) -> str:
    try:
        if (
            not isinstance(value, str)
            or len(value) > 2048
            or any(c.isspace() for c in value)
        ):
            raise ValueError()
        parsed = urlsplit(value)
        host = (parsed.hostname or "").rstrip(".")
        if (
            parsed.scheme not in ("http", "https")
            or not host
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 80, 443)
        ):
            raise ValueError()
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if (
                "." not in host
                or host.replace(".", "").isdigit()
                or host.endswith((".localhost", ".local", ".internal"))
            ):
                raise ValueError()
        else:
            if not address.is_global:
                raise ValueError()
    except ValueError:
        raise WebLookupError(
            "Use public HTTP(S) documentation URLs without credentials."
        ) from None
    return value


def _text(result) -> str:
    if result.is_error:
        raise WebLookupError("Public web lookup failed; try again later.")
    text = "\n".join(block.text for block in result.content if block.type == "text")
    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        raise WebLookupError(
            "Public web lookup returned no readable sources."
        ) from None
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise WebLookupError("Public web lookup returned no readable sources.")
    # Fetch can report page failures inside an otherwise successful MCP result.
    # Do not pass provider diagnostics to the model as if they were sources.
    if payload.get("errors"):
        raise WebLookupError(
            "Public web lookup could not retrieve the requested sources."
        )
    sources = []
    for item in payload["results"]:
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            raise WebLookupError("Public web lookup returned no readable sources.")
        url = _public_url(item["url"])
        excerpts = item.get("excerpts", [])
        if not isinstance(excerpts, list) or any(
            not isinstance(x, str) for x in excerpts
        ):
            raise WebLookupError("Public web lookup returned no readable sources.")
        content = "\n".join(excerpts).strip()
        if content:
            sources.append(f"Source: {url}\n{content}")
    if not sources:
        raise WebLookupError("Public web lookup returned no readable sources.")
    # Reserve space for both search and fetch when both are requested.
    return "\n\n".join(sources)[:7500]


async def documentation_context(context: dict) -> str:
    """Send only explicitly supplied public inputs, never PR contents or questions.

    Parallel is the default for an unconfigured installation. An operator can
    disable all web access, or select the explicit ``none`` provider. No other
    provider is silently substituted when configuration or execution fails.
    """
    query = context.get("public_web_query", "")
    urls = context.get("public_web_urls") or []
    if not query and not urls:
        return ""
    if (
        os.getenv("PR_AGENT_WEB_SEARCH_ENABLED", "true").lower() != "true"
        or context.get("web_search_enabled", True) is not True
    ):
        return "Public web lookup is disabled. No external sources were retrieved."
    provider = os.getenv("PR_AGENT_SEARCH_PROVIDER", "parallel").strip().lower()
    if provider == "none":
        return "Public web lookup is disabled. No external sources were retrieved."
    if provider != "parallel":
        raise WebLookupError(
            "Unsupported PR_AGENT_SEARCH_PROVIDER; use parallel or none."
        )
    if not isinstance(query, str) or len(query) > 1000:
        raise WebLookupError(
            "The public web query must be a string of at most 1000 characters."
        )
    query = query.strip()
    if not isinstance(urls, list) or len(urls) > 5:
        raise WebLookupError("Supply at most five public documentation URLs.")
    urls = [_public_url(url) for url in urls]
    if not query and not urls:
        return ""
    try:
        timeout = float(os.getenv("PR_AGENT_SEARCH_TIMEOUT", "30"))
        if not math.isfinite(timeout) or not 0 < timeout <= 120:
            raise ValueError()
    except ValueError:
        raise WebLookupError(
            "PR_AGENT_SEARCH_TIMEOUT must be greater than 0 and at most 120 seconds."
        ) from None

    # Reuse a private, opaque conversation scope across related search/fetch calls.
    scope = require_current_tenant_id() + "\0" + (context.get("pr_url") or "")
    session_id = hashlib.sha256(scope.encode()).hexdigest()
    transport = StreamableHttpTransport(
        MCP_URL, headers={"User-Agent": USER_AGENT}, auth=None
    )
    parts = []
    try:
        async with asyncio.timeout(timeout):
            async with Client(transport, timeout=timeout) as client:
                available = {tool.name for tool in await client.list_tools()}
                needed = ({"web_search"} if query else set()) | (
                    {"web_fetch"} if urls else set()
                )
                if not needed <= available:
                    raise WebLookupError("Public web lookup tools are unavailable.")
                if query:
                    result = await client.call_tool(
                        "web_search",
                        {
                            "objective": query,
                            "search_queries": [query],
                            "session_id": session_id,
                        },
                    )
                    parts.append("Search sources:\n" + _text(result))
                if urls:
                    result = await client.call_tool(
                        "web_fetch",
                        {
                            "urls": urls,
                            "full_content": False,
                            "session_id": session_id,
                        },
                    )
                    parts.append("Fetched sources:\n" + _text(result))
    except WebLookupError:
        raise
    except TimeoutError:
        raise WebLookupError("Public web lookup timed out; try again later.") from None
    except Exception:  # noqa: BLE001 - provider/transport diagnostics must stay private
        raise WebLookupError("Public web lookup failed; try again later.") from None
    return "\n\n".join(parts)[:MAX_CONTEXT_CHARS]
