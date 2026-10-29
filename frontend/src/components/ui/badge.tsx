import { cn } from "@/lib/utils";
import { categoryLabel, statusLabel } from "@/lib/categories";

const tones: Record<string, string> = {
  MATCHED: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  MISSING_IN_DIAN: "bg-amber-50 text-amber-800 ring-amber-200",
  MISSING_IN_ERP: "bg-amber-50 text-amber-800 ring-amber-200",
  VALUE_MISMATCH: "bg-orange-50 text-orange-800 ring-orange-200",
  DATE_MISMATCH: "bg-orange-50 text-orange-800 ring-orange-200",
  THIRD_PARTY_MISMATCH: "bg-orange-50 text-orange-800 ring-orange-200",
  POSSIBLE_DUPLICATE: "bg-violet-50 text-violet-800 ring-violet-200",
  REQUIRES_REVIEW: "bg-violet-50 text-violet-800 ring-violet-200",
  completed: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  failed: "bg-rose-50 text-rose-800 ring-rose-200",
  running: "bg-sky-50 text-sky-800 ring-sky-200",
};

export function Badge({ value, kind = "category" }: { value: string; kind?: "category" | "status" }) {
  const label = kind === "status" ? statusLabel(value) : categoryLabel(value);
  return (
    <span className={cn("inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset", tones[value] ?? "bg-slate-100 text-slate-700 ring-slate-200")}>
      {label}
    </span>
  );
}
