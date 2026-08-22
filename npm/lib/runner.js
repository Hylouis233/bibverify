import { createHash } from "node:crypto";
import { chmod, mkdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import { constants as osConstants, homedir } from "node:os";
import { dirname, join } from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

import { assetName } from "./platform.js";

const PACKAGE_ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const PACKAGE_JSON = JSON.parse(await readFile(join(PACKAGE_ROOT, "package.json"), "utf8"));
export const VERSION = PACKAGE_JSON.version;
const DEFAULT_RELEASE_BASE = "https://github.com/Hylouis233/bibverify/releases/download";

function cacheRoot() {
  if (process.env.BIBVERIFY_CACHE_DIR) return process.env.BIBVERIFY_CACHE_DIR;
  if (process.platform === "win32") {
    return join(process.env.LOCALAPPDATA || join(homedir(), "AppData", "Local"), "bibverify");
  }
  if (process.platform === "darwin") return join(homedir(), "Library", "Caches", "bibverify");
  return join(process.env.XDG_CACHE_HOME || join(homedir(), ".cache"), "bibverify");
}

async function fetchBytes(url) {
  const response = await fetch(url, { redirect: "follow" });
  if (!response.ok) throw new Error(`download failed (${response.status}) for ${url}`);
  return Buffer.from(await response.arrayBuffer());
}

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function expectedHash(checksums, filename) {
  for (const line of checksums.split(/\r?\n/u)) {
    const match = line.trim().match(/^([a-fA-F0-9]{64})\s+\*?(.+)$/u);
    if (match && match[2] === filename) return match[1].toLowerCase();
  }
  throw new Error(`${filename} is missing from SHA256SUMS`);
}

export async function ensureBinary() {
  if (process.env.BIBVERIFY_BINARY) return process.env.BIBVERIFY_BINARY;

  const filename = assetName(VERSION);
  const destination = join(cacheRoot(), VERSION, filename);
  const checksumPath = `${destination}.sha256`;
  try {
    const [cached, cachedChecksum] = await Promise.all([
      readFile(destination),
      readFile(checksumPath, "utf8"),
    ]);
    if (sha256(cached) === cachedChecksum.trim().toLowerCase()) {
      await chmod(destination, 0o755);
      return destination;
    }
    await Promise.all([rm(destination, { force: true }), rm(checksumPath, { force: true })]);
  } catch {
    // Download below when this exact version is not already cached.
  }

  const releaseBase = process.env.BIBVERIFY_RELEASE_BASE_URL || DEFAULT_RELEASE_BASE;
  const versionBase = `${releaseBase.replace(/\/$/u, "")}/v${VERSION}`;
  const [checksums, bytes] = await Promise.all([
    fetch(`${versionBase}/SHA256SUMS`, { redirect: "follow" }).then(async (response) => {
      if (!response.ok) throw new Error(`could not download SHA256SUMS (${response.status})`);
      return response.text();
    }),
    fetchBytes(`${versionBase}/${filename}`),
  ]);

  const actual = sha256(bytes);
  const expected = expectedHash(checksums, filename);
  if (actual !== expected) {
    throw new Error(`SHA-256 mismatch for ${filename}: expected ${expected}, received ${actual}`);
  }

  await mkdir(dirname(destination), { recursive: true });
  const temporary = `${destination}.${process.pid}.${Date.now()}.tmp`;
  await writeFile(temporary, bytes, { mode: 0o755 });
  try {
    await rename(temporary, destination);
  } catch (error) {
    await rm(temporary, { force: true });
    try {
      const concurrentDownload = await readFile(destination);
      if (sha256(concurrentDownload) !== expected) throw error;
      await chmod(destination, 0o755);
    } catch {
      throw error;
    }
  }
  await chmod(destination, 0o755);
  await writeFile(checksumPath, `${expected}\n`, { mode: 0o600 });
  return destination;
}

export async function run(args) {
  const executable = await ensureBinary();
  const child = spawn(executable, args, { stdio: "inherit", windowsHide: true });
  const signals = process.platform === "win32" ? ["SIGINT", "SIGTERM"] : ["SIGHUP", "SIGINT", "SIGTERM"];

  return new Promise((resolve, reject) => {
    const handlers = new Map();
    const cleanup = () => {
      for (const [signal, handler] of handlers) process.removeListener(signal, handler);
    };

    for (const signal of signals) {
      const handler = () => {
        if (child.exitCode !== null || child.signalCode !== null) return;
        try {
          child.kill(signal);
        } catch {
          try {
            child.kill();
          } catch {
            // The child may have exited between the state check and signal delivery.
          }
        }
      };
      handlers.set(signal, handler);
      process.on(signal, handler);
    }

    child.once("error", (error) => {
      cleanup();
      reject(error);
    });
    child.once("close", (status, signal) => {
      cleanup();
      if (signal) {
        const signalNumber = osConstants.signals[signal];
        resolve(typeof signalNumber === "number" ? 128 + signalNumber : 1);
        return;
      }
      resolve(status ?? 1);
    });
  });
}
