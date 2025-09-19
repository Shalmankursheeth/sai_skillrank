const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
async function handleJsonResponse(res) {
  const text = await res.text();
  try { return text ? JSON.parse(text) : null; } catch { return text; }
}
export async function getJobs(){ const res = await fetch(`${API_BASE}/jobs`); return handleJsonResponse(res); }
export async function createJob(payload){ const res = await fetch(`${API_BASE}/jobs`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}); return handleJsonResponse(res); }
export async function getCandidates(){ const res = await fetch(`${API_BASE}/candidates`); return handleJsonResponse(res); }
export async function createCandidate(payload, run_extract=false){ const url = `${API_BASE}/candidates${run_extract ? "?run_extract=true":""}`; const res = await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}); return handleJsonResponse(res); }
export async function uploadResume(file, name, email, run_extract=false){ const form = new FormData(); form.append("file", file); if(name) form.append("name", name); if(email) form.append("email", email); form.append("run_extract", run_extract ? "true":"false"); const res = await fetch(`${API_BASE}/resumes`,{method:"POST",body:form}); return handleJsonResponse(res); }
export async function extractCandidate(candidateId){ const res = await fetch(`${API_BASE}/candidates/${candidateId}/extract`,{method:"PUT"}); return handleJsonResponse(res); }
export async function computeMatch(candidateId, jobId, explain=true){ const url = `${API_BASE}/matches/simple?candidate_id=${candidateId}&job_id=${jobId}${explain ? "&explain=true":""}`; const res = await fetch(url,{method:"POST"}); return handleJsonResponse(res); }
export async function listMatches(){ try{ const res = await fetch(`${API_BASE}/matches`); if(!res.ok) return []; return handleJsonResponse(res); }catch{ return []; } }
