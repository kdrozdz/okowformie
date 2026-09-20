import { renderHook, act } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useCertificatesLightbox } from "./useCertificatesLightbox";

describe("useCertificatesLightbox", () => {
  it("zaczyna zamknięty (lightboxIndex === null)", () => {
    const { result } = renderHook(() => useCertificatesLightbox(3));

    expect(result.current.isOpen).toBe(false);
    expect(result.current.lightboxIndex).toBeNull();
  });

  it("open(index) otwiera lightbox na podanym indeksie", () => {
    const { result } = renderHook(() => useCertificatesLightbox(3));

    act(() => result.current.open(1));

    expect(result.current.isOpen).toBe(true);
    expect(result.current.lightboxIndex).toBe(1);
  });

  it("ignoruje open() z indeksem poza zakresem (ujemny lub >= count)", () => {
    const { result } = renderHook(() => useCertificatesLightbox(3));

    act(() => result.current.open(-1));
    expect(result.current.isOpen).toBe(false);

    act(() => result.current.open(3));
    expect(result.current.isOpen).toBe(false);
  });

  it("close() zamyka lightbox niezależnie od aktualnego indeksu", () => {
    const { result } = renderHook(() => useCertificatesLightbox(3));

    act(() => result.current.open(2));
    act(() => result.current.close());

    expect(result.current.isOpen).toBe(false);
    expect(result.current.lightboxIndex).toBeNull();
  });

  it("showNext() przesuwa się o jeden indeks do przodu", () => {
    const { result } = renderHook(() => useCertificatesLightbox(3));

    act(() => result.current.open(0));
    act(() => result.current.showNext());

    expect(result.current.lightboxIndex).toBe(1);
  });

  it("showNext() zawija się z ostatniego elementu na pierwszy", () => {
    const { result } = renderHook(() => useCertificatesLightbox(3));

    act(() => result.current.open(2));
    act(() => result.current.showNext());

    expect(result.current.lightboxIndex).toBe(0);
  });

  it("showPrev() przesuwa się o jeden indeks do tyłu", () => {
    const { result } = renderHook(() => useCertificatesLightbox(3));

    act(() => result.current.open(1));
    act(() => result.current.showPrev());

    expect(result.current.lightboxIndex).toBe(0);
  });

  it("showPrev() zawija się z pierwszego elementu na ostatni", () => {
    const { result } = renderHook(() => useCertificatesLightbox(3));

    act(() => result.current.open(0));
    act(() => result.current.showPrev());

    expect(result.current.lightboxIndex).toBe(2);
  });

  it("showNext()/showPrev() są no-opami, gdy lightbox jest zamknięty", () => {
    const { result } = renderHook(() => useCertificatesLightbox(3));

    act(() => result.current.showNext());
    expect(result.current.lightboxIndex).toBeNull();

    act(() => result.current.showPrev());
    expect(result.current.lightboxIndex).toBeNull();
  });

  it("showNext()/showPrev() są no-opami, gdy count === 0", () => {
    const { result } = renderHook(() => useCertificatesLightbox(0));

    act(() => result.current.open(0));
    expect(result.current.isOpen).toBe(false);

    act(() => result.current.showNext());
    act(() => result.current.showPrev());
    expect(result.current.lightboxIndex).toBeNull();
  });
});
