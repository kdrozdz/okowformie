import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output: `next build` emits a minimal server bundle with only
  // the production node_modules it actually needs, copied into
  // `.next/standalone`. Required for the lean, non-root Docker runtime stage
  // (see frontend/Dockerfile) instead of shipping the full node_modules tree.
  output: "standalone",
  images: {
    remotePatterns: [
      // Dev: Django serves `/media/**` directly on `localhost:8000` (only
      // under `DEBUG=True`, see `backend/src/backend/urls.py`). Scoped to
      // this exact host/port/path, not a wildcard, per `.claude/rules/seo.md`
      // image-security posture applied to `next.config.ts`.
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
        pathname: "/media/**",
      },
      // Prod media host depends on the still-open storage decision (S3 vs
      // VPS volume, see `CLAUDE.md` § Otwarte decyzje) — not guessed here.
      // Set `NEXT_PUBLIC_MEDIA_HOST` once that's resolved; empty/unset in
      // dev, so this entry is a no-op until then.
      ...(process.env.NEXT_PUBLIC_MEDIA_HOST
        ? [
            {
              protocol: "https" as const,
              hostname: process.env.NEXT_PUBLIC_MEDIA_HOST,
              pathname: "/media/**",
            },
          ]
        : []),
    ],
  },
};

export default nextConfig;
