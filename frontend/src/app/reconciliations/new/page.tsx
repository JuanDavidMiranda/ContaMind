import { NewReconciliationForm } from "@/features/reconciliations/new-reconciliation-form";

export default function NewReconciliationPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-slate-900">Nueva conciliación</h1>
      <NewReconciliationForm />
    </div>
  );
}
