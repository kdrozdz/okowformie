import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

import "@testing-library/jest-dom/vitest";

// `test.globals` jest wyłączone (celowo — jawne importy `describe`/`it`/
// `expect` z `vitest`, nie globalne magiczne zmienne), więc Testing
// Library nie rejestruje automatycznego `cleanup()` po każdym teście.
// Bez tego DOM z poprzedniego testu w tym samym pliku zostaje
// zamontowany obok kolejnego renderu — duplikaty elementów psują
// `getByRole`/`getByText` w kolejnych testach.
afterEach(() => {
  cleanup();
});
