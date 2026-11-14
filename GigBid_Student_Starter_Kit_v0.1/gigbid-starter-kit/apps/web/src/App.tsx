import React, { useState, createContext, useContext, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Link, useParams } from 'react-router-dom'
import clsx from 'clsx'

const API = {
  health: () => fetch('/api/health').then(r => r.json()),
  searchJobs: (q: string, limit = 20) => fetch(`/api/jobs/search?q=${encodeURIComponent(q)}&limit=${limit}`).then(r => r.json()),
  getJob: (id: string) => fetch(`/api/jobs/${id}`).then(r => r.json()),
  analyzeJob: (job: any) => fetch('/api/jobs/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ job }) }).then(r => r.json()),
  approvalsRespond: (body: any) => fetch('/api/approvals/respond', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(r => r.json()),
  messagesRespond: (body: any) => fetch('/api/messages/respond', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(r => r.json()),
  analytics: () => fetch('/api/analytics').then(r => r.json()),
  connects: () => fetch('/api/connects').then(r => r.json()),
}

interface User { id: string; name: string; persona: string }
interface AuthCtx { user: User | null; login: (n: string, p: string) => void; logout: () => void }
const AuthCtx = createContext<AuthCtx | null>(null)
export const useAuth = () => useContext(AuthCtx)!

interface AppCtxType { runningThread: string | null; setRunningThread: (t: string | null) => void }
const AppCtx = createContext<AppCtxType>({ runningThread: null, setRunningThread: () => {} })
export const useApp = () => useContext(AppCtx)!
interface RouteParams { id: string }
const badge = (v: any) => (v ? <span className="badge">{v}</span> : null)

function SignIn({ onLogin }: { onLogin: (n: string, p: string) => void }) {
  const [name, setName] = useState(''); const [persona, setPersona] = useState('AI/ML Engineer'); const [loading, setLoading] = useState(false)
  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-indigo-600 to-blue-500 px-4">
      <form onSubmit={(e) => { e.preventDefault(); onLogin(name || 'Freelancer', persona); }} className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8 space-y-6">
        <div className="text-center"><h1 className="text-3xl font-bold text-indigo-600">GigBid</h1><p className="text-slate-500 text-sm mt-1">Multi-agent freelancer copilot</p></div>
        <div className="space-y-4">
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
          <select className="input" value={persona} onChange={(e) => setPersona(e.target.value)}><option>AI/ML Engineer</option><option>Full-stack Web Developer</option><option>Data Analyst</option></select>
          <button className="btn-primary" disabled={loading}>{loading ? 'Signing in…' : 'Enter GigBid'}</button>
        </div>
        <p className="text-xs text-slate-400 text-center">Every proposal and message requires your approval before sending.</p>
      </form>
    </div>
  )
}

function Sidebar({ user, runningThread, setRunningThread }: any) {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-slate-900 text-white flex flex-col">
      <div className="p-4"><h1 className="text-xl font-bold text-white">GigBid</h1><p className="text-xs text-slate-400">{user.persona}</p></div>
      <nav className="flex-1 p-4 space-y-1">
        <NavLink to="/">Overview</NavLink>
        <NavLink to="/jobs">Job Inbox</NavLink>
        <NavLink to="/board">Pipeline</NavLink>
        <NavLink to="/messages">Messages</NavLink>
        <NavLink to="/runs">Agent Runs</NavLink>
        <NavLink to="/analytics">Analytics</NavLink>
        <NavLink to="/settings">Settings</NavLink>
      </nav>
      <div className="p-4 border-t border-slate-700"><div className="text-sm"><span className="block text-xs text-slate-400">User</span><span className="truncate">{user.name}</span></div><button className="mt-2 w-full text-xs border border-slate-600 py-1 rounded text-slate-400 hover:text-white" onClick={() => {}}>Settings</button></div>
    </aside>
  )
}

function NavLink({ children, to }: any) {
  const active = window.location.pathname === to
  return <Link to={to} className={clsx('block px-3 py-2 rounded-md text-sm font-medium', active ? 'bg-indigo-700 text-white' : 'text-slate-300 hover:bg-slate-700')}>{children}</Link>
}

function Dashboard({ user }: any) { return <div className="space-y-6"><Header /><OverviewCards /></div> }
function OverviewCards() { const [a] = useState({ jobs: 3, replies: 5, hires: 1, proposals: 7 }); return (
  <div className="grid gap-4 md:grid-cols-4">
    <Stat label="Jobs bidding" value={a.jobs} sub="50% hit rate" />
    <Stat label="Replies" value={a.replies} sub="3 led to interviews" />
    <Stat label="Hired" value={a.hires} sub="1 was a $900 project" />
    <Stat label="Proposals sent" value={a.proposals} sub="All human-approved" />

function Header() {
  const [connects, setConnects] = useState({ balance: 12 })
  useEffect(() => API.connects().then(setConnects), [])
  return (
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div><h2 className="text-xl font-semibold text-slate-800">Welcome back</h2><p className="text-slate-500 text-sm">GigBid is analysing your pipeline.</p></div>
      <div className="flex items-center gap-4">
        <div className="bg-white px-3 py-2 rounded-lg shadow text-sm border"><span className="block text-slate-500 text-xs">Connects</span><span className="font-semibold">{connects.balance}</span></div>
        <span className="badge bg-emerald-100 text-emerald-700">Live</span>
      </div>
    </div>
  )
}

function JobInbox({ user }: any) {
  const [jobs, setJobs] = useState<any[]>([]); const [loading, setLoading] = useState(true)
  useEffect(() => {
    API.searchJobs('').then(d => setJobs(d.jobs || [])).finally(() => setLoading(false))
  }, [user])
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between"><h3 className="text-lg font-semibold">Job Inbox</h3><input className="input w-64" placeholder="Search jobs" /></div>
      {loading ? <p className="text-slate-500">Loading…</p> : jobs.length === 0 ? <p className="text-slate-500">No jobs found.</p> :
        <div className="space-y-3">{jobs.map((j: any) => (
          <div key={j.job_id} className="bg-white rounded-xl border p-4 hover:shadow">
            <div className="flex items-start justify-between">
              <div><h4 className="font-semibold">{j.title}</h4><p className="text-xs text-slate-400">Client: {j.client_id}</p></div>
              <span className={clsx('badge', j.risk_report?.scam ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700')}>{j.risk_report?.scam ? 'SCAM RISK' : 'Review'}</span>
            </div>
            <p className="text-sm text-slate-600 mt-2 line-clamp-2">{j.description}</p>
            <div className="flex flex-wrap gap-2 mt-3 text-xs"><span className="badge bg-indigo-100 text-indigo-700">{j.required_skills?.join(', ')}</span><span className="badge bg-slate-100 text-slate-600">Connects: {j.connects_cost}</span></div>
          </div>
        ))}</div>}
    </div>
  )
}

function JobDetail({ user }: any) {
  const { id } = useParams() as RouteParams
  const [job, setJob] = useState<any>(null); const [detail, setDetail] = useState<any>(null)
  useEffect(() => {
    if (id) {
      API.getJob(id).then(setJob).catch(() => {})

function ProposalStudio() {
  const { id } = useParams() as RouteParams
  const [proposal, setProposal] = useState<any>(null); const [approved, setApproved] = useState(false)
  useEffect(() => { setProposal({ cover_letter: 'Draft cover letter citing evidence.', status: 'pending_review' }) }, [id])
  return (
    <div className="max-w-4xl space-y-4">
      <h3 className="text-xl font-semibold">Proposal Studio</h3>
      <div className="bg-white rounded-xl border p-4">
        <div className="h-2 bg-slate-200 rounded mb-2 w-full" />
        <textarea className="input h-32" value={proposal?.cover_letter || ''} onChange={() => {}} placeholder="Cover letter" />
        <div className="flex flex-wrap gap-2 mt-2 text-xs">
          <span className="badge bg-indigo-100 text-indigo-700">Evidence: [EVD-1], [EVD-3]</span>
          <span className="badge bg-slate-100 text-slate-600">Critic: grounded, personalised</span>
          <span className="badge bg-slate-100 text-slate-600">Compliance: passed</span>
        </div>
        <div className="mt-2 text-sm text-slate-600"><b>Dry run:</b> sends proposal via GigSim, costs 8 connects.</div>
        <div className="flex gap-2 mt-3">
          <button className="btn-primary" onClick={() => setApproved(true)}>Approve</button>
          <button className="btn-secondary" onClick={() => {}}>Reject</button>
          <button className="btn-secondary" onClick={() => {}}>Regenerate paragraph</button>
        </div>
        {approved && <p className="mt-2 text-emerald-600 font-medium">Proposal submitted to marketplace as a draft.</p>}
      </div>
    </div>
  )
}

function PipelineBoard() {
  const [cards, setCards] = useState([{ id: 1, title: 'Churn baseline job', status: 'drafted' as const }, { id: 2, title: 'Dashboard trial', status: 'submitted' as const }, { id: 3, title: 'Data pipeline', status: 'interview' as const }])
  const columns = ['drafted', 'submitted', 'viewed', 'replied', 'interview', 'hired', 'lost']
  return (
    <div><h3 className="text-xl font-semibold mb-3">Pipeline Board</h3><div className="flex gap-3 overflow-x-auto">{columns.map(c => (
      <div key={c} className="flex-shrink-0 w-44 bg-white rounded-xl border p-3"><div className="text-xs font-semibold text-slate-500 mb-2">{c}</div><div className="space-y-2">{cards.filter(cd => cd.status === c).map(cd => <div key={cd.id} className="text-sm bg-slate-50 rounded p-2">{cd.title}</div>)}</div>

function RunViewer() {
  const [runs, setRuns] = useState([{ thread_id: 'thread-a1b2c3d4', status: 'interrupted (awaiting approval)', progress: 8 }])
  return (
    <div><h3 className="text-xl font-semibold mb-3">Agent Run Viewer</h3><div className="space-y-3">{runs.map(r => <div key={r.thread_id} className="bg-white rounded-xl border p-3"><div className="flex justify-between text-sm"><span className="font-mono">{r.thread_id}</span><span className="badge">{r.status}</span></div><div className="mt-1 h-2 bg-slate-200 rounded w-full" /></div>)}</div></div>
  )
}

function Analytics() {
  const [a, setA] = useState({ replyRate: 0.4, hireRate: 0.08, connects: 13, p95Latency: 8.2, costPerProposal: 0.04 })
  useEffect(() => API.analytics().then(setA), [])
  return (
    <div><h3 className="text-xl font-semibold mb-3">Analytics</h3><div className="grid gap-4 md:grid-cols-2">
      <div className="bg-white rounded-xl p-4 border"><div className="text-2xl font-bold">{Math.round(a.replyRate * 100)}%</div><div className="text-xs text-slate-500">Reply rate</div></div>
      <div className="bg-white rounded-xl p-4 border"><div className="text-2xl font-bold">{Math.round(a.hireRate * 100)}%</div><div className="text-xs text-slate-500">Hire rate</div></div>
      <div className="bg-white rounded-xl p-4 border"><div className="text-2xl font-bold">{a.connects}</div><div className="text-xs text-slate-500">Connects spent</div></div>
      <div className="bg-white rounded-xl p-4 border"><div className="text-2xl font-bold">{a.p95Latency.toFixed(1)}s</div><div className="text-xs text-slate-500">p95 latency / proposal</div></div>
    </div>
    <p className="text-xs text-slate-400 mt-3">p95 latency {a.p95Latency}s, cost ${a.costPerProposal}/proposal (open-profile model).</p></div>
  )
}

function Settings() {
  const [auth, setAuth] = useState({ name: 'Freelancer', persona: 'AI/ML Engineer' })
  return (
    <div><h3 className="text-xl font-semibold mb-3">Settings</h3><div className="max-w-md space-y-3">
      <div className="bg-white rounded-xl p-4 border"><label className="text-sm font-medium">Name</label><input className="input mt-1" value={auth.name} onChange={e => setAuth({ ...auth, name: e.target.value })} /></div>
      <div className="bg-white rounded-xl p-4 border"><label className="text-sm font-medium">Persona</label><select className="input mt-1" value={auth.persona} onChange={e => setAuth({ ...auth, persona: e.target.value })}><option>AI/ML Engineer</option><option>Full-stack Web Developer</option><option>Data Analyst</option></select></div>
      <div className="bg-white rounded-xl p-4 border"><div className="flex items-center justify-between"><span>Autonomy level</span><span className="badge bg-slate-100 text-slate-600">Review every proposal</span></div><input type="range" className="mt-2" defaultValue={0} min={0} max={1} /><p className="text-xs text-slate-400 mt-1">Auto-skip low-fit jobs only; never auto-send.</p></div>
      <button className="btn-primary">Save settings</button>
    </div></div>
  )
}

// ---------------------------------------------------------------- App composer
export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [runningThread, setRunningThread] = useState<string | null>(null)
  const login = (name: string, persona: string) => {
    const u: User = { id: crypto.randomUUID(), name, persona }
    localStorage.setItem('gigbid_user', JSON.stringify(u)); setUser(u)
  }
  const logout = () => { localStorage.removeItem('gigbid_user'); setUser(null) }
  const value = { user, login, logout }
  const appValue = { runningThread, setRunningThread }
  return (
    <AuthCtx.Provider value={value}>
      <AppCtx.Provider value={appValue}>
        <BrowserRouter>
          <div className="min-h-screen bg-slate-50 text-slate-800">
            {!user ? <SignIn onLogin={login} /> : (
              <div className="flex min-h-screen">
                <Sidebar user={user} runningThread={runningThread} setRunningThread={setRunningThread} />
                <main className="flex-1 lg:ml-64 pb-16">
                  <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
                    <Routes>
                      <Route path="/" element={<Dashboard user={user} />} />
                      <Route path="/jobs" element={<JobInbox user={user} />} />
                      <Route path="/jobs/:id" element={<JobDetail user={user} />} />
                      <Route path="/proposals/:id" element={<ProposalStudio />} />
                      <Route path="/messages" element={<Messages user={user} />} />
                      <Route path="/board" element={<PipelineBoard />} />
                      <Route path="/analytics" element={<Analytics />} />
                      <Route path="/settings" element={<Settings />} />
                      <Route path="/runs" element={<RunViewer />} />
                    </Routes>
                  </div>
                </main>
              </div>
            )}
          </div>
        </BrowserRouter>
      </AppCtx.Provider>
    </AuthCtx.Provider>
  )
}

    ))}</div></div>
  )
}

function Messages({ user }: any) {
  const [msgs, setMsgs] = useState([{ role: 'client', text: 'Do you have capacity this week? React with availability.' }, { role: 'ai', text: 'Thanks for reaching out. I have capacity next week — two tentative slots.' }])
  const send = (e: any) => { e.preventDefault(); setMsgs([...msgs, { role: 'client', text: e.target.text.value }]); e.target.value = '' }
  return (
    <div className="max-w-2xl space-y-3">
      <h3 className="text-xl font-semibold">Messages</h3>
      {msgs.map(m => <div key={m.role + m.text} className={clsx('rounded-xl p-3', m.role === 'client' ? 'bg-slate-100' : 'bg-indigo-50 text-indigo-800')}>{m.text}</div>)}
      <form onSubmit={send} className="flex gap-2 mt-2"><input className="input flex-1" name="text" placeholder="Draft a reply (suggested replies shown; approve before send)" /><button className="btn-primary">Send (requires approval)</button></form>
    </div>
  )
}

      API.analyzeJob({ job_id: id, title: '', description: '', required_skills: [], budget: { min: 0, max: 0 } }).then(setDetail).catch(() => {})
    }
  }, [id])
  if (!job) return <p className="text-slate-500">Loading job…</p>
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between"><h3 className="text-xl font-semibold">{job.title}</h3><span className="badge bg-slate-100 text-slate-600">{job.job_id}</span></div>
      <p className="text-slate-600">{job.description}</p>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl p-4 border"><h4 className="font-semibold">Job Spec</h4><ul className="text-sm text-slate-600 space-y-1"><li className="grid grid-cols-2 gap-2"><span className="text-slate-400">Skills:</span><span className="font-mono">{job.required_skills?.join(', ')}</span></li><li className="grid grid-cols-2 gap-2"><span className="text-slate-400">Budget:</span><span className="font-mono">{job.budget_min}–{job.budget_max} {job.currency}</span></li><li className="grid grid-cols-2 gap-2"><span className="text-slate-400">Connects:</span><span className="font-mono">{job.connects_cost}</span></li></ul></div>
        <div className="bg-white rounded-xl p-4 border"><h4 className="font-semibold">Risk Report</h4><div>{badge(job.risk_report?.scam ? 'SCAM' : 'Low risk')}</div><p className="text-sm text-slate-600 mt-1">{job.risk_report?.explanation}</p></div>
      </div>
      {detail && (
        <div className="bg-white rounded-xl p-4 border"><h4 className="font-semibold">Analysis Results</h4><p className="text-sm text-slate-600 mt-1"><b>Decision:</b> {detail.decision} | <b>Price:</b> {detail.price_quote?.suggested_bid} {detail.price_quote?.currency}</p></div>
      )}
    </div>
  )
}

  </div>
) }
