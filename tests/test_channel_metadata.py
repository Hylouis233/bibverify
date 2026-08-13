from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
from tools.generate_channel_metadata import generate
from tools.package_standalone import normalized_target


def test_channel_manifests_are_generated_from_release_bytes(tmp_path: Path):
    release = tmp_path / "release"
    output = tmp_path / "channels"
    release.mkdir()
    names = [
        "bibverify-9.8.7-windows-x64.exe",
        "bibverify-9.8.7-macos-x64.tar.gz",
        "bibverify-9.8.7-macos-arm64.tar.gz",
        "bibverify-9.8.7-linux-x64.tar.gz",
        "bibverify-9.8.7-linux-arm64.tar.gz",
    ]
    for name in names:
        (release / name).write_bytes(name.encode())

    generated = generate(release, output, "9.8.7")

    assert {path.name for path in generated} == {
        "bibverify.rb",
        "bibverify.json",
        "Hylouis233.Bibverify.yaml",
        "Hylouis233.Bibverify.locale.en-US.yaml",
        "Hylouis233.Bibverify.installer.yaml",
    }
    scoop = json.loads((output / "bibverify.json").read_text(encoding="utf-8"))
    expected = hashlib.sha256(b"bibverify-9.8.7-windows-x64.exe").hexdigest()
    assert scoop["architecture"]["64bit"]["hash"] == expected
    assert scoop["version"] == "9.8.7"
    assert set(scoop["architecture"]) == {"64bit"}

    formula = (output / "bibverify.rb").read_text(encoding="utf-8")
    assert 'version "9.8.7"' in formula
    assert "macos-arm64.tar.gz" in formula
    assert "linux-x64.tar.gz" in formula

    for path in output.glob("*.yaml"):
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert parsed["PackageVersion"] == "9.8.7"

    winget = yaml.safe_load(
        (output / "Hylouis233.Bibverify.installer.yaml").read_text(encoding="utf-8")
    )
    assert [installer["Architecture"] for installer in winget["Installers"]] == ["x64"]


def test_standalone_target_names_are_normalized(monkeypatch):
    monkeypatch.setenv("RUNNER_OS", "Linux")
    monkeypatch.setenv("RUNNER_ARCH", "ARM64")
    assert normalized_target() == ("linux", "arm64")

    monkeypatch.setenv("RUNNER_OS", "macOS")
    monkeypatch.setenv("RUNNER_ARCH", "X64")
    assert normalized_target() == ("macos", "x64")
