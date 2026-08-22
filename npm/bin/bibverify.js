#!/usr/bin/env node

import { run } from "../lib/runner.js";

try {
  process.exitCode = await run(process.argv.slice(2));
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`bibverify: ${message}`);
  process.exitCode = 1;
}
