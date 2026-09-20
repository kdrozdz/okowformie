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
