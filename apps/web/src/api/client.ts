/**
 * Typed GigBid API Client matching FastAPI OpenAPI schema (/openapi.json).
 */

export interface HealthResponse {
  status: string;
  service: string;
  marketplace_degraded: boolean;
}

export interface JobPosting {
  job_id: string;
  title: string;
  description: string;
  required_skills: string[];
  budget?: { min: number; max: number; currency: string };
  budget_min?: number;
  budget_max?: number;
  currency?: string;
  connects_cost: number;
  client_id: string;
  warning_signals: string[];
  persona?: string;
}

export interface AnalyzeResponse {
  status: string;
  needs_approval: boolean;
  thread_id: string;
  result: Record<string, any>;
}

export interface ApproveRequest {
  thread_id: string;
  action: 'approved' | 'edited' | 'rejected';
  edit?: Record<string, any>;
  reason?: string;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem('gigbid_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const res = await fetch(url, { ...init, headers });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export const apiClient = {
  health: () => request<HealthResponse>('/api/health'),
  login: (name: string, persona: string) =>
    request<{ token: string; user_id?: string; name?: string; persona?: string; user?: { id: string; name: string; persona: string } }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ name, persona }),
    }),
  searchJobs: (q = '', limit = 25) =>
    request<{ jobs: JobPosting[]; degraded: boolean; error?: string }>(
      `/api/jobs/search?q=${encodeURIComponent(q)}&limit=${limit}`
    ),
  getJob: (jobId: string) => request<JobPosting>(`/api/jobs/${encodeURIComponent(jobId)}`),
  analyzeJob: (job: JobPosting, userId = 'default') =>
    request<AnalyzeResponse>('/api/jobs/analyze', {
      method: 'POST',
      body: JSON.stringify({ job, user_id: userId }),
    }),
  respondApproval: (body: ApproveRequest) =>
    request<{ status: string; thread_id: string; approval_status: string; result: Record<string, any> }>(
      '/api/approvals/respond',
      { method: 'POST', body: JSON.stringify(body) }
    ),
  getPipeline: () => request<{ cards: Record<string, any>[] }>('/api/pipeline'),
  getProposal: (jobId: string) => request<Record<string, any>>(`/api/proposals/${encodeURIComponent(jobId)}`),
  regenerateProposal: (jobId: string, feedback = '') =>
    request<Record<string, any>>('/api/proposals/regenerate', {
      method: 'POST',
      body: JSON.stringify({ job_id: jobId, feedback }),
    }),
  getMessages: () => request<{ messages: Record<string, any>[] }>('/api/messages'),
  respondMessage: (message: Record<string, any>, userId = 'default') =>
    request<Record<string, any>>('/api/messages/respond', {
      method: 'POST',
      body: JSON.stringify({ client_message: message, user_id: userId }),
    }),
  approveMessage: (threadId: string, action: string, editBody?: string) =>
    request<Record<string, any>>('/api/messages/approve', {
      method: 'POST',
      body: JSON.stringify({ thread_id: threadId, action, edit: editBody ? { body: editBody } : undefined }),
    }),
  getRuns: () => request<{ runs: Record<string, any>[] }>('/api/runs'),
  getAnalytics: () => request<Record<string, any>>('/api/analytics'),
  getConnects: () => request<{ balance: number; reserved: number }>('/api/connects'),
  getSettings: () => request<Record<string, any>>('/api/settings'),
  updateSettings: (payload: Record<string, any>) =>
    request<Record<string, any>>('/api/settings', { method: 'PUT', body: JSON.stringify(payload) }),
  getMemory: (userId = 'default') => request<Record<string, any>>(`/api/memory?user_id=${encodeURIComponent(userId)}`),
  deleteMemory: (userId = 'default', kind?: string) =>
    request<Record<string, any>>(
      `/api/memory?user_id=${encodeURIComponent(userId)}${kind ? `&kind=${kind}` : ''}`,
      { method: 'DELETE' }
    ),
  toggleDegraded: (enabled: boolean) =>
    request<{ degraded: boolean }>(`/api/marketplace/degraded?flag=${enabled}`, { method: 'POST' }),
};
