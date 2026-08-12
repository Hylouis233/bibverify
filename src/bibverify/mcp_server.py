"""Official MCP SDK server for Bibverify."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Literal, cast

import anyio
from mcp.server import MCPServer

from bibverify import __version__
from bibverify.checker import BibTeXChecker

Transport = Literal["stdio", "streamable-http"]


def create_server(default_config: str = "config.json") -> MCPServer[None]:
    """Build a protocol-compliant MCP server with typed tool schemas."""
    server: MCPServer[None] = MCPServer(
        "bibverify",
        title="Bibverify",
        description="Verify, repair, and enrich BibTeX references.",
        version=__version__,
        website_url="https://github.com/Hylouis233/bibverify",
    )

    def checker(config_file: str | None = None) -> BibTeXChecker:
        return BibTeXChecker(Path(config_file or default_config))

    @server.tool(structured_output=True)
    def doi_to_bibtex(
        doi: str,
        key: str | None = None,
        config_file: str | None = None,
    ) -> dict[str, Any]:
        """Fetch one DOI through Crossref and return a BibTeX entry."""
        with redirect_stdout(io.StringIO()):
            service = checker(config_file)
            bibtex = service.bibtex_from_doi(doi, key=key)
        if not bibtex:
            raise ValueError(service.lang.get_text("doi_not_found", doi=doi))
        return {"doi": service.canonicalize_doi(doi), "bibtex": bibtex.strip()}

    @server.tool(structured_output=True)
    def rank_lookup_sources(
        title: str,
        entry: dict[str, Any] | None = None,
        config_file: str | None = None,
    ) -> dict[str, Any]:
        """Return the effective provider order for a reference."""
        with redirect_stdout(io.StringIO()):
            order = checker(config_file)._rank_platforms_for_entry(title, entry or {})
        return {"platforms": order}

    @server.tool(structured_output=True)
    def explain_update_diff(
        original: dict[str, Any],
        updated: dict[str, Any],
        config_file: str | None = None,
    ) -> dict[str, Any]:
        """Compare two BibTeX-like entries and return field-level changes."""
        with redirect_stdout(io.StringIO()):
            differences = checker(config_file).compare_entries(original, updated)
        return {"differences": differences}

    @server.tool(structured_output=True)
    def verify_bib_file(config_file: str | None = None) -> dict[str, Any]:
        """Verify the configured BibTeX file and return a structured summary."""
        with redirect_stdout(io.StringIO()):
            return cast(dict[str, Any], checker(config_file).run())

    return server


def run_server(default_config: str = "config.json", transport: Transport = "stdio") -> None:
    """Run Bibverify over stdio or Streamable HTTP."""
    if transport not in {"stdio", "streamable-http"}:
        raise ValueError("transport must be 'stdio' or 'streamable-http'")
    create_server(default_config).run(transport=transport)


def _text_result(
    text: str, is_error: bool = False, structured: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compatibility result shape retained for v0.2 unit/API consumers."""
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}], "isError": is_error}
    if structured is not None:
        result["structuredContent"] = structured
    return result


def _call_compat(name: str, arguments: dict[str, Any], default_config: str) -> dict[str, Any]:
    config_file = arguments.get("config_file") or default_config
    with redirect_stdout(io.StringIO()):
        checker = BibTeXChecker(config_file)
        if name == "doi_to_bibtex":
            bibtex = checker.bibtex_from_doi(arguments.get("doi", ""), key=arguments.get("key"))
            if not bibtex:
                return _text_result(
                    checker.lang.get_text("doi_not_found", doi=arguments.get("doi", "")), True
                )
            return _text_result(bibtex.strip(), structured={"bibtex": bibtex.strip()})
        if name == "rank_lookup_sources":
            order = checker._rank_platforms_for_entry(
                arguments.get("title", ""), arguments.get("entry") or {}
            )
            return _text_result("\n".join(order), structured={"platforms": order})
        if name == "explain_update_diff":
            differences = checker.compare_entries(
                arguments.get("original") or {}, arguments.get("updated") or {}
            )
            return _text_result(json.dumps(differences), structured={"differences": differences})
        if name == "verify_bib_file":
            summary = checker.run()
            return _text_result("Bibverify completed.", structured=summary)
    raise ValueError(f"Unknown tool: {name}")


def handle_request(
    message: dict[str, Any], default_config: str = "config.json"
) -> dict[str, Any] | None:
    """Compatibility adapter for callers that used the v0.2 request helper."""
    request_id = message.get("id")
    method = message.get("method")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "bibverify", "version": __version__},
            },
        }
    if method == "tools/list":
        server = create_server(default_config)
        tools = anyio.run(server.list_tools)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [tool.model_dump(by_alias=True, exclude_none=True) for tool in tools]
            },
        }
    if method == "tools/call":
        params = message.get("params") or {}
        try:
            result = _call_compat(
                params.get("name", ""), params.get("arguments") or {}, default_config
            )
        except Exception as exc:
            result = _text_result(str(exc), True)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    if request_id is None:
        return None
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def run_stdio_server(
    default_config: str = "config.json", stdin: Any = None, stdout: Any = None
) -> int:
    """Compatibility JSON-lines harness; production uses the official SDK runner."""
    if stdin is None and stdout is None:
        run_server(default_config, "stdio")
        return 0
    for line in stdin:
        if not line.strip():
            continue
        try:
            response = handle_request(json.loads(line), default_config)
        except Exception as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(exc)},
            }
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()
    return 0
