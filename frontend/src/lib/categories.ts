export const CATEGORIES = [
  { id: "", label: "Todas las categorías" },
  { id: "MATCHED", label: "Coincidentes" },
  { id: "MISSING_IN_DIAN", label: "Ausentes en la DIAN" },
  { id: "MISSING_IN_ERP", label: "Ausentes en el ERP" },
  { id: "VALUE_MISMATCH", label: "Diferencias de valores" },
  { id: "DATE_MISMATCH", label: "Diferencias de fecha" },
  { id: "THIRD_PARTY_MISMATCH", label: "Diferencias de identificación" },
  { id: "POSSIBLE_DUPLICATE", label: "Posibles duplicados" },
  { id: "REQUIRES_REVIEW", label: "Requieren revisión" },
] as const;

const LABELS: Record<string, string> = Object.fromEntries(
  CATEGORIES.filter((item) => item.id).map((item) => [item.id, item.label]),
);

export function categoryLabel(category: string): string {
  return LABELS[category] ?? category;
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: "Borrador",
    files_uploaded: "Archivos cargados",
    mapping_confirmed: "Columnas confirmadas",
    running: "En ejecución",
    completed: "Terminada",
    failed: "Con error",
  };
  return labels[status] ?? status;
}

export const FIELD_OPTIONS = [
  { key: "document_number", label: "Número de factura o documento", required: true },
  { key: "third_party_id", label: "Identificación del emisor o tercero", required: false },
  { key: "issue_date", label: "Fecha de emisión", required: false },
  { key: "base_amount", label: "Base o subtotal", required: false },
  { key: "tax_amount", label: "IVA", required: false },
  { key: "total_amount", label: "Total del documento", required: false },
] as const;

export type FieldKey = (typeof FIELD_OPTIONS)[number]["key"];

export const FIELD_LABELS: Record<FieldKey, string> = {
  document_number: "Número de documento",
  third_party_id: "Identificación",
  issue_date: "Fecha",
  base_amount: "Base",
  tax_amount: "IVA",
  total_amount: "Total",
};
