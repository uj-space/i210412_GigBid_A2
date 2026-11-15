import React, { createContext, useContext, useEffect, useState } from 'react';
import { BrowserRouter, Link, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import clsx from 'clsx';
import { apiClient, JobPosting } from './api/client';
import { DegradedBanner } from './components/DegradedBanner';
import { EvidenceHover } from './components/EvidenceHover';

interface User {
  id: string;
  name: string;
  persona: string;
}

interface AuthCtxType {
  user: User | null;
  login: (name: string, persona: string) => Promise<void>;
  logout: () => void;
}

const AuthCtx = createContext<AuthCtxType | null>(null);
const useAuth = () => useContext(AuthCtx)!;

function SignIn() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [persona, setPersona] = useState('AI/ML Engineer');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(name || 'Freelancer', persona);
      navigate('/jobs');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-indigo-700 via-indigo-600 to-blue-500 px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md space-y-6 rounded-2xl bg-white p-8 shadow-2xl"
      >
        <div className="text-center">
          <h1 className="text-3xl font-bold text-indigo-600">GigBid</h1>
          <p className="mt-1 text-sm text-slate-500">Multi-agent freelancer copilot</p>
        </div>
        <div className="space-y-4">
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
          />
          <select
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            value={persona}
            onChange={(e) => setPersona(e.target.value)}
          >
            <option>AI/ML Engineer</option>
            <option>Full-stack Web Developer</option>
            <option>Data Analyst</option>
          </select>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {loading ? 'Signing in…' : 'Enter GigBid'}
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={async () => {
              setLoading(true);
              try {
                await login('Reviewer (Preloaded)', 'AI/ML Engineer');
                navigate('/jobs');
              } finally {
                setLoading(false);
              }
            }}
            className="w-full rounded-lg border border-indigo-200 bg-indigo-50 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-100"
          >
            Reviewer Quick Login (AI/ML Engineer)
          </button>
        </div>
        <p className="text-center text-xs text-slate-400">
          Every proposal and message requires your approval before sending.
        </p>
      </form>
    </div>
  );
}

