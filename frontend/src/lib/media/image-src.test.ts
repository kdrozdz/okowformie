import { afterEach, describe, expect, it, vi } from "vitest";

import { toOptimizableImageSrc } from "./image-src";

describe("toOptimizableImageSrc", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("bez API_URL zwraca URL bez zmian (no-op poza Dockerem)", () => {
    vi.stubEnv("API_URL", "");

    const result = toOptimizableImageSrc("http://localhost:8000/media/zdjecie.jpg");

    expect(result).toBe("http://localhost:8000/media/zdjecie.jpg");
  });

  it("przepisuje protokół i host na API_URL, zachowując ścieżkę", () => {
    vi.stubEnv("API_URL", "http://backend:8000");

    const result = toOptimizableImageSrc("http://localhost:8000/media/zdjecie.jpg");

    expect(result).toBe("http://backend:8000/media/zdjecie.jpg");
  });

  it("zachowuje query string wejściowego URL-a", () => {
    vi.stubEnv("API_URL", "http://backend:8000");

    const result = toOptimizableImageSrc("http://localhost:8000/media/zdjecie.jpg?v=2");

    expect(result).toBe("http://backend:8000/media/zdjecie.jpg?v=2");
  });

  it("przy niepoprawnym URL-u wejściowym zwraca go bez zmian zamiast rzucać", () => {
    vi.stubEnv("API_URL", "http://backend:8000");

    const result = toOptimizableImageSrc("nie-jest-to-url");

    expect(result).toBe("nie-jest-to-url");
  });

  it("przy niepoprawnym API_URL zwraca oryginalny URL bez zmian zamiast rzucać", () => {
    vi.stubEnv("API_URL", "nie-jest-to-url");

    const result = toOptimizableImageSrc("http://localhost:8000/media/zdjecie.jpg");

    expect(result).toBe("http://localhost:8000/media/zdjecie.jpg");
  });
});
