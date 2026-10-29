"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { ErrorText, Notice } from "@/components/notice";
import { CATEGORIES, FIELD_LABELS, FIELD_OPTIONS, type FieldKey } from "@/lib/categories";
import { formatDate } from "@/lib/utils";
import { api, ApiError, downloadReport } from "@/services/api";
import type { ColumnsPreview, Reconciliation, ReconciliationResult, ResultPage, SourcePreview } from "@/types/api";

const emptyMapping = (): Record<FieldKey, string> => ({
  document_number: "",
  third_party_id: "",
  issue_date: "",
  base_amount: "",
  tax_amount: "",
  total_amount: "",
});

export function ReconciliationWorkspace({ reconciliationId }: { reconciliationId: string }) {
  const [record, setRecord] = useState<Reconciliation | null>(null);
  const [preview, setPreview] = useState<ColumnsPreview | null>(null);
  const [erpMapping, setErpMapping] = useState(emptyMapping());
  const [dianMapping, setDianMapping] = useState(emptyMapping());
  const [results, setResults] = useState<ResultPage | null>(null);
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadRecord = useCallback(async () => {
    const next = await api<Reconciliation>(`/api/v1/reconciliations/${reconciliationId}`);
    setRecord(next);
    if (next.files.length > 0) {
      const columns = await api<ColumnsPreview>(`/api/v1/reconciliations/${reconciliationId}/columns`);
      setPreview(columns);
      setErpMapping(mappingFrom(next.erp_mapping, columns.erp));
      setDianMapping(mappingFrom(next.dian_mapping, columns.dian));
    }
    if (next.status === "completed") {
      const page = await api<ResultPage>(`/api/v1/reconciliations/${reconciliationId}/results?page=1&page_size=50`);
      setResults(page);
    }
  }, [reconciliationId]);

  useEffect(() => {
    loadRecord().catch((reason: unknown) => setError(messageOf(reason)));
  }, [loadRecord]);

  async function confirmMapping(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(`/api/v1/reconciliations/${reconciliationId}/mapping`, {
        method: "PUT",
        body: JSON.stringify({ erp: payload(erpMapping), dian: payload(dianMapping) }),
      });
      await loadRecord();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  }

  async function run() {
    setBusy(true);
    setError(null);
    try {
      await api(`/api/v1/reconciliations/${reconciliationId}/run`, { method: "POST" });
      await loadRecord();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  }

  async function search(event: FormEvent) {
    event.preventDefault();
    const params = new URLSearchParams({ page: "1", page_size: "50" });
    if (category) params.set("category", category);
    if (query) params.set("q", query);
    try {
      setResults(await api<ResultPage>(`/api/v1/reconciliations/${reconciliationId}/results?${params}`));
    } catch (reason) {
      setError(messageOf(reason));
    }
  }

  if (!record && !error) return <p className="text-sm text-slate-600">Cargando conciliación...</p>;
  if (!record) return <ErrorText>{error}</ErrorText>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-slate-500">{record.company_name}</p>
          <h1 className="text-2xl font-semibold text-slate-900">
            {formatDate(record.period_start)} – {formatDate(record.period_end)}
          </h1>
        </div>
        <Badge value={record.status} kind="status" />
      </div>
      {error ? <ErrorText>{error}</ErrorText> : null}
      <div className="grid gap-4 md:grid-cols-2">
        <SourceCard title="Archivo del ERP" file={record.files.find((item) => item.source === "erp")} />
        <SourceCard title="Archivo de la DIAN" file={record.files.find((item) => item.source === "dian")} />
      </div>
      {preview?.erp && preview.dian ? (
        <Card>
          <CardHeader>
            <CardTitle>Asignación de columnas</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={confirmMapping}>
              <p className="text-sm text-slate-600">
                Las sugerencias salen del nombre de cada columna. Confírmalas o corrígelas. Si un campo no existe en
                alguna fuente, déjalo sin asignar y la comparación de ese campo no se ejecutará.
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-slate-500">
                    <tr>
                      <th className="py-2 font-medium">Campo</th>
                      <th className="py-2 font-medium">Columna ERP</th>
                      <th className="py-2 font-medium">Columna DIAN</th>
                    </tr>
                  </thead>
                  <tbody>
                    {FIELD_OPTIONS.map((field) => (
                      <tr key={field.key} className="border-t border-slate-100">
                        <td className="py-2 pr-3">
                          {field.label}
                          {field.required ? " *" : ""}
                        </td>
                        <td className="py-2 pr-3">
                          <ColumnSelect headers={preview.erp?.headers ?? []} value={erpMapping[field.key]} required={field.required} onChange={(value) => setErpMapping({ ...erpMapping, [field.key]: value })} />
                        </td>
                        <td className="py-2">
                          <ColumnSelect headers={preview.dian?.headers ?? []} value={dianMapping[field.key]} required={field.required} onChange={(value) => setDianMapping({ ...dianMapping, [field.key]: value })} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex flex-wrap gap-3">
                <Button type="submit" disabled={busy}>
                  {busy ? "Guardando..." : "Confirmar columnas"}
                </Button>
                <Button type="button" variant="secondary" disabled={busy || record.status === "draft" || record.status === "files_uploaded"} onClick={run}>
                  {busy ? "Procesando..." : "Ejecutar conciliación"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}
      {record.summary ? <SummaryPanel record={record} onDownload={() => downloadReport(record.id).catch((reason) => setError(messageOf(reason)))} /> : null}
      {record.status === "completed" ? (
        <Card>
          <CardHeader>
            <CardTitle>Resultados</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Notice>
              La categoría principal es una sola por documento. Las señales de valor, fecha, identificación y duplicado
              pueden aparecer juntas. Ninguna cifra de esta tabla es un error contable confirmado.
            </Notice>
            <form className="flex flex-wrap gap-3" onSubmit={search}>
              <Select value={category} onChange={(event) => setCategory(event.target.value)} className="max-w-xs">
                {CATEGORIES.map((item) => (
                  <option key={item.id || "all"} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </Select>
              <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar número de documento" className="max-w-xs" />
              <Button type="submit" variant="outline">
                Filtrar
              </Button>
            </form>
            {!results || results.total === 0 ? (
              <p className="text-sm text-slate-600">No hay resultados para este filtro.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-slate-500">
                    <tr>
                      <th className="py-2 font-medium">Documento</th>
                      <th className="py-2 font-medium">Categoría</th>
                      <th className="py-2 font-medium">Señales</th>
                      <th className="py-2 font-medium">Total ERP</th>
                      <th className="py-2 font-medium">Total DIAN</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.items.map((item) => (
                      <ResultRow key={item.id} reconciliationId={reconciliationId} item={item} />
                    ))}
                  </tbody>
                </table>
                <p className="mt-3 text-xs text-slate-500">
                  {results.total} {results.total === 1 ? "documento" : "documentos"} en este filtro.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}
      {record.rules?.skipped_fields?.length ? (
        <Card>
          <CardHeader>
            <CardTitle>Comparaciones no ejecutadas</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-slate-700">
              {record.rules.skipped_fields.map((item) => (
                <li key={item.field}>
                  <span className="font-medium">{FIELD_LABELS[item.field as FieldKey] ?? item.field}:</span> {item.reason}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function ResultRow({ reconciliationId, item }: { reconciliationId: string; item: ReconciliationResult }) {
  return (
    <tr className="border-t border-slate-100">
      <td className="py-3">
        <Link href={`/reconciliations/${reconciliationId}/results/${item.id}`} className="font-medium text-teal-900 hover:underline">
          {item.document_key}
        </Link>
      </td>
      <td className="py-3">
        <Badge value={item.primary_category} />
      </td>
      <td className="py-3 text-slate-600">{item.flags.length ? item.flags.join(", ") : "—"}</td>
      <td className="py-3">{item.erp_normalized?.total_amount ?? "—"}</td>
      <td className="py-3">{item.dian_normalized?.total_amount ?? "—"}</td>
    </tr>
  );
}

function SummaryPanel({ record, onDownload }: { record: Reconciliation; onDownload: () => void }) {
  const summary = record.summary;
  if (!summary) return null;
  const cards = [
    ["Registros ERP", summary.erp_rows_read],
    ["Registros DIAN", summary.dian_rows_read],
    ["Coincidentes", summary.matched],
    ["Ausentes en la DIAN", summary.missing_in_dian],
    ["Ausentes en el ERP", summary.missing_in_erp],
    ["Diferencias de valores", summary.value_mismatch_flags],
    ["Diferencias de fecha", summary.date_mismatch_flags],
    ["Diferencias de identificación", summary.third_party_mismatch_flags],
    ["Posibles duplicados", summary.duplicate_groups],
    ["Requieren revisión", summary.requires_review],
    ["Errores de procesamiento", summary.processing_errors],
  ];
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Resumen de la ejecución</CardTitle>
        <Button variant="outline" onClick={onDownload}>
          Descargar Excel
        </Button>
      </CardHeader>
      <CardContent>
        {record.rules?.disclaimer ? <Notice>{record.rules.disclaimer}</Notice> : null}
        {record.review_progress ? (
          <p className="mt-4 text-sm text-slate-700">Avance de revisión manual: {record.review_progress.progress_label}</p>
        ) : null}
        <div className="mt-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {cards.map(([label, value]) => (
            <div key={String(label)} className="rounded-md bg-slate-50 px-3 py-3">
              <p className="text-xs text-slate-500">{label}</p>
              <p className="text-2xl font-semibold text-slate-900">{value}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function SourceCard({ title, file }: { title: string; file?: { original_filename: string; row_count: number; warnings: string[] } }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-slate-700">
        {file ? (
          <>
            <p>{file.original_filename}</p>
            <p className="text-slate-500">{file.row_count} filas leídas</p>
            {file.warnings.map((warning) => (
              <p key={warning} className="mt-2 text-amber-800">
                {warning}
              </p>
            ))}
          </>
        ) : (
          <p>Este archivo todavía no se ha cargado.</p>
        )}
      </CardContent>
    </Card>
  );
}

function ColumnSelect({
  headers,
  value,
  required,
  onChange,
}: {
  headers: string[];
  value: string;
  required: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <Select value={value} required={required} onChange={(event) => onChange(event.target.value)}>
      {!required ? <option value="">No comparar</option> : null}
      {headers.map((header) => (
        <option key={header} value={header}>
          {header}
        </option>
      ))}
    </Select>
  );
}

function mappingFrom(saved: Reconciliation["erp_mapping"], preview: SourcePreview | null): Record<FieldKey, string> {
  const next = emptyMapping();
  for (const field of FIELD_OPTIONS) {
    const savedColumn = saved?.[field.key];
    const suggested = preview?.suggestions[field.key]?.column;
    next[field.key] = savedColumn || suggested || "";
  }
  return next;
}

function payload(mapping: Record<FieldKey, string>) {
  return Object.fromEntries(FIELD_OPTIONS.map((field) => [field.key, mapping[field.key] || null]));
}

function messageOf(reason: unknown): string {
  return reason instanceof ApiError ? reason.message : "No fue posible completar la operación.";
}
