// In production (Docker/AWS), nginx proxies /api/* to the backend.
// In local dev, falls back to localhost:8000.
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function submitScreening(
  requirements: File,
  excel: File,
  resumes: File
): Promise<string> {
  const form = new FormData();
  form.append('requirements', requirements);
  form.append('excel', excel);
  form.append('resumes', resumes);
  const res = await fetch(`${BASE}/api/screen`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  return data.job_id;
}

export async function getStatus(jobId: string) {
  const res = await fetch(`${BASE}/api/status/${jobId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getResults(jobId: string) {
  const res = await fetch(`${BASE}/api/results/${jobId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function getDownloadUrl(jobId: string) {
  return `${BASE}/api/download/${jobId}`;
}
