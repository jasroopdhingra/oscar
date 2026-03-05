export interface RuleNode {
  rule_id: string;
  rule_text: string;
  operator?: "AND" | "OR";
  rules?: RuleNode[];
}

export interface CriteriaTree {
  title: string;
  insurance_name: string;
  rules: RuleNode;
}

export interface Policy {
  id: number;
  title: string;
  pdf_url: string;
  source_page_url: string;
  discovered_at: string;
  has_structured_tree: boolean;
  download_status: string | null;
}

export interface DownloadInfo {
  id: number;
  policy_id: number;
  stored_location: string | null;
  downloaded_at: string;
  http_status: number | null;
  error: string | null;
}

export interface StructuredPolicyInfo {
  id: number;
  policy_id: number;
  structured_json: CriteriaTree | null;
  structured_at: string;
  llm_metadata: Record<string, unknown> | null;
  validation_error: string | null;
}

export interface PolicyDetail {
  id: number;
  title: string;
  pdf_url: string;
  source_page_url: string;
  discovered_at: string;
  downloads: DownloadInfo[];
  structured_policies: StructuredPolicyInfo[];
}

export interface PipelineStatus {
  status: string;
  message: string;
  count: number;
}
