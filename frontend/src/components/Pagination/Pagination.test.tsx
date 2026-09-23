import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Pagination } from "./Pagination";

const labels = {
  previousLabel: "Poprzednia strona",
  nextLabel: "Następna strona",
  ariaLabel: "Stronicowanie",
};

describe("Pagination", () => {
  it("dopasowuje snapshot na pierwszej stronie (hasPrevious=false, hasNext=true)", () => {
    const { container } = render(
      <Pagination
        basePath="/pl/posty"
        currentPage={1}
        hasPrevious={false}
        hasNext={true}
        {...labels}
      />,
    );

    expect(container.firstChild).toMatchSnapshot();
  });

  it("dopasowuje snapshot na stronie środkowej (hasPrevious=true, hasNext=true)", () => {
    const { container } = render(
      <Pagination
        basePath="/pl/posty"
        currentPage={2}
        hasPrevious={true}
        hasNext={true}
        {...labels}
      />,
    );

    expect(container.firstChild).toMatchSnapshot();
  });

  it("dopasowuje snapshot na ostatniej stronie (hasPrevious=true, hasNext=false)", () => {
    const { container } = render(
      <Pagination
        basePath="/pl/posty"
        currentPage={3}
        hasPrevious={true}
        hasNext={false}
        {...labels}
      />,
    );

    expect(container.firstChild).toMatchSnapshot();
  });

  it("nie renderuje nic, gdy jest tylko jedna strona (hasPrevious=false, hasNext=false) — paginacja poza zakresem to stan pusty, nie pusta nawigacja", () => {
    const { container } = render(
      <Pagination
        basePath="/pl/posty"
        currentPage={1}
        hasPrevious={false}
        hasNext={false}
        {...labels}
      />,
    );

    expect(container.firstChild).toBeNull();
  });

  it("buduje href z dowolnego `basePath` (np. listy plików do pobrania), nie tylko `/posty`", () => {
    const { container } = render(
      <Pagination
        basePath="/pl/do-pobrania"
        currentPage={2}
        hasPrevious={true}
        hasNext={true}
        {...labels}
      />,
    );

    const links = container.querySelectorAll("a");
    expect(links[0]).toHaveAttribute("href", "/pl/do-pobrania?page=1");
    expect(links[1]).toHaveAttribute("href", "/pl/do-pobrania?page=3");
  });
});
