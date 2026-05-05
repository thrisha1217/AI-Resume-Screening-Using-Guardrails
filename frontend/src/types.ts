export interface Candidate {
  applicant_id: string;
  name: string;
  degree: string;
  specialisation: string;
  percentage: number;
  experience_years: number;
  skills: string;
  organization: string;
  status: 'screened in' | 'screened out' | 'manual check';
  reason: string;
  resume_summary: string;
  introduction: string;
  guardrails: string[];
}

export interface ScreeningResults {
  screened_in: number;
  screened_out: number;
  manual_check: number;
  total: number;
  results: Candidate[];
  guardrails_log: string[];
}

export interface JobStatus {
  status: 'queued' | 'running' | 'done' | 'error';
  progress: number;
  log: string[];
  error?: string;
}
