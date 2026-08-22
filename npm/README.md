# `@hylouis233/bibverify`

Run the Bibverify CLI or MCP server through npm without installing Python:

```bash
npx --yes @hylouis233/bibverify --version
npx --yes @hylouis233/bibverify check references.bib
npx --yes @hylouis233/bibverify mcp
```

`pnpm dlx @hylouis233/bibverify` and `bunx --bun @hylouis233/bibverify` use the same package.

This is a zero-dependency launcher for the native binaries published by the
[Bibverify project](https://github.com/Hylouis233/bibverify). It selects the release for the
current operating system and CPU, verifies it against the release `SHA256SUMS`, caches that exact
version, and forwards all arguments and exit codes.

Published native targets are Windows x64 plus macOS and glibc 2.28+ Linux on x64/ARM64. On Windows
11 Arm, the launcher uses the Windows x64 executable through the operating system's built-in
emulation. musl-based Linux users should use the Python package or container image.

See the [complete documentation](https://github.com/Hylouis233/bibverify#readme) for configuration,
MCP client setup, output safety, and the Python API.
