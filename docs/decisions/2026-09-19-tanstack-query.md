# TanStack Query (`useQuery`) do fetchowania danych po stronie klienta

- **Decyzja:** Dla danych pobieranych z komponentów klienckich (`"use client"`) — np. wyszukiwarka postów, filtry, paginacja bez przeładowania strony — używamy TanStack Query (`useQuery`/`useMutation`), nie własnych hooków na `fetch`/`useEffect` ani globalnego state managera.
- **Kontekst:** Blog jest w większości treścią statyczną renderowaną przez RSC + SSG/ISR (`performance.md`). Część widoków (wyszukiwarka, filtrowanie listy) wymaga jednak fetchowania po stronie klienta z cache'owaniem, refetchem i stanami loading/error — ręczne `useEffect`+`fetch` prowadzi do duplikacji tej logiki w każdym komponencie.
- **Alternatywy:**
  - **Redux / Zustand** — odrzucone na razie: to state managery do stanu klienckiego (UI state, dane rozproszone po wielu niepowiązanych widokach), nie do cache'owania danych serwerowych. Blog w fazie 1 nie ma takiego stanu (brak koszyka, konta, wielokrokowych formularzy) — patrz `scope.md`. Rozważyć ponownie w fazie 2.
  - **Ręczne `useEffect`/`fetch` per komponent** — odrzucone: brak cache'owania i deduplikacji zapytań, każdy komponent odtwarza tę samą logikę stanów loading/error.

## Konwencje
- Domyślny wzorzec pozostaje RSC + fetch po stronie serwera (`performance.md`) — `useQuery` tylko tam, gdzie dane faktycznie zależą od interakcji klienta (input użytkownika, brak SSR/ISR sensu).
- Jeden `QueryClientProvider` w korzeniu drzewa klienckiego, nie per-widok.
- Query keys spójne z endpointami `/api/v1/` (`scope.md`) — nie duplikować typów odpowiedzi API osobno dla RSC i dla `useQuery`.

- **Status:** aktywna.
