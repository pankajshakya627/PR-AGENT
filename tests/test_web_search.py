"""Exercise MCP dispatch, HTTP requests and PR-question prompt consumption.

Model responses are scripted; these tests do not claim live model reasoning.
"""

import asyncio
import importlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx2 as httpx
import pytest
import pytest_asyncio
from fastmcp import Client, FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from src import tenant, web_search
from src.agents.specialized import BaseLLMAgent, PRQuestionsAgent
from src.analyzer import TaskDependencyAnalyzer

SOURCE = "https://docs.python.org/3/library/asyncio-task.html"
QUERY = "Python asyncio cancellation documentation"


@pytest.fixture
def runtime(monkeypatch):
    for name in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GROQ_API_KEY",
        "NVIDIA_API_KEY",
        "OPENROUTER_API_KEY",
        "PARALLEL_API_KEY",
        "DEFAULT_TENANT_ID",
        "PR_AGENT_SEARCH_PROVIDER",
        "PR_AGENT_WEB_SEARCH_ENABLED",
        "PR_AGENT_SEARCH_TIMEOUT",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LANGFUSE_ENABLED", "false")
    monkeypatch.setenv("ENABLE_CACHING", "true")
    monkeypatch.setattr(tenant, "_tenant_cache", {})
    prompts = []

    async def answer(prompt):
        prompts.append(prompt.to_messages())
        return AIMessage(content=prompt.to_messages()[-1].content)

    model = RunnableLambda(answer)
    monkeypatch.setattr(BaseLLMAgent, "_create_llm", lambda *args: model)
    monkeypatch.setattr(
        BaseLLMAgent, "_get_diff", AsyncMock(return_value="PRIVATE_DIFF")
    )
    monkeypatch.setattr(TaskDependencyAnalyzer, "__init__", lambda self: None)
    main = importlib.import_module("main")
    return SimpleNamespace(server=main.mcp, prompts=prompts)


@pytest_asyncio.fixture
async def mcp_http(monkeypatch):
    remote = FastMCP("search-fixture")
    state = SimpleNamespace(
        requests=[],
        clients=[],
        calls=[],
        error=False,
        text=None,
        payload=None,
        wait=False,
        entered=asyncio.Event(),
        cancelled=asyncio.Event(),
    )

    async def source(name, arguments):
        state.calls.append((name, arguments))
        state.entered.set()
        if state.wait:
            try:
                await asyncio.Event().wait()
            finally:
                state.cancelled.set()
        if state.error:
            raise ValueError("PRIVATE_PROVIDER_DIAGNOSTIC")
        if state.payload is not None:
            return json.dumps(state.payload)
        excerpt = (
            state.text
            if state.text is not None
            else "Documentation excerpt: cancellation uses CancelledError."
        )
        return json.dumps(
            {"results": [{"url": SOURCE, "excerpts": [excerpt]}], "errors": []}
        )

    @remote.tool(name="web_search")
    async def search(objective: str, search_queries: list[str], session_id: str) -> str:
        return await source(
            "web_search",
            {
                "objective": objective,
                "search_queries": search_queries,
                "session_id": session_id,
            },
        )

    @remote.tool(name="web_fetch")
    async def fetch(urls: list[str], full_content: bool, session_id: str) -> str:
        return await source(
            "web_fetch",
            {"urls": urls, "full_content": full_content, "session_id": session_id},
        )

    app = remote.http_app(path="/mcp", json_response=True, stateless_http=True)

    async def record(request):
        state.requests.append(
            {
                "url": str(request.url),
                "headers": dict(request.headers),
                "body": request.content.decode() if request.content else "",
            }
        )

    def factory(**kwargs):
        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            event_hooks={"request": [record]},
            **kwargs,
        )
        state.clients.append(client)
        return client

    def transport(url, **kwargs):
        return StreamableHttpTransport(url, httpx_client_factory=factory, **kwargs)

    monkeypatch.setattr(web_search, "StreamableHttpTransport", transport)
    ready, stop = asyncio.Event(), asyncio.Event()

    async def lifespan():
        # AnyIO cancel scopes must enter and exit in the same task. Pytest's
        # fixture setup/teardown run in separate tasks, so keep lifespan here.
        async with app.router.lifespan_context(app):
            ready.set()
            await stop.wait()

    lifecycle = asyncio.create_task(lifespan())
    await ready.wait()
    try:
        yield state
    finally:
        stop.set()
        await lifecycle


async def ask(runtime, **kwargs):
    arguments = {
        "pr_url": "https://github.com/example/repo/pull/42",
        "question": "PRIVATE_QUESTION",
        "tenant_id": "search-test",
    }
    arguments.update(kwargs)
    async with Client(runtime.server) as client:
        result = await client.call_tool("ask_pr", arguments)
    return "\n".join(block.text for block in result.content if block.type == "text")