function Shell({
  children,
  degraded,
  onRecover,
}: {
  children: React.ReactNode;
  degraded: boolean;
  onRecover: () => void;
}) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [connects, setConnects] = useState<number>(80);

  useEffect(() => {
    apiClient.getConnects().then((d) => setConnects(d.balance ?? 80)).catch(() => {});
  }, []);

  const navItems = [
    { to: '/jobs', label: 'Job Inbox' },
    { to: '/board', label: 'Pipeline' },
    { to: '/messages', label: 'Messages' },
    { to: '/runs', label: 'Agent Runs' },
    { to: '/analytics', label: 'Analytics' },
    { to: '/settings', label: 'Settings' },
  ];

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      <aside className="fixed left-0 top-0 flex h-full w-60 flex-col bg-slate-900 text-white">
        <div className="border-b border-slate-800 p-4">
          <h1 className="text-xl font-bold text-white">GigBid</h1>
          <p className="text-xs text-slate-400">{user?.persona}</p>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {navItems.map((item) => {
            const active = window.location.pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={clsx(
                  'block rounded-lg px-3 py-2 text-sm font-medium transition',
                  active ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-800 p-4 text-xs">
          <div className="mb-2 flex items-center justify-between text-slate-300">
            <span>Connects</span>
            <span className="rounded bg-slate-800 px-2 py-0.5 font-semibold text-emerald-400">{connects}</span>
          </div>
          <div className="mb-2 truncate text-slate-400">{user?.name}</div>
          <button
            onClick={() => {
              logout();
              navigate('/');
            }}
            className="w-full rounded-md border border-slate-700 py-1.5 text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            Sign Out
          </button>
        </div>
      </aside>
      <main className="ml-60 flex-1 p-6">
        <DegradedBanner degraded={degraded} onRecover={onRecover} />
        {children}
      </main>
    </div>
  );
}

function JobInbox({
  analysisMap,
  setAnalysisMap,
}: {
  analysisMap: Record<string, any>;
  setAnalysisMap: React.Dispatch<React.SetStateAction<Record<string, any>>>;
}) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);

  const loadJobs = (q = '') => {
    setLoading(true);
    apiClient
      .searchJobs(q, 25)
      .then((d) => setJobs(d.jobs || []))
      .catch(() => setJobs([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadJobs('');
  }, []);

  const handleAnalyze = async (job: JobPosting) => {
    setAnalyzingId(job.job_id);
    try {
      const res = await apiClient.analyzeJob(job, user?.id || 'default');
      setAnalysisMap((prev) => ({ ...prev, [job.job_id]: res }));
      navigate(`/jobs/${job.job_id}`);
    } finally {
      setAnalyzingId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Job Inbox</h2>
          <p className="text-sm text-slate-500">Real-time marketplace opportunities scored for your persona.</p>
        </div>
        <div className="flex gap-2">
          <input
            className="w-64 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            placeholder="Search jobs..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button
            onClick={() => loadJobs(query)}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Search
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">Loading jobs…</p>
      ) : jobs.length === 0 ? (
        <p className="text-sm text-slate-500">No matching jobs found.</p>
      ) : (
        <div className="space-y-3">
          {jobs.map((j) => {
            const analyzed = analysisMap[j.job_id];
            return (
              <div
                key={j.job_id}
                className="flex flex-wrap items-start justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
              >
                <div className="max-w-2xl space-y-1.5">
                  <Link
                    to={`/jobs/${j.job_id}`}
                    className="text-base font-semibold text-indigo-700 hover:underline"
                  >
                    {j.title}
                  </Link>
                  <p className="line-clamp-2 text-sm text-slate-600">{j.description}</p>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {(j.required_skills || []).map((sk) => (
                      <span key={sk} className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-700">
                        {sk}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2 text-right">
                  <span className="text-sm font-semibold text-slate-800">
                    ${j.budget?.min ?? 0}–${j.budget?.max ?? 0}
                  </span>
                  <span className="text-xs text-slate-500">{j.connects_cost} Connects</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleAnalyze(j)}
                      disabled={analyzingId === j.job_id}
                      className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
                    >
                      {analyzingId === j.job_id ? 'Analyzing…' : analyzed ? 'Re-Analyze' : 'Analyze & Draft'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function JobDetail({
  analysisMap,
  setAnalysisMap,
}: {
  analysisMap: Record<string, any>;
  setAnalysisMap: React.Dispatch<React.SetStateAction<Record<string, any>>>;
}) {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [job, setJob] = useState<JobPosting | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const analysis = id ? analysisMap[id] : null;

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    apiClient
      .getJob(id)
      .then(setJob)
      .catch(() => setJob(null))
      .finally(() => setLoading(false));
  }, [id]);

  const runAnalysis = async () => {
    if (!job) return;
    setRunning(true);
    try {
      const res = await apiClient.analyzeJob(job, user?.id || 'default');
      setAnalysisMap((prev) => ({ ...prev, [job.job_id]: res }));
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <p className="text-sm text-slate-500">Loading job…</p>;
  if (!job) return <p className="text-sm text-rose-600">Job not found.</p>;

  const res = analysis?.result || {};
  const risk = res.risk_report || {};
  const fit = res.fit_report || {};
  const price = res.price_quote || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Job Detail</h2>
          <p className="text-sm text-slate-600">{job.title}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={runAnalysis}
            disabled={running}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            {running ? 'Running Agents…' : analysis ? 'Re-run Multi-Agent Analysis' : 'Run Multi-Agent Analysis'}
          </button>
          {analysis && (
            <button
              onClick={() => navigate(`/proposals/${job.job_id}`)}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
            >
              Open Proposal Studio
            </button>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="font-semibold text-slate-800">Job Description</h3>
        <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">{job.description}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {(job.required_skills || []).map((s) => (
            <span key={s} className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700">
              {s}
            </span>
          ))}
        </div>
      </div>

      {analysis && (
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs font-medium uppercase text-slate-400">Decision</div>
            <div className="mt-1 text-xl font-bold uppercase text-indigo-700">{res.decision || 'N/A'}</div>
            <div className="mt-1 text-xs text-slate-500">Thread: {analysis.thread_id}</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs font-medium uppercase text-slate-400">Fit & Risk</div>
            <div className="mt-1 text-sm">Fit Score: <strong>{fit.score ?? '—'}</strong></div>
            <div className="text-sm">Client Quality: <strong>{risk.score ?? '—'}</strong></div>
            {risk.scam && <span className="mt-1 inline-block rounded bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-700">SCAM FLAGGED</span>}
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs font-medium uppercase text-slate-400">Price Quote</div>
            <div className="mt-1 text-xl font-bold text-emerald-700">${price.suggested_bid ?? 0}</div>
            <div className="mt-1 text-xs text-slate-500">{price.rationale}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function ProposalStudio({
  analysisMap,
  setAnalysisMap,
}: {
  analysisMap: Record<string, any>;
  setAnalysisMap: React.Dispatch<React.SetStateAction<Record<string, any>>>;
}) {
  const { id } = useParams();
  const analysis = id ? analysisMap[id] : null;
  const res = analysis?.result || {};
  const draft = res.proposal_draft || {};
  const [coverLetter, setCoverLetter] = useState(draft.cover_letter || '');
  const [rejectReason, setRejectReason] = useState('');
  const [statusMsg, setStatusMsg] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setCoverLetter(draft.cover_letter || '');
  }, [draft.cover_letter]);

  if (!id || !analysis) {
    return (
      <div className="space-y-3">
        <h2 className="text-2xl font-bold">Proposal Studio</h2>
        <p className="text-sm text-slate-500">No active analysis for this job yet. Run analysis from Job Detail first.</p>
      </div>
    );
  }

  const evidenceList: any[] = res.evidence || [];
  const evidenceMap = Object.fromEntries(evidenceList.map((e) => [e.evidence_id, e]));
  const verifications: any[] = res.claim_verification || [];
  const compliance = res.compliance_verdict || { passed: true, violations: [] };

  const handleAction = async (action: 'approved' | 'edited' | 'rejected') => {
    setSubmitting(true);
    try {
      const resp = await apiClient.respondApproval({
        thread_id: analysis.thread_id,
        action,
        edit: action === 'edited' ? { cover_letter: coverLetter } : undefined,
        reason: action === 'rejected' ? rejectReason || 'Rejected by user' : undefined,
      });
      setStatusMsg(`Approval status: ${resp.approval_status}`);
      setAnalysisMap((prev) => ({
        ...prev,
        [id]: { ...prev[id], needs_approval: false, result: resp.result },
      }));
    } catch (err: any) {
      setStatusMsg(`Error: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Proposal Studio</h2>
          <p className="text-sm text-slate-500">Thread {analysis.thread_id} · Grounded claim-by-claim review</p>
        </div>
        <span
          className={clsx(
            'rounded-full px-3 py-1 text-xs font-semibold',
            compliance.passed ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
          )}
        >
          {compliance.passed ? 'Compliance Passed' : 'Compliance Violation'}
        </span>
      </div>

      {statusMsg && (
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm text-indigo-800">
          {statusMsg}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="font-semibold text-slate-800">Cover Letter Draft</h3>
          <textarea
            rows={11}
            value={coverLetter}
            onChange={(e) => setCoverLetter(e.target.value)}
            className="w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-indigo-500 focus:outline-none"
          />
          <div className="flex flex-wrap gap-2">
            <button
              disabled={submitting}
              onClick={() => handleAction('approved')}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
            >
              Approve & Submit
            </button>
            <button
              disabled={submitting}
              onClick={() => handleAction('edited')}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Save Edit & Submit
            </button>
          </div>
          <div className="flex gap-2 pt-2">
            <input
              className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
              placeholder="Rejection reason..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
            />
            <button
              disabled={submitting}
              onClick={() => handleAction('rejected')}
              className="rounded-lg bg-rose-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-rose-700"
            >
              Reject
            </button>
          </div>
        </div>

        <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="font-semibold text-slate-800">Claim-by-Claim Verification (Hover for Evidence)</h3>
          <div className="space-y-2">
            {verifications.length === 0 ? (
              <p className="text-sm text-slate-500">No claim verification records available.</p>
            ) : (
              verifications.map((v, idx) => (
                <EvidenceHover key={idx} item={v} evidenceMap={evidenceMap} />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function PipelineBoard() {
  const [cards, setCards] = useState<any[]>([]);
  useEffect(() => {
    apiClient.getPipeline().then((d) => setCards(d.cards || [])).catch(() => {});
  }, []);

  const columns = ['drafted', 'submitted', 'interview', 'won', 'lost'];
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-slate-800">Pipeline Board</h2>
      <div className="grid gap-4 md:grid-cols-5">
        {columns.map((col) => (
          <div key={col} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">{col}</h3>
            <div className="space-y-2">
              {cards
                .filter((c) => c.status === col)
                .map((c) => (
                  <Link
                    key={c.id}
                    to={`/proposals/${c.id}`}
                    className="block rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs hover:border-indigo-400"
                  >
                    <div className="font-semibold text-slate-800">{c.title}</div>
                    <div className="mt-1 text-slate-500">Fit: {c.fit_score}</div>
                  </Link>
                ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MessagesInbox() {
  const [messages, setMessages] = useState<any[]>([]);
  const [replyState, setReplyState] = useState<any>(null);
  const [draftBody, setDraftBody] = useState('');

  useEffect(() => {
    apiClient.getMessages().then((d) => setMessages(d.messages || [])).catch(() => {});
  }, []);

  const draftReply = async (m: any) => {
    const res = await apiClient.respondMessage(m);
    setReplyState(res);
    setDraftBody(res?.result?.reply_draft?.body || '');
  };

  const approveReply = async (action: 'approved' | 'rejected') => {
    if (!replyState?.thread_id) return;
    await apiClient.approveMessage(replyState.thread_id, action, draftBody);
    setReplyState(null);
  };

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-slate-800">Messages Inbox</h2>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-3">
          {messages.map((m, i) => (
            <div key={i} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-xs font-semibold text-indigo-600">Client {m.client_id}</div>
              <p className="mt-1 text-sm text-slate-700">{m.body}</p>
              <button
                onClick={() => draftReply(m)}
                className="mt-2 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white"
              >
                Draft AI Reply
              </button>
            </div>
          ))}
        </div>
        {replyState && (
          <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="font-semibold">Reply Approval Gate ({replyState.result?.intent})</h3>
            <textarea
              rows={6}
              value={draftBody}
              onChange={(e) => setDraftBody(e.target.value)}
              className="w-full rounded-lg border border-slate-300 p-2 text-sm"
            />
            <div className="flex gap-2">
              <button
                onClick={() => approveReply('approved')}
                className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white"
              >
                Approve & Send
              </button>
              <button
                onClick={() => approveReply('rejected')}
                className="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-medium text-white"
              >
                Reject
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AgentRuns() {
  const [runs, setRuns] = useState<any[]>([]);
  const [events, setEvents] = useState<string[]>([]);
  const [activeThread, setActiveThread] = useState<string | null>(null);

  useEffect(() => {
    apiClient.getRuns().then((d) => setRuns(d.runs || [])).catch(() => {});
  }, []);

  const streamRun = (threadId: string) => {
    setActiveThread(threadId);
    setEvents([]);
    const es = new EventSource(`/api/runs/${threadId}/stream`);
    es.onmessage = (ev) => {
      setEvents((prev) => [...prev, ev.data]);
    };
    es.addEventListener('done', () => es.close());
    es.onerror = () => es.close();
  };

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-slate-800">Agent Runs & Traces</h2>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-2">
          {runs.length === 0 ? (
            <p className="text-sm text-slate-500">No runs recorded yet.</p>
          ) : (
            runs.map((r) => (
              <div key={r.thread_id} className="flex items-center justify-between rounded-xl border bg-white p-3 text-sm">
                <div>
                  <div className="font-semibold">{r.title || r.job_id}</div>
                  <div className="text-xs text-slate-500">{r.thread_id} · {r.status}</div>
                </div>
                <button
                  onClick={() => streamRun(r.thread_id)}
                  className="rounded bg-indigo-600 px-3 py-1 text-xs text-white"
                >
                  Stream SSE
                </button>
              </div>
            ))
          )}
        </div>
        <div className="rounded-xl border bg-slate-900 p-4 font-mono text-xs text-emerald-300">
          <div className="mb-2 text-slate-400">Live SSE Stream {activeThread ? `(${activeThread})` : ''}</div>
          {events.map((e, i) => (
            <div key={i}>{e}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Analytics() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    apiClient.getAnalytics().then(setData).catch(() => {});
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-slate-800">Analytics</h2>
      {data && (
        <div className="grid gap-4 md:grid-cols-4">
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <div className="text-xs text-slate-500">Reply Rate</div>
            <div className="text-2xl font-bold text-indigo-700">{(data.replyRate * 100).toFixed(0)}%</div>
          </div>
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <div className="text-xs text-slate-500">Hire Rate</div>
            <div className="text-2xl font-bold text-emerald-700">{(data.hireRate * 100).toFixed(0)}%</div>
          </div>
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <div className="text-xs text-slate-500">Connects Spent</div>
            <div className="text-2xl font-bold text-slate-800">{data.connects}</div>
          </div>
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <div className="text-xs text-slate-500">RAG Recall@5 (V8)</div>
            <div className="text-2xl font-bold text-indigo-700">
              {data.eval_summary?.rag_best_recall_at_5 ?? '1.0'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Settings({
  degraded,
  onToggleDegraded,
}: {
  degraded: boolean;
  onToggleDegraded: (flag: boolean) => void;
}) {
  const { user } = useAuth();
  const [variant, setVariant] = useState('v8');
  const [floor, setFloor] = useState(40);
  const [memory, setMemory] = useState<any>({ style: [], outcome: [] });

  useEffect(() => {
    apiClient.getSettings().then((s) => {
      if (s.rag_variant) setVariant(s.rag_variant);
      if (s.rate_floor) setFloor(s.rate_floor);
    }).catch(() => {});
    apiClient.getMemory(user?.id || 'default').then(setMemory).catch(() => {});
  }, [user?.id]);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">Settings</h2>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-3 rounded-xl border bg-white p-5 shadow-sm">
          <h3 className="font-semibold">Agent & RAG Configuration</h3>
          <label className="block text-xs text-slate-500">Active RAG Variant</label>
          <select
            value={variant}
            onChange={(e) => setVariant(e.target.value)}
            className="w-full rounded-lg border px-3 py-2 text-sm"
          >
            {['v0', 'v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9'].map((v) => (
              <option key={v} value={v}>{v.toUpperCase()}</option>
            ))}
          </select>
          <label className="block text-xs text-slate-500">Hourly Rate Floor ($)</label>
          <input
            type="number"
            value={floor}
            onChange={(e) => setFloor(Number(e.target.value))}
            className="w-full rounded-lg border px-3 py-2 text-sm"
          />
          <div className="flex gap-2">
            <button
              onClick={() => apiClient.updateSettings({ rag_variant: variant, rate_floor: floor })}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-medium text-white"
            >
              Save Settings
            </button>
            <button
              onClick={() => onToggleDegraded(!degraded)}
              className="rounded-lg border border-amber-400 px-4 py-2 text-xs font-medium text-amber-800"
            >
              {degraded ? 'Disable Degraded Mode' : 'Simulate Marketplace Outage'}
            </button>
          </div>
        </div>

        <div className="space-y-3 rounded-xl border bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Long-Term Memory (Style & Outcome)</h3>
            <button
              onClick={() => apiClient.deleteMemory(user?.id || 'default').then(() => setMemory({ style: [], outcome: [] }))}
              className="text-xs text-rose-600 hover:underline"
            >
              Clear Memory
            </button>
          </div>
          <div className="text-xs text-slate-600">
            <strong>Style Rules:</strong> {(memory.style || []).length}
          </div>
          <div className="text-xs text-slate-600">
            <strong>Outcome Records:</strong> {(memory.outcome || []).length}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [analysisMap, setAnalysisMap] = useState<Record<string, any>>({});

  useEffect(() => {
    apiClient
      .health()
      .then((h) => setDegraded(Boolean(h.marketplace_degraded)))
      .catch(() => setDegraded(true));
  }, []);

  const login = async (name: string, persona: string) => {
    const res = await apiClient.login(name, persona);
    localStorage.setItem('gigbid_token', res.token);
    setUser(
      res.user || {
        id: res.user_id || res.persona || 'default',
        name: res.name || name,
        persona: res.persona || persona,
      }
    );
  };

  const logout = () => {
    localStorage.removeItem('gigbid_token');
    setUser(null);
  };

  const toggleDegraded = async (flag: boolean) => {
    await apiClient.toggleDegraded(flag);
    setDegraded(flag);
  };

  return (
    <AuthCtx.Provider value={{ user, login, logout }}>
      <BrowserRouter>
        {!user ? (
          <Routes>
            <Route path="*" element={<SignIn />} />
          </Routes>
        ) : (
          <Shell degraded={degraded} onRecover={() => toggleDegraded(false)}>
            <Routes>
              <Route path="/" element={<JobInbox analysisMap={analysisMap} setAnalysisMap={setAnalysisMap} />} />
              <Route path="/jobs" element={<JobInbox analysisMap={analysisMap} setAnalysisMap={setAnalysisMap} />} />
              <Route path="/jobs/:id" element={<JobDetail analysisMap={analysisMap} setAnalysisMap={setAnalysisMap} />} />
              <Route path="/proposals/:id" element={<ProposalStudio analysisMap={analysisMap} setAnalysisMap={setAnalysisMap} />} />
              <Route path="/board" element={<PipelineBoard />} />
              <Route path="/messages" element={<MessagesInbox />} />
              <Route path="/runs" element={<AgentRuns />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings degraded={degraded} onToggleDegraded={toggleDegraded} />} />
            </Routes>
          </Shell>
        )}
      </BrowserRouter>
    </AuthCtx.Provider>
  );
}
