"""Modern, script-friendly command-line interface for Bibverify."""

from __future__ import annotations

import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Annotated, Literal, cast

import click
import typer
from rich.console import Console

from bibverify import __version__
from bibverify.agent import (
    SUPPORTED_TARGETS,
    doctor,
    export_skill,
    format_doctor_report,
    init_agent,
)
from bibverify.benchmark import run_benchmark
from bibverify.cache import ResponseCache
from bibverify.checker import BibTeXChecker
from bibverify.config import create_config, load_config
from bibverify.models import QueryStatus

app = typer.Typer(
    name="bibverify",
    help="Verify, repair, and enrich BibTeX references.",
    no_args_is_help=True,
    add_completion=False,
)
config_app = typer.Typer(help="Create and inspect configuration files.")
agent_app = typer.Typer(help="Set up Bibverify for AI assistants.")
skill_app = typer.Typer(help="Export AI-assistant skill instructions.")
providers_app = typer.Typer(help="Inspect academic metadata providers.")
cache_app = typer.Typer(help="Inspect or clear the local metadata response cache.")
app.add_typer(config_app, name="config")
app.add_typer(agent_app, name="agent")
app.add_typer(skill_app, name="skill")
app.add_typer(providers_app, name="providers")
app.add_typer(cache_app, name="cache")

console = Console()
error_console = Console(stderr=True)


def _version_callback(value: bool) -> None:
    if value:
        console.print(__version__)
        raise typer.Exit()


@app.callback()
def root(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_version_callback, is_eager=True, help="Show the version."
        ),
    ] = False,
) -> None:
    """Bibverify command group."""


@app.command()
def check(
    bib_file: Annotated[Path | None, typer.Argument(help="BibTeX file to verify.")] = None,
    config: Annotated[Path, typer.Option("--config", "-c", help="Configuration JSON path.")] = Path(
        "config.json"
    ),
    output_dir: Annotated[
        Path | None, typer.Option("--output-dir", "-o", help="Directory for generated files.")
    ] = None,
    encoding: Annotated[str | None, typer.Option(help="Input encoding or 'auto'.")] = None,
    language: Annotated[
        str | None, typer.Option("--language", "-l", help="Output language: CN or EN.")
    ] = None,
    report_format: Annotated[
        str | None,
        typer.Option("--format", help="Report format: txt, json, jsonl, or csv."),
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Write a machine-readable summary to stdout.")
    ] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress progress output.")] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Verify without writing any report, backup, or BibTeX file."
        ),
    ] = False,
    apply_changes: Annotated[
        bool,
        typer.Option(
            "--apply", help="Apply high-confidence field updates to the input file after backup."
        ),
    ] = False,
) -> None:
    """Verify a BibTeX file and write safe output files."""
    overrides: dict[str, object] = {}
    if bib_file is not None:
        overrides["bib_file"] = str(bib_file.expanduser().resolve(strict=False))
    if output_dir is not None:
        overrides["output_dir"] = str(output_dir.expanduser().resolve(strict=False))
    if encoding:
        overrides["encoding"] = encoding
    if language:
        overrides["language"] = language.upper()
    if report_format:
        overrides["output_settings"] = {"report_format": report_format.lower()}

    if dry_run and apply_changes:
        raise typer.BadParameter("--dry-run and --apply are mutually exclusive")
    captured = StringIO()
    try:
        if quiet or json_output:
            with redirect_stdout(captured):
                summary = BibTeXChecker(
                    config,
                    overrides=overrides,
                    dry_run=dry_run,
                    apply_changes=apply_changes,
                ).run()
        else:
            summary = BibTeXChecker(
                config,
                overrides=overrides,
                dry_run=dry_run,
                apply_changes=apply_changes,
            ).run()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        error_console.print(f"Error: {exc}")
        raise typer.Exit(code=5) from exc

    if json_output:
        typer.echo(json.dumps(summary, ensure_ascii=False, indent=2))

    counts = summary["counts"]
    if counts.get("invalid_input", 0):
        raise typer.Exit(code=5)
    if (
        not summary.get("complete", True)
        or counts.get("source_unavailable", 0)
        or counts.get("errors", 0)
    ):
        raise typer.Exit(code=4)
    if (
        counts.get("ambiguous", 0)
        or counts.get("not_found", 0)
        or counts.get("identifier_conflict", 0)
    ):
        raise typer.Exit(code=3)
    if counts.get("updated", 0):
        raise typer.Exit(code=2)


@app.command()
def doi(
    value: Annotated[str, typer.Argument(help="DOI, DOI URL, or DOI-prefixed value.")],
    key: Annotated[str | None, typer.Option(help="BibTeX citation key.")] = None,
    config: Annotated[Path, typer.Option("--config", "-c", help="Configuration JSON path.")] = Path(
        "config.json"
    ),
    json_output: Annotated[
        bool, typer.Option("--json", help="Write a machine-readable result.")
    ] = False,
) -> None:
    """Resolve one DOI to a BibTeX entry."""
    with redirect_stdout(StringIO()):
        checker = BibTeXChecker(config)
        bibtex, lookup = checker.bibtex_from_doi_result(value, key=key)
    if not bibtex:
        error_console.print(checker.doi_lookup_failure_message(value, lookup))
        if lookup.status.is_unavailable:
            raise typer.Exit(code=4)
        if lookup.status is QueryStatus.IDENTIFIER_CONFLICT:
            raise typer.Exit(code=3)
        raise typer.Exit(code=1)
    if json_output:
        typer.echo(
            json.dumps(
                {"doi": checker.canonicalize_doi(value), "bibtex": bibtex.strip()},
                ensure_ascii=False,
            )
        )
    else:
        typer.echo(bibtex.strip())


