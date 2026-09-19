/**
 * Języki obsługiwane przez frontend.
 *
 * Świadoma duplikacja z `core.constants.Language` w backendzie
 * (`.claude/rules/scope.md` — granica domenowa dotyczy też frontend/backend,
 * frontend nie importuje kodu backendu). Zmiana zestawu języków wymaga
 * ręcznej synchronizacji obu miejsc.
 */
export const SUPPORTED_LANGUAGES = ["pl", "en"] as const;

export type Language = (typeof SUPPORTED_LANGUAGES)[number];

export function isSupportedLanguage(value: string): value is Language {
  return (SUPPORTED_LANGUAGES as readonly string[]).includes(value);
}