@pytest.mark.asyncio
async def test_dispatch_to_http_and_prompt(runtime, mcp_http):
    output = await ask(runtime, public_web_query=QUERY, public_web_urls=[SOURCE])
    assert "Search sources:" in output and "Fetched sources:" in output
    assert SOURCE in output and "CancelledError" in output
    assert "PRIVATE_DIFF" in output and "PRIVATE_QUESTION" in output
    assert [name for name, _ in mcp_http.calls] == ["web_search", "web_fetch"]
    search, fetch = [args for _, args in mcp_http.calls]
    assert search["objective"] == QUERY and search["search_queries"] == [QUERY]
    assert fetch["urls"] == [SOURCE] and fetch["full_content"] is False
    assert search["session_id"] == fetch["session_id"]
    assert len(search["session_id"]) == 64
    assert mcp_http.requests
    for request in mcp_http.requests:
        assert request["url"] == web_search.MCP_URL
        assert request["headers"]["user-agent"] == web_search.USER_AGENT
        assert "authorization" not in request["headers"]
        assert "PRIVATE_DIFF" not in request["body"]
        assert "PRIVATE_QUESTION" not in request["body"]
        assert "search-test" not in request["body"]
    assert any(
        "tools/list" in r["body"] or "discovery" in r["body"] for r in mcp_http.requests
    )
    assert "untrusted reference material" in runtime.prompts[-1][0].content
    assert SOURCE in runtime.prompts[-1][-1].content


@pytest.mark.asyncio
async def test_inbound_http_credentials_are_not_forwarded(runtime, mcp_http):
    app = runtime.server.http_app(path="/mcp", json_response=True, stateless_http=True)

    def local_client(**kwargs):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), **kwargs)

    incoming = StreamableHttpTransport(
        "http://pr-agent.test/mcp",
        headers={
            "Authorization": "Bearer PRIVATE_CLIENT_TOKEN",
            "Cookie": "private_session=PRIVATE_COOKIE",
            "X-User-Secret": "PRIVATE_CUSTOM_HEADER",
        },
        httpx_client_factory=local_client,
    )
    async with app.router.lifespan_context(app), Client(incoming) as client:
        result = await client.call_tool(
            "ask_pr",
            {
                "pr_url": "https://github.com/example/repo/pull/42",
                "question": "PRIVATE_QUESTION",
                "tenant_id": "http-test",
                "public_web_query": QUERY,
                "public_web_urls": [SOURCE],
            },
        )
    assert SOURCE in result.content[0].text
    assert [name for name, _ in mcp_http.calls] == ["web_search", "web_fetch"]
    for request in mcp_http.requests:
        assert "authorization" not in request["headers"]
        assert "cookie" not in request["headers"]
        assert "x-user-secret" not in request["headers"]
        assert "PRIVATE_" not in str(request)


@pytest.mark.asyncio
@pytest.mark.parametrize("disabled", ["provider", "operator", "call"])
async def test_disabled_access(runtime, mcp_http, monkeypatch, disabled):
    kwargs = {"public_web_query": QUERY}
    if disabled == "provider":
        monkeypatch.setenv("PR_AGENT_SEARCH_PROVIDER", "none")
    elif disabled == "operator":
        monkeypatch.setenv("PR_AGENT_WEB_SEARCH_ENABLED", "false")
        kwargs["web_search_enabled"] = True  # Cannot override operator permission.
    else:
        kwargs["web_search_enabled"] = False
    assert "disabled" in await ask(runtime, **kwargs)
    assert mcp_http.requests == []


@pytest.mark.asyncio
async def test_local_calls_and_question_cache(runtime, mcp_http):
    first = await ask(runtime, question="first question")
    second = await ask(runtime, question="second question")
    assert "first question" in first and "second question" in second
    assert await ask(runtime, question="first question") == first
    assert len(runtime.prompts) == 2
    assert mcp_http.requests == []


@pytest.mark.asyncio
async def test_web_answers_fresh_and_configuration_reread(
    runtime, mcp_http, monkeypatch
):
    await ask(runtime, public_web_query=QUERY)
    await ask(runtime, public_web_query=QUERY)
    assert len(mcp_http.calls) == 2
    assert mcp_http.calls[0][1]["session_id"] == mcp_http.calls[1][1]["session_id"]
    monkeypatch.setenv("PR_AGENT_SEARCH_PROVIDER", "none")
    assert "disabled" in await ask(runtime, public_web_query=QUERY)
    assert len(mcp_http.calls) == 2
    monkeypatch.setenv("PR_AGENT_SEARCH_PROVIDER", "unknown-configured-provider")
    assert "Unsupported PR_AGENT_SEARCH_PROVIDER" in await ask(
        runtime, public_web_query=QUERY
    )
    assert len(mcp_http.calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "urls",
    [
        ["file:///etc/passwd"],
        ["https://user:secret@example.com"],
        ["http://127.0.0.1"],
        ["http://127.1"],
        ["http://localhost."],
        ["http://[::1]"],
        ["https://docs.local/x"],
        ["https://example.com:123/x"],
        [SOURCE] * 6,
    ],
)
async def test_url_validation_before_network(runtime, mcp_http, urls):
    output = await ask(runtime, public_web_urls=urls)
    assert "Error:" in output
    assert mcp_http.requests == []


