import { Suspense } from "react";
import { ResultDetail } from "@/features/reconciliations/result-detail";

export default function ResultPage({ params }: { params: Promise<{ id: string; resultId: string }> }) {
  return (
    <Suspense fallback={<p className="text-sm text-slate-600">Cargando detalle...</p>}>
      <Resolved params={params} />
    </Suspense>
  );
}

async function Resolved({ params }: { params: Promise<{ id: string; resultId: string }> }) {
  const { id, resultId } = await params;
  return <ResultDetail reconciliationId={id} resultId={resultId} />;
}