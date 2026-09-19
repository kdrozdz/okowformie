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
      // Docker compose dev: server-side fetch to the API uses `API_URL`
      // (`http://backend:8000`, the container hostname — see
      // `frontend/src/lib/api/client.ts`), and Django builds absolute media
      // URLs from the Host header of *that* request (`request.build_absolute_uri`),
      // so API payloads contain `http://backend:8000/media/...`, not
      // `localhost:8000`. `next/image` optimization fetches remote images
      // server-side (inside this container, where "backend" resolves) and
      // serves the result to the browser via `/_next/image` — the browser
      // itself never requests `backend:8000` directly, so this does not
      // widen what's exposed publicly. Not in the original spec (which only
      // listed `localhost:8000`); added after `docker compose up` testing
      // surfaced `next/image`'s "unconfigured host" error for this exact URL.
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
    // fetch a host that resolves to a private IP (SSRF hardening) — which
    // is exactly what "backend" does inside the compose network. The
    // `backend:8000` entry above is already scoped to one exact
    // host/port/path via `remotePatterns` (not a wildcard), so this only
    // removes a *redundant* second check for a host we already explicitly
    // allow-listed; it does not widen what's publicly fetchable. Real fix
    // belongs in the backend (build absolute media URLs from a configured
    // public site URL, not the request Host header) — flagged to
    // backend-agent; this stays only as long as that isn't done.
    dangerouslyAllowLocalIP: true,
  },
};

export default nextConfig;
