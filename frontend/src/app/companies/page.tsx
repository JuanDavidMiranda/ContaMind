import { CompanyManager } from "@/features/companies/company-manager";

export default function CompaniesPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-slate-900">Empresas</h1>
      <CompanyManager />
    </div>
  );
}
