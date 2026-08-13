const TARGETS = new Map([
  ["win32:x64", { os: "windows", arch: "x64", extension: ".exe" }],
  ["win32:arm64", { os: "windows", arch: "arm64", extension: ".exe" }],
  ["darwin:x64", { os: "macos", arch: "x64", extension: "" }],
  ["darwin:arm64", { os: "macos", arch: "arm64", extension: "" }],
  ["linux:x64", { os: "linux", arch: "x64", extension: "" }],
  ["linux:arm64", { os: "linux", arch: "arm64", extension: "" }],
]);

export function releaseTarget(platform = process.platform, architecture = process.arch) {
  const target = TARGETS.get(`${platform}:${architecture}`);
  if (!target) {
    throw new Error(
      `unsupported platform ${platform}/${architecture}; use uvx, pipx, or the Python package instead`,
    );
  }
  return target;
}

export function assetName(version, platform = process.platform, architecture = process.arch) {
  const target = releaseTarget(platform, architecture);
  return `bibverify-${version}-${target.os}-${target.arch}${target.extension}`;
}
