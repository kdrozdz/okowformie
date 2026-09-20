import { describe, expect, it } from "vitest";

import { isActiveLink } from "./PrimaryNav";

describe("isActiveLink", () => {
  it("dokładne dopasowanie ścieżki → aktywny", () => {
    expect(isActiveLink("/pl/posty", "/pl/posty")).toBe(true);
  });

  it("dopasowanie z dodatkowym segmentem (post pod listą) → aktywny", () => {
    expect(isActiveLink("/pl/posty/jakis-slug", "/pl/posty")).toBe(true);
  });

  it("zupełny brak dopasowania → nieaktywny", () => {
    expect(isActiveLink("/pl/o-mnie", "/pl/posty")).toBe(false);
  });

  it("dopasowanie samego prefiksu znaków bez granicy segmentu → nieaktywny (bug, po który istnieją testy)", () => {
    // `/pl/postyxyz` dzieli znakowy prefiks z `/pl/posty`, ale to inny
    // segment ścieżki (inna strona), nie zagnieżdżenie pod „posty”.
    // Naiwne `pathname.startsWith(href)` (bez `/` na końcu) złapałoby to
    // jako fałszywie aktywne — właściwa implementacja wymaga granicy `/`.
    expect(isActiveLink("/pl/postyxyz", "/pl/posty")).toBe(false);
  });

  it("dopasowanie prefiksu innego linku bez granicy segmentu → nieaktywny", () => {
    expect(isActiveLink("/pl/o-mnie-firmowe", "/pl/o-mnie")).toBe(false);
  });
});
