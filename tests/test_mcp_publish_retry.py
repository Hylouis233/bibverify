"""Offline classifier and workflow tests; the publisher is always a local stub."""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "tools" / "mcp_publish_retry.py"
SPEC = importlib.util.spec_from_file_location("mcp_publish_retry", HELPER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

# Sanitized responses from the v0.5.0 Registry publication failure.
PYPI = 'Error: publish failed: server returned status 400: {"title":"Bad Request","status":400,"detail":"Failed to publish server","errors":[{"message":"registry validation failed for package 0 (bibverify): PyPI package \'bibverify\' exists, but version \'0.5.0\' was not found (status: 404). A newly published release can take a moment to appear on PyPI. Wait and retry, or publish version \'0.5.0\' before registering it"}]}'
NPM = 'Error: publish failed: server returned status 400: {"title":"Bad Request","status":400,"detail":"Failed to publish server","errors":[{"message":"registry validation failed for package 1 (@hylouis233/bibverify): NPM package \'@hylouis233/bibverify\' exists, but version \'0.5.0\' was not found (status: 404). A newly published release can take a moment to appear on the registry. Wait and retry, or publish version \'0.5.0\' before registering it"}]}'
AUTH = 'Error: publish failed: server returned status 401: {"title":"Unauthorized","status":401,"detail":"Invalid or expired Registry JWT token","errors":[{"message":"failed to parse token: token has invalid claims: token is expired"}]}'


class ClassifierTests(unittest.TestCase):
    def test_known_propagation_responses(self):
        for output in (PYPI, NPM, MODULE.BANNER + "\n" + PYPI + "\n\n"):
            self.assertTrue(MODULE.is_propagation_failure(output))
        payload = json.loads(PYPI[len(MODULE.PREFIX) :])
        payload["errors"].extend(json.loads(NPM[len(MODULE.PREFIX) :])["errors"])
        self.assertTrue(MODULE.is_propagation_failure(MODULE.PREFIX + json.dumps(payload)))

    def test_fail_closed(self):
        cases = [
            AUTH,
            "",
            "network timeout",
            PYPI + "\n" + AUTH,
            PYPI + " trailing",
            PYPI.replace("400:", "500:"),
            PYPI.replace('"status":400', '"status":401'),
            PYPI.replace('"status":400', '"status":400,"status":400'),
            PYPI.replace("0.5.0' before", "0.6.0' before"),
            PYPI.replace("PyPI. Wait", "the registry. Wait"),
        ]
        payload = json.loads(PYPI[len(MODULE.PREFIX) :])
        for key, value in (
            ("detail", "Invalid credentials"),
            ("extra", "fatal"),
            ("errors", []),
            ("errors", ["bad"]),
            ("errors", [{"message": 3}]),
            ("errors", [{"message": "schema failure"}]),
            ("errors", payload["errors"] + [{"message": "unauthorized"}]),
            ("errors", [{**payload["errors"][0], "extra": "fatal"}]),
        ):
            cases.append(MODULE.PREFIX + json.dumps({**payload, key: value}))
        for output in cases:
            with self.subTest(output=output):
                self.assertFalse(MODULE.is_propagation_failure(output))

    def test_cli(self):
        for output, expected in ((PYPI, 0), (NPM, 0), (AUTH, 1), ("{}", 1)):
            result = subprocess.run(
                [sys.executable, str(HELPER)],
                input=output,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, expected)
            self.assertEqual(result.stdout, "")


@unittest.skipUnless(
    os.name == "posix" and shutil.which("bash"), "workflow runs on Ubuntu and needs POSIX Bash"
)
class WorkflowTests(unittest.TestCase):
    def run_workflow(self, failures=(), login_failure=0, repeat=False):
        workflow = (ROOT / ".github/workflows/publish-mcp.yml").read_text(encoding="utf-8")
        step = workflow.split(
            "      - name: Publish server metadata with fresh authentication\n", 1
        )[1]
        self.assertIn("        timeout-minutes: 35\n", step)
        script = textwrap.dedent(step.split("        run: |\n", 1)[1])
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            (work / "tools").mkdir()
            shutil.copy2(HELPER, work / "tools" / HELPER.name)
            (work / "failures.json").write_text(json.dumps(list(failures)), encoding="utf-8")
            publisher = work / "mcp-publisher"
            publisher.write_text(
                "#!/bin/sh\nexec " + shlex.quote(sys.executable) + ' stub.py "$@"\n',
                encoding="utf-8",
            )
            publisher.chmod(0o755)
            (work / "stub.py").write_text(
                textwrap.dedent("""
                import json
                import os
                import sys
                from pathlib import Path
                state = Path("state.json")
                data = json.loads(state.read_text()) if state.exists() else {"login": 0, "publish": 0}
                command = sys.argv[1]
                assert sys.argv[1:] in (["login", "github-oidc"], ["publish"])
                data[command] += 1
                state.write_text(json.dumps(data))
                with Path("calls").open("a") as calls:
                    calls.write(command + "\\n")
                if command == "login":
                    if data["login"] == int(os.environ["LOGIN_FAILURE"]):
                        sys.exit(7)
                    Path("fresh-token").write_text("stub")
                    sys.exit(0)
                token = Path("fresh-token")
                assert token.exists(), "publish without fresh authentication"
                token.unlink()
                failures = json.loads(Path("failures.json").read_text())
                index = 0 if os.environ["REPEAT"] == "1" else data["publish"] - 1
                if index < len(failures):
                    print(failures[index], file=sys.stderr)
                    sys.exit(1)
            """),
                encoding="utf-8",
            )
            binary = work / "bin"
            binary.mkdir()
            for name, body in (
                ("python", "exec " + shlex.quote(sys.executable) + ' "$@"'),
                ("sleep", 'test "$1" = 30 || exit 8\nprintf "sleep\\n" >> calls'),
            ):
                path = binary / name
                path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
                path.chmod(0o755)
            env = {
                **os.environ,
                "PATH": str(binary) + os.pathsep + os.environ["PATH"],
                "LOGIN_FAILURE": str(login_failure),
                "REPEAT": "1" if repeat else "0",
                "TMPDIR": str(work),
            }
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", script],
                cwd=work,
                env=env,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            calls = (work / "calls").read_text().splitlines()
            self.assertEqual(list(work.glob("tmp.*")), [], "publish log must be removed")
            return result, calls

    def test_success(self):
        result, calls = self.run_workflow()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(calls, ["login", "publish"])

    def test_propagation_then_success(self):
        result, calls = self.run_workflow([PYPI, NPM])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(calls, ["login", "publish", "sleep"] * 2 + ["login", "publish"])

    def test_auth_failure(self):
        result, calls = self.run_workflow([AUTH])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(calls, ["login", "publish"])

    def test_unknown_failure(self):
        result, calls = self.run_workflow(["network timeout"])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(calls, ["login", "publish"])

    def test_mixed_failure(self):
        result, calls = self.run_workflow([PYPI + "\n" + AUTH])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(calls, ["login", "publish"])

    def test_first_login_failure(self):
        result, calls = self.run_workflow(login_failure=1)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(calls, ["login"])

    def test_retry_login_failure(self):
        result, calls = self.run_workflow([PYPI], login_failure=2)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(calls, ["login", "publish", "sleep", "login"])

    def test_retry_limit(self):
        result, calls = self.run_workflow([NPM], repeat=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(calls, ["login", "publish", "sleep"] * 59 + ["login", "publish"])
        self.assertIn("failed after 60 attempts", result.stdout)
