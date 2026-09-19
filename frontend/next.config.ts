import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output: `next build` emits a minimal server bundle with only
  // the production node_modules it actually needs, copied into
  // `.next/standalone`. Required for the lean, non-root Docker runtime stage
  // (see frontend/Dockerfile) instead of shipping the full node_modules tree.
  output: "standalone",
};

export default nextConfig;
