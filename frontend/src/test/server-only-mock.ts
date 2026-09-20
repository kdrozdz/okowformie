// Stub dla `import "server-only"` pod Vitest. Next.js resolvuje ten
// specifier na własny wewnętrzny marker package przez alias w swoim
// webpack configu (poza zasięgiem Vite/Vitest) — bez tego aliasu import
// modułu server-only (np. `lib/api/client.ts`, `lib/media/image-src.ts`)
// rzuca w testach błędem resolvera zamiast dać się przetestować logikę,
// która nie ma nic wspólnego z granicą client/server.
export {};
