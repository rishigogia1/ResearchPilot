export type ExecutionStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'not_implemented';

export type ConfidenceLevel = 'low' | 'medium' | 'high';

export type ResearchDepth = 'quick' | 'standard' | 'deep';

export type ServiceStatus = 'missing_credentials' | 'configured' | 'verified' | 'unavailable';

export interface HealthServices {
  llm_provider?: string;
  llm_configured?: boolean;
  tavily_configured?: boolean;
  extractor_operational?: boolean;
  [key: string]: unknown;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  timestamp: string;
  services: HealthServices;
}

export interface LLMHealthResponse {
  status: ServiceStatus;
  configured: boolean;
  provider: string;
  model: string;
  message: string;
  timestamp: string;
}

export interface ToolItemHealth {
  name: string;
  status: ServiceStatus;
  configured: boolean;
  verified: boolean;
  description: string;
}

export interface ToolsHealthResponse {
  status: string;
  tools: ToolItemHealth[];
  timestamp: string;
}

export interface ResearchRequest {
  query: string;
  depth?: ResearchDepth;
  max_sources?: number;
}

export interface PlanStep {
  step_id: number;
  description: string;
  search_query: string;
  status: string;
}

export interface EvidenceSource {
  source_id: string;
  url: string;
  title: string;
  domain: string;
  snippet: string;
  raw_content?: string | null;
  credibility_note?: string | null;
}

export interface Citation {
  citation_id: string;
  source_id: string;
  url: string;
  source_title: string;
  cited_claim: string;
}

export interface FindingItem {
  heading: string;
  content: string;
  citations: string[];
}

export interface ConfidenceScore {
  score: number;
  level: ConfidenceLevel;
  explanation: string;
  limitations: string[];
}

export interface ResearchResponse {
  query: string;
  status: ExecutionStatus;
  executive_summary: string;
  findings: FindingItem[];
  plan: PlanStep[];
  sources: EvidenceSource[];
  citations: Citation[];
  confidence: ConfidenceScore;
  assumptions: string[];
  limitations: string[];
  suggested_next_steps: string[];
  completed_at?: string | null;
  execution_time_seconds?: number | null;
  metadata?: Record<string, unknown>;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: unknown;
  request_id?: string;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}
