import assert from "node:assert/strict";
import { after, test } from "node:test";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { chmod, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { assetName, releaseTarget } from "../lib/platform.js";
import { ensureBinary, run, VERSION } from "../lib/runner.js";

const temporaryDirectories = [];
after(async () =>
  Promise.all(temporaryDirectories.map((path) => rm(path, { force: true, recursive: true }))),
);

test("maps every published operating system and architecture", () => {
  assert.equal(assetName("0.4.0", "win32", "x64"), "bibverify-0.4.0-windows-x64.exe");
  assert.equal(assetName("0.4.0", "win32", "arm64"), "bibverify-0.4.0-windows-x64.exe");
  assert.equal(assetName("0.4.0", "darwin", "x64"), "bibverify-0.4.0-macos-x64");
  assert.equal(assetName("0.4.0", "darwin", "arm64"), "bibverify-0.4.0-macos-arm64");
  assert.equal(assetName("0.4.0", "linux", "x64"), "bibverify-0.4.0-linux-x64");
  assert.equal(assetName("0.4.0", "linux", "arm64"), "bibverify-0.4.0-linux-arm64");
});

test("rejects targets for which no native release is built", () => {
  assert.throws(() => releaseTarget("freebsd", "x64"), /unsupported platform/u);
  assert.throws(() => releaseTarget("linux", "ia32"), /unsupported platform/u);
});

test("rejects musl Linux before selecting a glibc release", () => {
  assert.throws(
    () => assetName("0.4.0", "linux", "x64", "musl"),
    /unsupported Linux libc musl; published binaries require glibc 2\.28 or newer/u,
  );
});

test("forwards arguments and preserves the native exit code", async () => {
  process.env.BIBVERIFY_BINARY = process.execPath;
  try {
    assert.equal(await run(["-e", "process.exit(7)"]), 7);
  } finally {
    delete process.env.BIBVERIFY_BINARY;
  }
});

test(
  "forwards SIGTERM to the native child",
  { skip: process.platform === "win32" },
  async () => {
    const root = await mkdtemp(join(tmpdir(), "bibverify-npm-signal-test-"));
    temporaryDirectories.push(root);
    const pidFile = join(root, "native.pid");
    const runnerUrl = new URL("../lib/runner.js", import.meta.url).href;
    const nativeScript =
      'const fs = require("node:fs"); fs.writeFileSync(process.argv[1], String(process.pid)); setInterval(() => {}, 1000);';
    const wrapperScript = `import { run } from ${JSON.stringify(runnerUrl)}; process.exitCode = await run(["-e", ${JSON.stringify(nativeScript)}, ${JSON.stringify(pidFile)}]);`;
    const wrapper = spawn(process.execPath, ["--input-type=module", "--eval", wrapperScript], {
      env: { ...process.env, BIBVERIFY_BINARY: process.execPath },
      stdio: "ignore",
      windowsHide: true,
    });
    const wrapperExit = new Promise((resolve, reject) => {
      wrapper.once("error", reject);
      wrapper.once("exit", (code, signal) => resolve({ code, signal }));
    });
    let nativePid;

    try {
      const deadline = Date.now() + 5_000;
      while (Date.now() < deadline) {
        try {
          nativePid = Number(await readFile(pidFile, "utf8"));
          break;
        } catch {
          await new Promise((resolve) => setTimeout(resolve, 25));
        }
      }
      assert.ok(Number.isInteger(nativePid), "native child did not start");

      assert.equal(wrapper.kill("SIGTERM"), true);
      assert.deepEqual(await wrapperExit, { code: 143, signal: null });

      const reapDeadline = Date.now() + 5_000;
      while (Date.now() < reapDeadline) {
        try {
          process.kill(nativePid, 0);
          await new Promise((resolve) => setTimeout(resolve, 25));
        } catch (error) {
          if (error?.code === "ESRCH") return;
          throw error;
        }
      }
      assert.fail(`native child ${nativePid} remained alive after SIGTERM`);
    } finally {
      if (wrapper.exitCode === null && wrapper.signalCode === null) wrapper.kill("SIGKILL");
      if (Number.isInteger(nativePid)) {
        try {
          process.kill(nativePid, "SIGKILL");
        } catch (error) {
          if (error?.code !== "ESRCH") throw error;
        }
      }
    }
  },
);

test("downloads and verifies an uncached native release", async () => {
  const root = await mkdtemp(join(tmpdir(), "bibverify-npm-test-"));
  temporaryDirectories.push(root);
  const filename = assetName(VERSION);
  const bytes = Buffer.from("verified-bibverify-test-binary");
  const { createHash } = await import("node:crypto");
  const checksum = createHash("sha256").update(bytes).digest("hex");
  const server = createServer((request, response) => {
    if (request.url === `/v${VERSION}/SHA256SUMS`) {
      response.end(`${checksum}  ${filename}\n`);
      return;
    }
    if (request.url === `/v${VERSION}/${filename}`) {
      response.end(bytes);
      return;
    }
    response.writeHead(404).end();
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  assert.ok(address && typeof address === "object");

  process.env.BIBVERIFY_CACHE_DIR = join(root, "cache");
  process.env.BIBVERIFY_RELEASE_BASE_URL = `http://127.0.0.1:${address.port}`;
  try {
    const binary = await ensureBinary();
    assert.equal(await readFile(binary, "utf8"), bytes.toString());
    await chmod(binary, 0o755);
    await writeFile(binary, "tampered cache");
    assert.equal(await ensureBinary(), binary);
    assert.equal(await readFile(binary, "utf8"), bytes.toString());
  } finally {
    delete process.env.BIBVERIFY_CACHE_DIR;
    delete process.env.BIBVERIFY_RELEASE_BASE_URL;
    await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  }
});

test("rejects a release whose checksum does not match", async () => {
  const root = await mkdtemp(join(tmpdir(), "bibverify-npm-test-"));
  temporaryDirectories.push(root);
  const filename = assetName(VERSION);
  const server = createServer((request, response) => {
    if (request.url?.endsWith("SHA256SUMS")) {
      response.end(`${"0".repeat(64)}  ${filename}\n`);
      return;
    }
    response.end("tampered");
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  assert.ok(address && typeof address === "object");

  process.env.BIBVERIFY_CACHE_DIR = join(root, "cache");
  process.env.BIBVERIFY_RELEASE_BASE_URL = `http://127.0.0.1:${address.port}`;
  try {
    await assert.rejects(ensureBinary(), /SHA-256 mismatch/u);
  } finally {
    delete process.env.BIBVERIFY_CACHE_DIR;
    delete process.env.BIBVERIFY_RELEASE_BASE_URL;
    await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  }
});
