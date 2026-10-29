import { Suspense } from "react";
import { ReconciliationWorkspace } from "@/features/reconciliations/reconciliation-workspace";

export default function ReconciliationPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense fallback={<p className="text-sm text-slate-600">Cargando conciliación...</p>}>
      <Resolved params={params} />
    </Suspense>
  );
}

async function Resolved({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ReconciliationWorkspace reconciliationId={id} />;
}
