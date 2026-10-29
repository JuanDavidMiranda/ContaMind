"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorText } from "@/components/notice";
import { formatDate } from "@/lib/utils";
import { api, ApiError } from "@/services/api";
import type { Reconciliation } from "@/types/api";

export function ReconciliationList() {
  const [rows, setRows] = useState<Reconciliation[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Reconciliation[]>("/api/v1/reconciliations")
      .then(setRows)
      .catch((reason: unknown) => setError(reason instanceof ApiError ? reason.message : "No fue posible cargar el historial."));
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Conciliaciones</h1>
        <Link href="/reconciliations/new">
          <Button>Nueva conciliación</Button>
        </Link>
      </div>
      {error ? <ErrorText>{error}</ErrorText> : null}
      <Card>
        <CardContent>
          {rows.length === 0 ? (
            <p className="text-sm text-slate-600">No hay conciliaciones guardadas.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="text-slate-500">
                <tr>
                  <th className="py-2 font-medium">Empresa</th>
                  <th className="py-2 font-medium">Periodo</th>
                  <th className="py-2 font-medium">Estado</th>
                  <th className="py-2 font-medium">Coincidentes</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="py-3">
                      <Link href={`/reconciliations/${row.id}`} className="font-medium text-teal-900 hover:underline">
                        {row.company_name}
                      </Link>
                    </td>
                    <td className="py-3">
                      {formatDate(row.period_start)} – {formatDate(row.period_end)}
                    </td>
                    <td className="py-3">
                      <Badge value={row.status} kind="status" />
                    </td>
                    <td className="py-3">{row.summary?.matched ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
