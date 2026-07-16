/**
 * Production build wrapper.
 * Disables Next.js worker threads and retries on intermittent Windows
 * PageNotFoundError / ENOENT during "Collecting page data".
 */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import path from "node:path";

const root = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(root, "..");
const nextDir = path.join(frontendRoot, ".next");

const env = {
  ...process.env,
  NEXT_DISABLE_WORKER_THREADS: "true",
  NEXT_PRIVATE_WORKER_THREADS: "false",
};

function runBuild() {
  return spawnSync("npx", ["next", "build"], {
    cwd: frontendRoot,
    env,
    stdio: "inherit",
    shell: true,
  });
}

const maxAttempts = 3;
let lastStatus = 1;
for (let attempt = 1; attempt <= maxAttempts; attempt++) {
  if (fs.existsSync(nextDir)) {
    fs.rmSync(nextDir, { recursive: true, force: true });
  }
  console.log(`\n[next-build] attempt ${attempt}/${maxAttempts}`);
  const result = runBuild();
  lastStatus = result.status ?? 1;
  if (lastStatus === 0) {
    process.exit(0);
  }
  console.warn(`[next-build] attempt ${attempt} failed with status ${lastStatus}`);
}

process.exit(lastStatus);
