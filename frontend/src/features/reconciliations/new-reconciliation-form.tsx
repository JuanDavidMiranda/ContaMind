"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/input";
import { ErrorText, Notice } from "@/components/notice";
import { api, ApiError } from "@/services/api";
import type { Company, Reconciliation } from "@/types/api";

export function NewReconciliationForm() {
  const router = useRouter();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyId, setCompanyId] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [tolerance, setTolerance] = useState("0");
  const [erp, setErp] = useState<File | null>(null);
  const [dian, setDian] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api<Company[]>("/api/v1/companies")
      .then((rows) => {
        setCompanies(rows.filter((company) => company.status === "active"));
        if (rows[0]) setCompanyId(rows[0].id);
      })
      .catch((reason: unknown) => setError(reason instanceof ApiError ? reason.message : "No fue posible cargar las empresas."));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!erp || !dian) {
      setError("Selecciona el archivo del ERP y el archivo de la DIAN.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const created = await api<Reconciliation>("/api/v1/reconciliations", {
        method: "POST",
        body: JSON.stringify({
          company_id: companyId,
          period_start: periodStart,
          period_end: periodEnd,
          tolerance,
        }),
      });
      await upload(created.id, "erp", erp);
      await upload(created.id, "dian", dian);
      router.push(`/reconciliations/${created.id}`);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "No fue posible crear la conciliación.");
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Datos del proceso</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-5" onSubmit={onSubmit}>
          <Notice>
            Indica con claridad cuál archivo es del ERP y cuál es de la DIAN. Después podrás confirmar las columnas
            antes de comparar.
          </Notice>
          {companies.length === 0 ? (
            <p className="text-sm text-slate-600">
              Primero crea una empresa en la sección Empresas. Sin una empresa activa no se puede guardar la conciliación.
            </p>
          ) : null}
          <div>
            <Label htmlFor="company">Empresa</Label>
            <Select id="company" value={companyId} onChange={(event) => setCompanyId(event.target.value)} required>
              <option value="">Selecciona una empresa</option>
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.legal_name}
                </option>
              ))}
            </Select>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <Label htmlFor="start">Periodo desde</Label>
              <Input id="start" type="date" value={periodStart} onChange={(event) => setPeriodStart(event.target.value)} required />
            </div>
            <div>
              <Label htmlFor="end">Periodo hasta</Label>
              <Input id="end" type="date" value={periodEnd} onChange={(event) => setPeriodEnd(event.target.value)} required />
            </div>
            <div>
              <Label htmlFor="tolerance">Tolerancia monetaria</Label>
              <Input id="tolerance" value={tolerance} onChange={(event) => setTolerance(event.target.value)} required />
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <FileField title="Ventas del ERP" hint="Exportación de ventas del sistema contable." file={erp} onChange={setErp} />
            <FileField title="Facturación DIAN" hint="Información de facturación electrónica. No se asume un formato universal." file={dian} onChange={setDian} />
          </div>
          {error ? <ErrorText>{error}</ErrorText> : null}
          <Button type="submit" disabled={saving || companies.length === 0}>
            {saving ? "Cargando archivos..." : "Continuar a la asignación de columnas"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function FileField({
  title,
  hint,
  file,
  onChange,
}: {
  title: string;
  hint: string;
  file: File | null;
  onChange: (file: File | null) => void;
}) {
  return (
    <label className="block rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4">
      <span className="block text-sm font-semibold text-slate-900">{title}</span>
      <span className="mt-1 block text-xs text-slate-500">{hint} CSV o Excel .xlsx.</span>
      <input
        className="mt-3 block w-full text-sm"
        type="file"
        accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
      />
      {file ? <span className="mt-2 block text-xs text-teal-800">{file.name}</span> : null}
    </label>
  );
}

async function upload(reconciliationId: string, source: "erp" | "dian", file: File) {
  const body = new FormData();
  body.set("source", source);
  body.set("file", file);
  await api(`/api/v1/reconciliations/${reconciliationId}/files`, { method: "POST", body });
}
