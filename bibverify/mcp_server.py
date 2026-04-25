import io
import json
import sys
from contextlib import redirect_stdout

from bib_check import BibTeXChecker
from bibverify import __version__


PROTOCOL_VERSION = "2025-06-18"


TOOLS = [
    {
        "name": "doi_to_bibtex",
        "title": "DOI to BibTeX",
        "description": "Fetch one DOI through Crossref and return a BibTeX entry.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "doi": {"type": "string", "description": "DOI, DOI URL, or DOI-prefixed value."},
                "key": {"type": "string", "description": "Optional BibTeX key."},
                "config_file": {"type": "string", "description": "Optional Bibverify config path."},
            },
            "required": ["doi"],
        },
    },
    {
        "name": "rank_lookup_sources",
        "title": "Rank Lookup Sources",
        "description": "Return the effective metadata-source order for a title and optional BibTeX entry.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Reference title."},
                "entry": {"type": "object", "description": "Optional BibTeX-like entry fields."},
                "config_file": {"type": "string", "description": "Optional Bibverify config path."},
            },
            "required": ["title"],
        },
    },
    {
        "name": "explain_update_diff",
        "title": "Explain Update Diff",
        "description": "Compare two BibTeX-like entry objects and return field-level differences.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "original": {"type": "object", "description": "Original entry fields."},
                "updated": {"type": "object", "description": "Updated entry fields."},
                "config_file": {"type": "string", "description": "Optional Bibverify config path."},
            },
            "required": ["original", "updated"],
        },
    },
    {
        "name": "verify_bib_file",
        "title": "Verify BibTeX File",
        "description": "Run Bibverify against a config file and return a captured text summary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "config_file": {"type": "string", "description": "Bibverify config path."},
            },
            "required": [],
        },
    },
]


def _response(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _text_result(text, is_error=False, structured=None):
    result = {
        "content": [{"type": "text", "text": text}],
        "isError": bool(is_error),
    }
    if structured is not None:
        result["structuredContent"] = structured
    return result


def _checker(config_file):
    return BibTeXChecker(config_file or "config.json")


def _call_tool(name, arguments, default_config="config.json"):
    arguments = arguments or {}
    config_file = arguments.get("config_file") or default_config
    captured = io.StringIO()

    with redirect_stdout(captured):
        checker = _checker(config_file)
        if name == "doi_to_bibtex":
            bibtex = checker.bibtex_from_doi(arguments.get("doi", ""), key=arguments.get("key"))
            logs = captured.getvalue().strip()
            if not bibtex:
                text = checker.lang.get_text("doi_not_found", doi=arguments.get("doi", ""))
                if logs:
                    text = f"{text}\n\nLogs:\n{logs}"
                return _text_result(text, is_error=True)
            text = bibtex.strip()
            if logs:
                text = f"{text}\n\nLogs:\n{logs}"
            return _text_result(text, structured={"bibtex": bibtex.strip()})

        if name == "rank_lookup_sources":
            title = arguments.get("title", "")
            entry = arguments.get("entry") or {}
            order = checker._rank_platforms_for_entry(title, entry)
            text = "Effective lookup order:\n" + "\n".join(f"- {platform}" for platform in order)
            logs = captured.getvalue().strip()
            if logs:
                text = f"{text}\n\nLogs:\n{logs}"
            return _text_result(text, structured={"platforms": order})

        if name == "explain_update_diff":
            original = arguments.get("original") or {}
            updated = arguments.get("updated") or {}
            differences = checker.compare_entries(original, updated)
            text = json.dumps(differences, ensure_ascii=False, indent=2)
            logs = captured.getvalue().strip()
            if logs:
                text = f"{text}\n\nLogs:\n{logs}"
            return _text_result(text, structured={"differences": differences})

        if name == "verify_bib_file":
            checker.run()
            output = captured.getvalue().strip()
            return _text_result(output or "Bibverify completed.")

    raise ValueError("Unknown tool: " + name)


def handle_request(message, default_config="config.json"):
    request_id = message.get("id")
    method = message.get("method")

    if method == "initialize":
        return _response(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "bibverify", "version": __version__},
            },
        )

    if method == "tools/list":
        return _response(request_id, {"tools": TOOLS})

    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            return _response(request_id, _call_tool(name, arguments, default_config=default_config))
        except Exception as exc:
            return _response(request_id, _text_result(str(exc), is_error=True))

    if request_id is None:
        return None

    return _error(request_id, -32601, "Method not found: " + str(method))


def run_stdio_server(default_config="config.json", stdin=None, stdout=None):
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            response = handle_request(message, default_config=default_config)
        except Exception as exc:
            response = _error(None, -32700, str(exc))
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()
    return 0
