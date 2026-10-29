"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorText, Notice } from "@/components/notice";
import { FIELD_LABELS, type FieldKey } from "@/lib/categories";
import { api, ApiError } from "@/services/api";
import type { Candidate, ReconciliationResult } from "@/types/api";

export function ResultDetail({ reconciliationId, resultId }: { reconciliationId: string; resultId: string }) {
  const [result, setResult] = useState<ReconciliationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<ReconciliationResult>(`/api/v1/reconciliations/${reconciliationId}/results/${resultId}`)
      .then(setResult)
      .catch((reason: unknown) => setError(reason instanceof ApiError ? reason.message : "No fue posible cargar el detalle."));
  }, [reconciliationId, resultId]);

  if (error) return <ErrorText>{error}</ErrorText>;
  if (!result) return <p className="text-sm text-slate-600">Cargando detalle...</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link href={`/reconciliations/${reconciliationId}`} className="text-sm text-teal-800 hover:underline">
          Volver a la conciliación
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">{result.document_key}</h1>
        <div className="mt-2 flex flex-wrap gap-2">
          <Badge value={result.primary_category} />
          {result.flags.map((flag) => (
            <Badge key={flag} value={flag} />
          ))}
        </div>
      </div>
      <Notice>{result.messages.join(" ")}</Notice>
      <Card>
        <CardHeader>
          <CardTitle>Diferencias por campo</CardTitle>
        </CardHeader>
        <CardContent>
          {result.differences.length === 0 ? (
            <p className="text-sm text-slate-600">No hay diferencias de campo calculadas para este documento.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="text-slate-500">
                <tr>
                  <th className="py-2 font-medium">Campo</th>
                  <th className="py-2 font-medium">Original ERP</th>
                  <th className="py-2 font-medium">Original DIAN</th>
                  <th className="py-2 font-medium">Normalizado ERP</th>
                  <th className="py-2 font-medium">Normalizado DIAN</th>
                  <th className="py-2 font-medium">Diferencia</th>
                </tr>
              </thead>
              <tbody>
                {result.differences.map((difference) => (
                  <tr key={difference.field} className="border-t border-slate-100">
                    <td className="py-2">{FIELD_LABELS[difference.field] ?? difference.field}</td>
                    <td className="py-2">{difference.erp_original ?? "—"}</td>
                    <td className="py-2">{difference.dian_original ?? "—"}</td>
                    <td className="py-2">{difference.erp_normalized ?? "—"}</td>
                    <td className="py-2">{difference.dian_normalized ?? "—"}</td>
                    <td className="py-2">{difference.delta ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
      <div className="grid gap-4 md:grid-cols-2">
        <Candidates title="Registros del ERP" rows={result.erp_candidates} />
        <Candidates title="Registros de la DIAN" rows={result.dian_candidates} />
      </div>
      {result.validation_errors && result.validation_errors.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Observaciones de validación</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {result.validation_errors.flatMap((errorRow) =>
                errorRow.issues.map((issue) => (
                  <li key={`${errorRow.source}-${errorRow.row_number}-${issue.message}`}>
                    {errorRow.source.toUpperCase()}, fila {errorRow.row_number}: {issue.message}
                  </li>
                )),
              )}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function Candidates({ title, rows }: { title: string; rows: Candidate[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {rows.length === 0 ? <p className="text-slate-600">No hay registros de esta fuente.</p> : null}
        {rows.map((row) => (
          <div key={row.row_number} className="rounded-md bg-slate-50 p-3">
            <p className="font-medium text-slate-800">Fila {row.row_number}</p>
            {Object.entries(row.normalized).map(([field, value]) => (
              <p key={field} className="text-slate-600">
                {FIELD_LABELS[field as FieldKey] ?? field}: {value ?? "vacío"}
                {row.original[field] && row.original[field] !== value ? ` (original: ${row.original[field]})` : ""}
              </p>
            ))}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
