"""Generate package-manager manifests from verified standalone release files."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

if __package__:
    from .sync_release_metadata import source_version
else:
    from sync_release_metadata import source_version

REPOSITORY = "https://github.com/Hylouis233/bibverify"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def required_assets(release_dir: Path, version: str) -> dict[str, Path]:
    names = {
        "windows-x64": f"bibverify-{version}-windows-x64.exe",
        "macos-x64": f"bibverify-{version}-macos-x64.tar.gz",
        "macos-arm64": f"bibverify-{version}-macos-arm64.tar.gz",
        "linux-x64": f"bibverify-{version}-linux-x64.tar.gz",
        "linux-arm64": f"bibverify-{version}-linux-arm64.tar.gz",
    }
    assets = {target: release_dir / name for target, name in names.items()}
    missing = [path.name for path in assets.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing release assets: {', '.join(missing)}")
    return assets


def release_url(path: Path, version: str) -> str:
    return f"{REPOSITORY}/releases/download/v{version}/{path.name}"


def homebrew_formula(assets: dict[str, Path], version: str) -> str:
    def stanza(target: str) -> str:
        path = assets[target]
        return f'    url "{release_url(path, version)}"\n    sha256 "{sha256(path)}"'

    return f'''class Bibverify < Formula
  desc "Cross-platform BibTeX verification CLI and MCP server"
  homepage "{REPOSITORY}"
  version "{version}"
  license "MIT"

  on_macos do
    if Hardware::CPU.arm?
{stanza("macos-arm64")}
    else
{stanza("macos-x64")}
    end
  end

  on_linux do
    if Hardware::CPU.arm?
{stanza("linux-arm64")}
    else
{stanza("linux-x64")}
    end
  end

  def install
    bin.install "bibverify"
  end

  test do
    assert_equal version.to_s, shell_output("#{{bin}}/bibverify --version").strip
  end
end
'''


def scoop_manifest(assets: dict[str, Path], version: str) -> str:
    payload = {
        "version": version,
        "description": "Cross-platform BibTeX verification CLI and MCP server",
        "homepage": REPOSITORY,
        "license": "MIT",
        "architecture": {
            "64bit": {
                "url": f"{release_url(assets['windows-x64'], version)}#/bibverify.exe",
                "hash": sha256(assets["windows-x64"]),
            },
        },
        "bin": "bibverify.exe",
        "checkver": {"github": REPOSITORY},
        "autoupdate": {
            "architecture": {
                "64bit": {
                    "url": f"{REPOSITORY}/releases/download/v$version/bibverify-$version-windows-x64.exe#/bibverify.exe"
                },
            }
        },
    }
    return json.dumps(payload, indent=2) + "\n"


def winget_manifests(assets: dict[str, Path], version: str) -> dict[str, str]:
    identifier = "Hylouis233.Bibverify"
    base = f"PackageIdentifier: {identifier}\nPackageVersion: {version}\n"
    version_manifest = (
        f"# yaml-language-server: $schema=https://aka.ms/winget-manifest.version.1.12.0.schema.json\n"
        f"{base}DefaultLocale: en-US\nManifestType: version\nManifestVersion: 1.12.0\n"
    )
    locale_manifest = f"""# yaml-language-server: $schema=https://aka.ms/winget-manifest.defaultLocale.1.12.0.schema.json
{base}PackageLocale: en-US
Publisher: Hylouis233
PublisherUrl: {REPOSITORY.rsplit("/", 1)[0]}
PublisherSupportUrl: {REPOSITORY}/issues
PackageName: Bibverify
PackageUrl: {REPOSITORY}
License: MIT
LicenseUrl: {REPOSITORY}/blob/main/LICENSE
ShortDescription: Verify and repair BibTeX metadata across academic providers.
Description: Cross-platform BibTeX verification for researchers and AI assistants, with a CLI, Python API, MCP server, and explainable multi-source matching.
Moniker: bibverify
Tags:
- bibliography
- bibtex
- citation
- cli
- mcp
- research
ManifestType: defaultLocale
ManifestVersion: 1.12.0
"""
    installers = []
    for architecture, target in (("x64", "windows-x64"),):
        path = assets[target]
        installers.append(
            f"""- Architecture: {architecture}
  InstallerUrl: {release_url(path, version)}
  InstallerSha256: {sha256(path).upper()}
"""
        )
    installer_manifest = f"""# yaml-language-server: $schema=https://aka.ms/winget-manifest.installer.1.12.0.schema.json
{base}InstallerType: portable
Commands:
- bibverify
Installers:
{"".join(installers)}ManifestType: installer
ManifestVersion: 1.12.0
"""
    return {
        f"{identifier}.yaml": version_manifest,
        f"{identifier}.locale.en-US.yaml": locale_manifest,
        f"{identifier}.installer.yaml": installer_manifest,
    }


def generate(release_dir: Path, output_dir: Path, version: str | None = None) -> list[Path]:
    resolved_version = version or source_version()
    assets = required_assets(release_dir, resolved_version)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated = {
        "bibverify.rb": homebrew_formula(assets, resolved_version),
        "bibverify.json": scoop_manifest(assets, resolved_version),
        **winget_manifests(assets, resolved_version),
    }
    paths = []
    for name, content in generated.items():
        path = output_dir / name
        path.write_text(content, encoding="utf-8", newline="\n")
        paths.append(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version")
    args = parser.parse_args()
    for path in generate(args.release_dir, args.output_dir, args.version):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
