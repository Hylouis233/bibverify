import { spawnSync } from "node:child_process";

const TARGETS = new Map([
  ["win32:x64", { os: "windows", arch: "x64", extension: ".exe" }],
  // Windows 11 on Arm runs the published x64 executable through built-in emulation.
  ["win32:arm64", { os: "windows", arch: "x64", extension: ".exe" }],
  ["darwin:x64", { os: "macos", arch: "x64", extension: "" }],
  ["darwin:arm64", { os: "macos", arch: "arm64", extension: "" }],
  ["linux:x64", { os: "linux", arch: "x64", extension: "" }],
  ["linux:arm64", { os: "linux", arch: "arm64", extension: "" }],
]);

function detectLinuxLibc() {
  try {
    const report = process.report?.getReport?.();
    if (report?.header?.glibcVersionRuntime) return "glibc";
  } catch {
    // Fall back to ldd for runtimes such as Bun that may not implement process.report.
  }

  try {
    const result = spawnSync("ldd", ["--version"], {
      encoding: "utf8",
      windowsHide: true,
    });
    const output = `${result.stdout ?? ""}\n${result.stderr ?? ""}`.toLowerCase();
    if (output.includes("musl")) return "musl";
    if (output.includes("gnu libc") || output.includes("glibc")) return "glibc";
  } catch {
    // An unknown libc is rejected below instead of risking an incompatible download.
  }

  return "unknown";
}

export function releaseTarget(
  platform = process.platform,
  architecture = process.arch,
  libc = platform === "linux" && platform === process.platform ? detectLinuxLibc() : "glibc",
) {
  const target = TARGETS.get(`${platform}:${architecture}`);
  if (!target) {
    throw new Error(
      `unsupported platform ${platform}/${architecture}; use uvx, pipx, or the Python package instead`,
    );
  }
  if (platform === "linux" && libc !== "glibc") {
    throw new Error(
      `unsupported Linux libc ${libc}; published binaries require glibc 2.28 or newer; ` +
        "use uvx, pipx, or the Python package instead",
    );
  }
  return target;
}

export function assetName(
  version,
  platform = process.platform,
  architecture = process.arch,
  libc = undefined,
) {
  const target = releaseTarget(platform, architecture, libc);
  return `bibverify-${version}-${target.os}-${target.arch}${target.extension}`;
}
