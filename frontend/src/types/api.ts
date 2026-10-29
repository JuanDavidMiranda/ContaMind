import type { FieldKey } from "@/lib/categories";

export type Company = {
  id: string;
  legal_name: string;
  tax_id: string | null;
  status: string;
  created_at: string;
};

export type StoredFile = {
  id: string;
  source: "erp" | "dian";
  original_filename: string;
  detected_type: string;
  encoding: string | null;
  size_bytes: number;
  row_count: number;
  warnings: string[];
};

export type Reconciliation = {
  id: string;
  company_id: string;
  company_name: string;
  period_start: string;
  period_end: string;
  status: string;
  tolerance: string;
  erp_mapping: Partial<Record<FieldKey, string | null>> | null;
  dian_mapping: Partial<Record<FieldKey, string | null>> | null;
  summary: Summary | null;
  rules: Rules | null;
  executed_at: string | null;
  created_at: string;
  files: StoredFile[];
  current_run_id: string;
  run_count: number;
  review_progress: ReviewProgress | null;
};

export type ReviewProgress = {
  actionable_count: number;
  pending_count: number;
  reviewed_count: number;
  progress_label: string;
};

export type Summary = {
  erp_rows_read: number;
  dian_rows_read: number;
  erp_rows_usable: number;
  dian_rows_usable: number;
  erp_rows_rejected: number;
  dian_rows_rejected: number;
  matched: number;
  missing_in_dian: number;
  missing_in_erp: number;
  value_mismatch_flags: number;
  date_mismatch_flags: number;
  third_party_mismatch_flags: number;
  duplicate_groups: number;
  requires_review: number;
  processing_errors: number;
  result_count: number;
};

export type Rules = {
  tolerance: string;
  match_key: string;
  active_fields: string[];
  skipped_fields: { field: string; reason: string }[];
  disclaimer: string;
};

export type Suggestion = {
  column: string | null;
  confidence: number;
  reason: string;
};

export type SourcePreview = {
  source: "erp" | "dian";
  filename: string;
  headers: string[];
  suggestions: Record<FieldKey, Suggestion>;
  sample_rows: Array<Record<string, string | null>>;
  warnings: string[];
};

export type ColumnsPreview = {
  erp: SourcePreview | null;
  dian: SourcePreview | null;
};

export type Difference = {
  field: FieldKey;
  erp_original: string | null;
  dian_original: string | null;
  erp_normalized: string | null;
  dian_normalized: string | null;
  delta: string | null;
};

export type Candidate = {
  row_index: number;
  row_number: number;
  original: Record<string, string | null>;
  normalized: Record<string, string | null>;
  issues: Array<{ field: string | null; code: string; message: string; severity: string }>;
};

export type ReconciliationResult = {
  id: string;
  document_key: string;
  primary_category: string;
  flags: string[];
  differences: Difference[];
  messages: string[];
  erp_original: Record<string, string | null> | null;
  dian_original: Record<string, string | null> | null;
  erp_normalized: Record<string, string | null> | null;
  dian_normalized: Record<string, string | null> | null;
  erp_row_numbers: number[];
  dian_row_numbers: number[];
  erp_candidates: Candidate[];
  dian_candidates: Candidate[];
  duplicate_kind: string | null;
  validation_errors?: Array<{
    source: string;
    row_number: number;
    issues: Array<{ message: string; severity: string }>;
  }>;
};

export type ResultPage = {
  items: ReconciliationResult[];
  total: number;
  page: number;
  page_size: number;
};
