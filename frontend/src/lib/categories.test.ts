import { describe, expect, it } from "vitest";
import { categoryLabel, statusLabel } from "./categories";

describe("etiquetas de conciliación", () => {
  it("traduce las categorías sin presentarlas como errores confirmados", () => {
    expect(categoryLabel("VALUE_MISMATCH")).toBe("Diferencias de valores");
    expect(categoryLabel("REQUIRES_REVIEW")).toBe("Requieren revisión");
    expect(categoryLabel("DESCONOCIDA")).toBe("DESCONOCIDA");
  });

  it("traduce el estado de la ejecución", () => {
    expect(statusLabel("completed")).toBe("Terminada");
    expect(statusLabel("failed")).toBe("Con error");
  });
});
