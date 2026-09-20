import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { afterEach, describe, expect, it, vi } from "vitest";

import { getBranding } from "@/lib/api/client";
import type { Branding } from "@/lib/api/types";

import Icon from "./icon";

// Konwencja repo: `Header.test.tsx`/`Footer.test.tsx` mockują `next/image`
// przez `vi.mock`; tu analogicznie mockujemy `@/lib/api/client`, żeby test
// nie zależał od realnego backendu — `Icon()` jest server-side (route
// function), więc testujemy bezpośrednio jej wynik (`Response`), nie render.
vi.mock("@/lib/api/client", () => ({
  getBranding: vi.fn(),
}));

const fullBranding: Branding = {
  logo: "http://backend:8000/media/branding/logo/abc123.png",
  social_links: [],
};

// Ten sam statyczny plik, do którego spada fallback w `icon.tsx` — realny
// plik na dysku (nie mockowany `readFile`) jest najprostszym sposobem
// zweryfikowania, że fallback-response ma niepustą, poprawną treść.
async function readFallbackLogo(): Promise<Buffer> {
  return readFile(join(process.cwd(), "public/brand/logo.png"));
}

describe("Icon (app/icon.tsx)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("branding z logo, drugi fetch `ok: true` → bajty i Content-Type z odpowiedzi fetcha", async () => {
    vi.mocked(getBranding).mockResolvedValue(fullBranding);
    const bytes = new Uint8Array([1, 2, 3, 4]);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(bytes, {
          status: 200,
          headers: { "Content-Type": "image/webp" },
        }),
      ),
    );

    const response = await Icon();

    expect(response.headers.get("Content-Type")).toBe("image/webp");
    const body = new Uint8Array(await response.arrayBuffer());
    expect(body).toEqual(bytes);
  });

  it("branding.logo === null → fallback na statyczny plik", async () => {
    vi.mocked(getBranding).mockResolvedValue({ logo: null, social_links: [] });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await Icon();

    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.headers.get("Content-Type")).toBe("image/png");
    const body = new Uint8Array(await response.arrayBuffer());
    const fallback = await readFallbackLogo();
    expect(body).toEqual(new Uint8Array(fallback));
  });

  it("`getBranding()` rzuca wyjątek → fallback + `console.error` wywołany", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.mocked(getBranding).mockRejectedValue(new Error("Backend nieosiągalny"));

    const response = await Icon();

    expect(consoleError).toHaveBeenCalledTimes(1);
    const body = new Uint8Array(await response.arrayBuffer());
    const fallback = await readFallbackLogo();
    expect(body).toEqual(new Uint8Array(fallback));
  });

  it("drugi fetch zwraca `!response.ok` → fallback", async () => {
    vi.mocked(getBranding).mockResolvedValue(fullBranding);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 404 })));

    const response = await Icon();

    const body = new Uint8Array(await response.arrayBuffer());
    const fallback = await readFallbackLogo();
    expect(body).toEqual(new Uint8Array(fallback));
  });

  it("drugi fetch rzuca wyjątek (błąd sieci) → fallback + `console.error` wywołany", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.mocked(getBranding).mockResolvedValue(fullBranding);
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Błąd sieci")));

    const response = await Icon();

    expect(consoleError).toHaveBeenCalledTimes(1);
    const body = new Uint8Array(await response.arrayBuffer());
    const fallback = await readFallbackLogo();
    expect(body).toEqual(new Uint8Array(fallback));
  });
});
