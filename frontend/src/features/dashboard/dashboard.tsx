"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ErrorText, Notice } from "@/components/notice";
import { formatDate } from "@/lib/utils";
import { api, ApiError } from "@/services/api";
import type { Company, Reconciliation } from "@/types/api";

export function Dashboard() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [reconciliations, setReconciliations] = useState<Reconciliation[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api<Company[]>("/api/v1/companies"), api<Reconciliation[]>("/api/v1/reconciliations")])
      .then(([companyRows, reconciliationRows]) => {
        setCompanies(companyRows);
        setReconciliations(reconciliationRows);
      })
      .catch((reason: unknown) => setError(reason instanceof ApiError ? reason.message : "No fue posible cargar el inicio."));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Inicio</h1>
          <p className="mt-1 text-sm text-slate-600">
            Compara las ventas del ERP con la información de facturación electrónica y revisa las discrepancias.
          </p>
        </div>
        <Link href="/reconciliations/new">
          <Button>Nueva conciliación</Button>
        </Link>
      </div>
      <Notice>
        Esta versión usa un usuario local de desarrollo y no está apta para producción. Una diferencia es una
        discrepancia para revisión; el sistema no confirma un incumplimiento tributario ni corrige la contabilidad.
      </Notice>
      {error ? <ErrorText>{error}</ErrorText> : null}
      <div className="grid gap-4 sm:grid-cols-3">
        <Metric title="Empresas" value={companies.length} />
        <Metric title="Conciliaciones" value={reconciliations.length} />
        <Metric title="Terminadas" value={reconciliations.filter((item) => item.status === "completed").length} />
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Conciliaciones recientes</CardTitle>
        </CardHeader>
        <CardContent>
          {reconciliations.length === 0 ? (
            <p className="text-sm text-slate-600">Todavía no hay conciliaciones guardadas.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {reconciliations.slice(0, 6).map((item) => (
                <li key={item.id} className="flex items-center justify-between gap-3 py-3 text-sm">
                  <div>
                    <Link href={`/reconciliations/${item.id}`} className="font-medium text-teal-900 hover:underline">
                      {item.company_name}
                    </Link>
                    <p className="text-slate-500">
                      {formatDate(item.period_start)} – {formatDate(item.period_end)}
                    </p>
                  </div>
                  <Badge value={item.status} kind="status" />
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ title, value }: { title: string; value: number }) {
  return (
    <Card>
      <CardContent className="py-5">
        <p className="text-sm text-slate-500">{title}</p>
        <p className="mt-1 text-3xl font-semibold text-slate-900">{value}</p>
      </CardContent>
    </Card>
  );
}
