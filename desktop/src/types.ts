export type EvidenceClass =
  | "Level A"
  | "Level B"
  | "Level C"
  | "Level D"
  | "Level E"
  | "Level F"
  | "Level U";

export interface FacilitySummary {
  id: string;
  slug: string;
  name: string;
  operator: string;
  facility_type: string;
  operational_status: string;
  country: string;
  data_quality: {
    score: number;
    label: string;
    reasons: string[];
  };
}

export interface FieldEvidence {
  field: string;
  value: string | number | boolean | null;
  unit: string | null;
  evidence_class: EvidenceClass;
  figure_type: string;
  reporting_boundary: string;
  source_id: string;
  confidence: number;
  value_status: string;
  notes: string | null;
}

export interface FacilityDetailResponse {
  facility: FacilitySummary;
  primary_water_figure: FieldEvidence | null;
  contradictory_claims: FieldEvidence[];
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
  known_holders: Array<{
    authority: string;
    jurisdiction: string;
    record_types: string[];
    rationale: string;
  }>;
  templates: PublicRecordTemplate[];
}
