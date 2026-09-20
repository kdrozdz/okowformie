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
      // Docker compose dev: `lib/media/image-src.ts` rewrites the API's
      // public `SITE_URL`-based image URLs (unreachable from inside this
      // container — "localhost" there is the frontend container itself) to
      // `API_URL`'s host (`backend`, the container-reachable service name)
      // before they ever reach `<Image src>`. Needed here so next/image's
      // optimization fetch is allowed to follow that rewritten URL.
      {
        protocol: "http",
        hostname: "backend",
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
    // Next.js 16 refuses, by default, to let the image-optimization proxy
    // fetch a host that resolves to a private/loopback IP (SSRF hardening) —
    // "localhost" resolves to 127.0.0.1, which falls under that block. This
    // is inherent to using `localhost:8000` as the dev media host above, not
    // tied to any particular workaround; `remotePatterns` already scopes the
    // allow-list to one exact host/port/path (not a wildcard), so this only
    // permits fetching a host we've explicitly allow-listed anyway.
    dangerouslyAllowLocalIP: true,
  },
};

export default nextConfig;