@config_app.command("init")
def config_init(
    output: Annotated[Path, typer.Option("--output", "-o", help="Destination JSON path.")] = Path(
        "config.json"
    ),
    force: Annotated[bool, typer.Option("--force", help="Replace an existing file.")] = False,
) -> None:
    """Create a documented starter configuration."""
    try:
        written = create_config(output, force=force)
    except FileExistsError as exc:
        raise typer.BadParameter(str(exc), param_hint="--output") from exc
    console.print(f"Created {written}")


@app.command("doctor")
def doctor_command(
    config: Annotated[Path, typer.Option("--config", "-c", help="Configuration JSON path.")] = Path(
        "config.json"
    ),
    json_output: Annotated[bool, typer.Option("--json", help="Write checks as JSON.")] = False,
) -> None:
    """Check installation, configuration, and local runtime readiness."""
    checks = doctor(config_file=str(config))
    if json_output:
        typer.echo(json.dumps(checks, ensure_ascii=False, indent=2))
    else:
        console.print(format_doctor_report(checks))
    if any(not item["ok"] and item.get("required", False) for item in checks):
        raise typer.Exit(code=2)


@providers_app.command("list")
def providers_list(json_output: Annotated[bool, typer.Option("--json")] = False) -> None:
    """List supported metadata providers."""
    from bibverify.providers import PROVIDER_NAMES

    if json_output:
        typer.echo(json.dumps({"providers": list(PROVIDER_NAMES)}))
    else:
        for name in PROVIDER_NAMES:
            console.print(name)


@cache_app.command("clear")
def cache_clear(
    config: Annotated[Path, typer.Option("--config", "-c", help="Configuration JSON path.")] = Path(
        "config.json"
    ),
) -> None:
    """Delete Bibverify's SQLite response cache."""
    loaded, _ = load_config(config)
    path = Path(loaded["query_settings"]["cache_path"])
    removed = ResponseCache(path).clear()
    console.print(f"{'Removed' if removed else 'No cache found at'} {path}")


@app.command("benchmark")
def benchmark_command(
    dataset: Annotated[
        Path | None,
        typer.Option("--dataset", help="Path to a labeled JSON benchmark dataset."),
    ] = None,
) -> None:
    """Run the deterministic offline matching benchmark."""
    result = run_benchmark(dataset)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if result["wrong_auto_match_rate"] > 0:
        raise typer.Exit(code=1)


@app.command("mcp")
def mcp_command(
    config: Annotated[
        Path, typer.Option("--config", "-c", help="Default configuration path.")
    ] = Path("config.json"),
    transport: Annotated[
        str, typer.Option(help="MCP transport: stdio or streamable-http.")
    ] = "stdio",
    workspace_root: Annotated[
        Path | None,
        typer.Option(
            "--workspace-root",
            help="Restrict MCP file reads/writes to this directory (defaults to the config directory).",
        ),
    ] = None,
) -> None:
    """Run the official MCP SDK server."""
    from bibverify.mcp_server import run_server

    if transport not in {"stdio", "streamable-http"}:
        raise typer.BadParameter("transport must be stdio or streamable-http")
    run_server(
        default_config=str(config),
        transport=cast(Literal["stdio", "streamable-http"], transport),
        workspace_root=str(workspace_root) if workspace_root else None,
    )


@agent_app.command("init")
def agent_init(
    target: Annotated[str, typer.Option(help="Assistant target.")] = "generic",
    output: Annotated[Path, typer.Option("--output", "-o")] = Path(".bibverify-agent"),
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config.json"),
) -> None:
    """Create ready-to-copy MCP and skill integration files."""
    if target not in SUPPORTED_TARGETS:
        raise typer.BadParameter(f"target must be one of {', '.join(SUPPORTED_TARGETS)}")
    for path in init_agent(target=target, output=str(output), config_file=str(config)):
        console.print(path)


@agent_app.command("doctor")
def agent_doctor(
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config.json"),
) -> None:
    """Alias for ``bibverify doctor``."""
    doctor_command(config=config, json_output=False)


@skill_app.command("export")
def skill_export(
    target: Annotated[str, typer.Option(help="Assistant target.")] = "generic",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config.json"),
) -> None:
    """Export Bibverify skill instructions."""
    if target not in SUPPORTED_TARGETS:
        raise typer.BadParameter(f"target must be one of {', '.join(SUPPORTED_TARGETS)}")
    written = export_skill(
        target=target,
        output=str(output) if output else None,
        config_file=str(config),
    )
    if written:
        console.print(written)


def _translate_legacy_args(argv: list[str]) -> list[str]:
    """Keep v0.2 command forms working during the v0.3 transition."""
    commands = {
        "check",
        "doi",
        "config",
        "doctor",
        "providers",
        "cache",
        "benchmark",
        "mcp",
        "agent",
        "skill",
    }
    if "--doi" in argv:
        index = argv.index("--doi")
        if index + 1 >= len(argv):
            return argv
        value = argv[index + 1]
        remaining = argv[:index] + argv[index + 2 :]
        config_args: list[str] = []
        if remaining and not remaining[0].startswith("-"):
            config_args = ["--config", remaining.pop(0)]
        return ["doi", value, *config_args, *remaining]
    if argv and not argv[0].startswith("-") and argv[0] not in commands:
        return ["check", "--config", argv[0], *argv[1:]]
    return argv


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    args = _translate_legacy_args(list(sys.argv[1:] if argv is None else argv))
    try:
        app(args=args, standalone_mode=False)
    except typer.Exit as exc:
        return int(exc.exit_code)
    except click.ClickException as exc:
        exc.show(file=sys.stderr)
        return int(exc.exit_code)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
