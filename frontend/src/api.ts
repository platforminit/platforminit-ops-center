const API_BASE = "http://localhost:8000";

export interface ProblemEntry {
  check_id: string;
  status: string;
  output: string;
  created_at: string;
  duration_seconds: number;
  timed_out: boolean;
  acknowledged: boolean;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  acknowledged_reason: string | null;
  in_downtime: boolean;
}

export interface ProblemsResponse {
  problems: ProblemEntry[];
}

export async function fetchProblems(): Promise<ProblemsResponse> {
  const response = await fetch(`${API_BASE}/api/v1/problems`);
  if (!response.ok) {
    throw new Error(`Failed to fetch problems: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<ProblemsResponse>;
}
