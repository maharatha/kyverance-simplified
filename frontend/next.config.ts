import type { NextConfig } from "next";

/**
 * Standalone output is required by the frontend Dockerfile (Linux).
 * On Windows, Next 15 standalone file-tracing frequently fails with ENOENT
 * while copying page_client-reference-manifest.js / routes-manifest.json.
 * Skip standalone locally so `next build` / `next start` remain verifiable.
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,
  ...(process.platform === "win32" ? {} : { output: "standalone" as const }),
  experimental: {
    cpus: 1,
  },
};

export default nextConfig;
