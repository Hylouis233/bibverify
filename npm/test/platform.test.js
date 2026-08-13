import assert from "node:assert/strict";
import { after, test } from "node:test";
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

test("forwards arguments and preserves the native exit code", async () => {
  process.env.BIBVERIFY_BINARY = process.execPath;
  try {
    assert.equal(await run(["-e", "process.exit(7)"]), 7);
  } finally {
    delete process.env.BIBVERIFY_BINARY;
  }
});

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
