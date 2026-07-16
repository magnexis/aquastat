export type EvidenceClass =
  | "Level A"
  | "Level B"
  | "Level C"
  | "Level D"
  | "Level E"
  | "Level F"
  | "Level U";

export interface DataQualitySummary {
  score: number;
  label: string;
  reasons: string[];
}

export interface FacilityCoverage {
  location: string;
  capacity: string;
  cooling_system: string;
  pue: string;
  wue: string;
  water_use: string;
}

export interface SourceSummary {
  total_sources: number;
  primary_sources: number;
  independent_chains: number;
  latest_source_date: string;
}

export interface FacilitySummary {
  id: string;
  slug: string;
  name: string;
  operator: string;
  facility_type: string;
  operational_status: string;
  country: string;
  state_or_province: string | null;
  municipality: string | null;
  latitude: number | null;
  longitude: number | null;
  estimated_it_load_mw: number | null;
  announced_it_load_mw: number | null;
  cooling_systems: string[];
  electricity_grid_region: string | null;
  verification_status: string;
  synthetic: boolean;
  production_eligible: boolean;
  data_quality: DataQualitySummary;
  coverage: FacilityCoverage;
  source_summary: SourceSummary;
  warnings: string[];
}

export interface FieldEvidence {
  field: string;
  value: string | number | boolean | null;
  unit: string | null;
  evidence_class: EvidenceClass;
  figure_type: string;
  reporting_boundary: string;
  source_id: string;
  source_type: string;
  source_date: string;
  extraction_method: string;
  verification_status: string;
  confidence: number;
  value_status: string;
  independent_chain_id: string | null;
  notes: string | null;
}

export interface WaterSourceComponent {
  type: string;
  percent: number | null;
  status: string;
}

export interface FacilityDetailResponse {
  facility: FacilitySummary;
  aliases: string[];
  owner: string | null;
  campus_name: string | null;
  primary_water_figure: FieldEvidence | null;
  contradictory_claims: FieldEvidence[];
  water_sources: WaterSourceComponent[];
  utility_providers: string[];
  reported_data_year: number | null;
  confidence_score: number;
  record_status: string;
  verification_notes: string[];
}

export interface FacilityListResponse {
  items: FacilitySummary[];
  next_cursor: string | null;
  total: number;
}

export interface FacilityHistoryEntry {
  changed_at: string;
  field: string;
  previous_value: string | number | null;
  new_value: string | number | null;
  status: string;
  source_id: string | null;
  summary: string;
}

export interface FacilityChangesResponse {
  facility_id: string;
  changes: FacilityHistoryEntry[];
}

export interface FacilityEvidenceResponse {
  facility_id: string;
  evidence: FieldEvidence[];
}

export interface SourceReliability {
  score: number;
  tier: string;
  explanation: string;
}

export interface SourceRecordResponse {
  id: string;
  title: string;
  publisher: string;
  source_type: string;
  url: string;
  document_type: string;
  publication_date: string;
  retrieved_at: string;
  license: string | null;
  jurisdiction: string | null;
  language: string;
  access_status: string;
  parser_version: string;
  ingestion_status: string;
  review_status: string;
  notes: string | null;
  reliability: SourceReliability;
}

export interface FacilitySourcesResponse {
  facility_id: string;
  sources: SourceRecordResponse[];
}

export interface PublicRecordHolder {
  authority: string;
  jurisdiction: string;
  record_types: string[];
  rationale: string;
}

export interface PublicRecordTemplate {
  facility_id: string;
  authority: string;
  subject: string;
  summary: string;
  requested_records: string[];
  body: string;
  legal_notes: string[];
}

export interface PublicRecordTemplateResponse {
  facility_id: string;
  known_holders: PublicRecordHolder[];
  templates: PublicRecordTemplate[];
}
