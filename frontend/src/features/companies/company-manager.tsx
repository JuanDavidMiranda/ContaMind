"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { ErrorText } from "@/components/notice";
import { formatDate } from "@/lib/utils";
import { api, ApiError } from "@/services/api";
import type { Company } from "@/types/api";

export function CompanyManager() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [legalName, setLegalName] = useState("");
  const [taxId, setTaxId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    const rows = await api<Company[]>("/api/v1/companies");
    setCompanies(rows);
  }

  useEffect(() => {
    load().catch((reason: unknown) => setError(reason instanceof ApiError ? reason.message : "No fue posible cargar las empresas."));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api<Company>("/api/v1/companies", {
        method: "POST",
        body: JSON.stringify({ legal_name: legalName, tax_id: taxId || null }),
      });
      setLegalName("");
      setTaxId("");
      await load();
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "No fue posible crear la empresa.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      <Card>
        <CardHeader>
          <CardTitle>Nueva empresa</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={onSubmit}>
            <div>
              <Label htmlFor="legal-name">Razón social</Label>
              <Input id="legal-name" value={legalName} onChange={(event) => setLegalName(event.target.value)} required />
            </div>
            <div>
              <Label htmlFor="tax-id">Identificación tributaria</Label>
              <Input id="tax-id" value={taxId} onChange={(event) => setTaxId(event.target.value)} placeholder="Opcional" />
            </div>
            {error ? <ErrorText>{error}</ErrorText> : null}
            <Button type="submit" disabled={saving}>
              {saving ? "Guardando..." : "Crear empresa"}
            </Button>
          </form>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Empresas</CardTitle>
        </CardHeader>
        <CardContent>
          {companies.length === 0 ? (
            <p className="text-sm text-slate-600">Crea la primera empresa para asociarle conciliaciones.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="text-slate-500">
                <tr>
                  <th className="py-2 font-medium">Razón social</th>
                  <th className="py-2 font-medium">Identificación</th>
                  <th className="py-2 font-medium">Estado</th>
                  <th className="py-2 font-medium">Creada</th>
                </tr>
              </thead>
              <tbody>
                {companies.map((company) => (
                  <tr key={company.id} className="border-t border-slate-100">
                    <td className="py-3">{company.legal_name}</td>
                    <td className="py-3">{company.tax_id || "—"}</td>
                    <td className="py-3">{company.status === "active" ? "Activa" : "Inactiva"}</td>
                    <td className="py-3">{formatDate(company.created_at)}</td>
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