@pytest.mark.asyncio
async def test_query_limit(runtime, mcp_http):
    assert "1000 characters" in await ask(runtime, public_web_query="x" * 1001)
    assert mcp_http.requests == []


@pytest.mark.asyncio
async def test_provider_errors_are_safe_no_model_fallback(runtime, mcp_http):
    mcp_http.error = True
    assert "Public web lookup failed" in await ask(runtime, public_web_query=QUERY)
    assert len(mcp_http.calls) == 1
    assert runtime.prompts == []
    assert "PRIVATE_PROVIDER_DIAGNOSTIC" not in await ask(
        runtime, public_web_query=QUERY
    )


@pytest.mark.asyncio
async def test_timeout_closes_http_client(runtime, mcp_http, monkeypatch):
    mcp_http.wait = True
    monkeypatch.setenv("PR_AGENT_SEARCH_TIMEOUT", "0.15")
    assert "timed out" in await ask(runtime, public_web_query=QUERY)
    assert mcp_http.clients and all(client.is_closed for client in mcp_http.clients)
    assert runtime.prompts == []


@pytest.mark.asyncio
async def test_cancellation_propagates(runtime, mcp_http):
    mcp_http.wait = True
    task = asyncio.create_task(
        PRQuestionsAgent().execute(
            {
                "pr_url": "https://github.com/example/repo/pull/42",
                "question": "PRIVATE_QUESTION",
                "public_web_query": QUERY,
                "tenant_id": "cancel-test",
            }
        )
    )
    await asyncio.wait_for(mcp_http.entered.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert mcp_http.clients and all(client.is_closed for client in mcp_http.clients)
    assert runtime.prompts == []


@pytest.mark.asyncio
async def test_missing_tenant_denies_network(runtime, mcp_http):
    with pytest.raises(ValueError, match="Valid tenant_id required"):
        await PRQuestionsAgent().execute({"public_web_query": QUERY})
    assert mcp_http.requests == []


@pytest.mark.asyncio
async def test_fetch_only_preserves_url(runtime, mcp_http):
    url = "https://docs.python.org/3/library/asyncio-task.html?q=cancel%20task#shield"
    output = await ask(runtime, public_web_urls=[url])
    assert "Fetched sources:" in output
    assert [name for name, _ in mcp_http.calls] == ["web_fetch"]
    assert mcp_http.calls[0][1]["urls"] == [url]


@pytest.mark.asyncio
async def test_response_budget_retains_both_results(runtime, mcp_http):
    mcp_http.text = "reference " * 5000
    output = await ask(runtime, public_web_query=QUERY, public_web_urls=[SOURCE])
    web_context = runtime.prompts[-1][-1].content.split("Public documentation:\n", 1)[1]
    assert len(web_context) <= web_search.MAX_CONTEXT_CHARS
    assert "Search sources:" in output and "Fetched sources:" in output
    assert web_context.count(SOURCE) == 2


@pytest.mark.asyncio
async def test_empty_sources_not_presented_as_verification(runtime, mcp_http):
    mcp_http.text = "   "
    assert "no readable sources" in await ask(runtime, public_web_query=QUERY)
    assert runtime.prompts == []


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["0", "nan", "inf", "121", "invalid"])
async def test_invalid_deadline_before_network(runtime, mcp_http, monkeypatch, value):
    monkeypatch.setenv("PR_AGENT_SEARCH_TIMEOUT", value)
    assert "PR_AGENT_SEARCH_TIMEOUT" in await ask(runtime, public_web_query=QUERY)
    assert mcp_http.requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"results": [], "errors": []},
        {"results": [{"url": SOURCE, "excerpts": []}]},
        {"results": [{"url": SOURCE, "excerpts": ["   "]}]},
        {"unexpected": "PRIVATE_PROVIDER_DIAGNOSTIC"},
        {"results": [{"url": SOURCE, "excerpts": "malformed"}]},
        {
            "results": [],
            "errors": [
                {
                    "url": SOURCE,
                    "error_type": "fetch_error",
                    "http_status_code": 404,
                    "content": "PRIVATE_PROVIDER_DIAGNOSTIC",
                }
            ],
        },
        {
            "results": [{"url": SOURCE, "excerpts": ["valid excerpt"]}],
            "errors": [
                {
                    "url": "https://example.com/missing",
                    "content": "PRIVATE_PROVIDER_DIAGNOSTIC",
                }
            ],
        },
    ],
)
async def test_provider_payload_errors_do_not_reach_model(runtime, mcp_http, payload):
    mcp_http.payload = payload
    output = await ask(runtime, public_web_urls=[SOURCE])
    assert "Error:" in output
    assert "PRIVATE_PROVIDER_DIAGNOSTIC" not in output
    assert runtime.prompts == []
