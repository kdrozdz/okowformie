import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Vitest (natywne snapshoty, bez Jest jako drugiego test runnera) —
// `.claude/rules/conventions.md`. Alias `@/*` powielony z `tsconfig.json`
// (Vitest nie czyta `paths` z tsconfig automatycznie bez dodatkowego
// pluginu — jeden alias nie uzasadnia dokładania `vite-tsconfig-paths`
// jako zależności, `.claude/rules/engineering-principles.md` KISS).
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    css: true,
    // Wymuszone jednoznacznie, niezależnie od tego, czy testy odpalają się
    // w kontenerze `frontend` (gdzie `API_URL` jest już ustawione przez
    // docker-compose) czy gołym `npm test` na hoście (gdzie nie jest) —
    // `toOptimizableImageSrc()` (lib/media/image-src.ts) zachowuje się
    // różnie w zależności od tej zmiennej, więc bez tego snapshoty
    // PostCard/PostDetail/AboutSection łapałyby inny wynik zależnie od
    // środowiska uruchomienia i pękały na świeżym checkout (code-review).
    env: {
      API_URL: "http://backend:8000",
    },
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      // Next.js resolvuje `import "server-only"` przez alias w swoim
      // webpack configu; Vite/Vitest nie zna tego mapowania, więc bez tego
      // wpisu import modułów server-only rzuca błędem resolvera w testach
      // (patrz komentarz w `src/test/server-only-mock.ts`).
      "server-only": fileURLToPath(new URL("./src/test/server-only-mock.ts", import.meta.url)),
    },
  },
});
