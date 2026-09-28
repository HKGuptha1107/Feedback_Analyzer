import { useEffect, useMemo, useState } from 'react'
import {
  Activity, ArrowUpRight, Brain, Check, ChevronLeft, ChevronRight, CircleAlert,
  Database, FileSpreadsheet, FileUp, LayoutDashboard, LoaderCircle,
  MessageSquareText, Pin, Plus, RefreshCw, Search, Send, Sparkles, Trash2, Upload, X, Zap,
} from 'lucide-react'
import {
  analyzeFeedback, deleteConversationFeedback, fetchFeedback, fetchMemory, reflectMemory, retainMemory,
  searchMemory, submitFeedback, uploadCsv,
} from './api'
import type { Conversation, Feedback, ImportedFile, MemoryOverview, UploadSummary, View } from './types'

const navItems: Array<{ id: View; label: string; icon: typeof LayoutDashboard }> = [
  { id: 'overview', label: 'Command center', icon: LayoutDashboard },
  { id: 'feedback', label: 'Feedback explorer', icon: MessageSquareText },
  { id: 'memory', label: 'Memory inspector', icon: Brain },
  { id: 'assistant', label: 'Intelligence assistant', icon: Sparkles },
  { id: 'files', label: 'Imported files', icon: FileSpreadsheet },
  { id: 'conversations', label: 'Conversations', icon: MessageSquareText },
]

const sourceOptions = ['App Review', 'Support Ticket', 'Survey', 'Email', 'Feature Request', 'Interview', 'Social Media']
const categoryOptions = ['General', 'Performance', 'UI', 'Billing', 'Notifications', 'Integrations', 'Reporting']

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value))
}

function sentimentLabel(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function readWorkspace<T>(key: string, fallback: T): T {
  try { return JSON.parse(localStorage.getItem(key) ?? '') as T } catch { return fallback }
}

function writeWorkspace(key: string, value: unknown) {
  localStorage.setItem(key, JSON.stringify(value))
}

function App() {
  const [view, setView] = useState<View>('overview')
  const [feedback, setFeedback] = useState<Feedback[]>([])
  const [feedbackTotal, setFeedbackTotal] = useState(0)
  const [memory, setMemory] = useState<MemoryOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showIntake, setShowIntake] = useState(false)
  const [selected, setSelected] = useState<Feedback | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [importedFiles, setImportedFiles] = useState<ImportedFile[]>(() => readWorkspace<ImportedFile[]>('flowdesk-imported-files', []).filter((item) => Boolean(item.conversationId)))
  const [conversations, setConversations] = useState<Conversation[]>(() => readWorkspace('flowdesk-conversations', []))
  const [activeDatasetIds, setActiveDatasetIds] = useState<string[]>(() => readWorkspace<string[]>('flowdesk-active-datasets', []))

  async function loadData(datasetIds = activeDatasetIds) {
    setRefreshing(true)
    setError('')
    try {
      const [feedbackResult, memoryResult] = await Promise.all([
        fetchFeedback({ page: 1, limit: 100, conversation_ids: datasetIds }),
        fetchMemory(),
      ])
      setFeedback(feedbackResult.items)
      setFeedbackTotal(feedbackResult.total)
      setMemory(memoryResult)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to connect to the API')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => { void loadData(activeDatasetIds) }, [activeDatasetIds])
  useEffect(() => { writeWorkspace('flowdesk-imported-files', importedFiles) }, [importedFiles])
  useEffect(() => { writeWorkspace('flowdesk-conversations', conversations) }, [conversations])
  useEffect(() => { writeWorkspace('flowdesk-active-datasets', activeDatasetIds) }, [activeDatasetIds])

  const metrics = useMemo(() => {
    const negative = feedback.filter((item) => item.sentiment === 'negative').length
    const recurring = feedback.filter((item) => item.analysis_result?.is_recurring).length
    const urgent = feedback.filter((item) => ['high', 'critical'].includes(item.analysis_result?.urgency ?? '')).length
    const average = feedback.filter((item) => item.rating).reduce((sum, item) => sum + (item.rating ?? 0), 0) / Math.max(1, feedback.filter((item) => item.rating).length)
    return { negative, recurring, urgent, average }
  }, [feedback])

  async function handleCreated(item: Feedback) {
    setFeedback((current) => [item, ...current])
    setFeedbackTotal((total) => total + 1)
    setShowIntake(false)
    setView('feedback')
    setSelected(item)
    void loadData()
  }

  function handleUploaded(fileName: string, summary: UploadSummary) {
    setImportedFiles((current) => [{ id: crypto.randomUUID(), conversationId: summary.conversation_id, name: fileName, uploadedAt: new Date().toISOString(), uploaded: summary.uploaded, successful: summary.successful, failed: summary.failed }, ...current])
    setActiveDatasetIds([summary.conversation_id])
    setView('feedback')
    void loadData([summary.conversation_id])
  }

  function handleConversation(query: string, response: string, workspace: 'assistant' | 'memory' = 'assistant') {
    setConversations((current) => [{ id: crypto.randomUUID(), title: query.length > 58 ? `${query.slice(0, 58)}...` : query, createdAt: new Date().toISOString(), pinned: false, workspace, datasetIds: activeDatasetIds, messages: [{ role: 'user', content: query, createdAt: new Date().toISOString() }, { role: 'agent', content: response, createdAt: new Date().toISOString() }] }, ...current])
  }

  function toggleConversationPin(id: string) { setConversations((current) => current.map((item) => item.id === id ? { ...item, pinned: !item.pinned } : item)) }
  function deleteConversation(id: string) { setConversations((current) => current.filter((item) => item.id !== id)) }
  async function deleteImportedFile(file: ImportedFile) { await deleteConversationFeedback(file.conversationId); setImportedFiles((current) => current.filter((item) => item.id !== file.id)); if (activeDatasetIds.includes(file.conversationId)) { const remaining = activeDatasetIds.filter((id) => id !== file.conversationId); setActiveDatasetIds(remaining); if (!remaining.length) { setFeedback([]); setFeedbackTotal(0) } } }
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark"><span>F</span><div><strong>Feedback Analyzer</strong><small>Product intelligence</small></div></div>
        <div className="workspace-switcher"><span className="status-dot" /> Feedback Analyzer <ChevronRight size={14} /></div>
        <nav className="nav-list" aria-label="Main navigation">
          <p className="nav-kicker">Workspace</p>
          {navItems.map(({ id, label, icon: Icon }) => (
            <button key={id} className={`nav-item ${view === id ? 'active' : ''}`} onClick={() => setView(id)}>
              <Icon size={18} strokeWidth={1.8} /><span>{label}</span>{id === 'feedback' && feedbackTotal > 0 && <em>{feedbackTotal}</em>}
            </button>
          ))}
        </nav>
        {conversations.some((item) => item.pinned) && <div className="sidebar-pinned"><p className="nav-kicker">Pinned</p>{conversations.filter((item) => item.pinned).slice(0, 5).map((item) => <button className="sidebar-conversation" key={item.id} onClick={() => setView('conversations')}><MessageSquareText size={14} /><span>{item.title}</span></button>)}</div>}
        <div className="sidebar-bottom">
          <div className="memory-status"><div className="memory-orbit"><Brain size={17} /></div><div><strong>Hindsight memory</strong><span>{memory?.is_live_service ? 'Live service connected' : 'Local fallback active'}</span></div></div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar"><div className="breadcrumbs"><span>Workspace</span><ChevronRight size={14} /><strong>{navItems.find((item) => item.id === view)?.label}</strong></div><div className="top-actions"><button className="primary-button compact" onClick={() => setShowIntake(true)}><Plus size={16} /> Add feedback</button></div></header>
        {error && <div className="error-banner"><CircleAlert size={18} /><span>{error}</span><button onClick={() => setError('')}><X size={16} /></button></div>}
        {loading ? <LoadingState /> : view === 'overview' ? <Overview feedback={feedback} total={feedbackTotal} metrics={metrics} onOpenFeedback={() => setView('feedback')} onSelect={setSelected} /> : view === 'feedback' ? <FeedbackExplorer initialItems={feedback} total={feedbackTotal} conversationIds={activeDatasetIds} conversationOptions={importedFiles} onConversationChange={setActiveDatasetIds} onSelect={setSelected} onOpenIntake={() => setShowIntake(true)} /> : view === 'memory' ? <MemoryInspector memory={memory} onRefresh={() => void loadData()} onOpenUpload={() => setShowIntake(true)} onActivity={(query, response) => handleConversation(query, response, 'memory')} /> : view === 'files' ? <ImportedFilesPage files={importedFiles} onOpenUpload={() => setShowIntake(true)} onDelete={deleteImportedFile} /> : view === 'conversations' ? <ConversationsPage conversations={conversations} onPin={toggleConversationPin} onDelete={deleteConversation} onOpenAssistant={() => setView('assistant')} /> : <Assistant onConversation={handleConversation} />}
      </main>
      {selected && <FeedbackDetail feedback={selected} onClose={() => setSelected(null)} onUpdated={(item) => { setSelected(item); setFeedback((items) => items.map((current) => current.id === item.id ? item : current)) }} />}
      {showIntake && <IntakeModal onClose={() => setShowIntake(false)} onCreated={handleCreated} onUploaded={handleUploaded} />}
    </div>
  )
}

function LoadingState() { return <div className="loading-state"><LoaderCircle className="spin" size={26} /><span>Loading intelligence workspace...</span></div> }

function Overview({ feedback, total, metrics, onOpenFeedback, onSelect }: { feedback: Feedback[]; total: number; metrics: { negative: number; recurring: number; urgent: number; average: number }; onOpenFeedback: () => void; onSelect: (item: Feedback) => void }) {
  const sentimentTotal = Math.max(1, feedback.length)
  const categories = Object.entries(feedback.reduce<Record<string, number>>((acc, item) => { acc[item.category] = (acc[item.category] ?? 0) + 1; return acc }, {})).sort((a, b) => b[1] - a[1]).slice(0, 5)
  return <div className="page animate-in">
    <div className="page-heading"><div><p className="eyebrow">MONDAY, SEPTEMBER 28, 2026</p><h1>Good morning, product team.</h1><p className="subheading">Your customer signal is concentrated around a few clear opportunities.</p></div><button className="secondary-button" onClick={onOpenFeedback}><Upload size={16} /> Ingest feedback</button></div>
    <section className="hero-band"><div><span className="section-label"><Zap size={14} /> Signal overview</span><h2>Feedback is telling a story.<br /><span>Here is the useful part.</span></h2><p>Track the moments that change customer sentiment, then carry the context forward with persistent memory.</p></div><div className="hero-spark"><div className="spark-line"><i style={{ height: '34%' }} /><i style={{ height: '49%' }} /><i style={{ height: '42%' }} /><i style={{ height: '68%' }} /><i style={{ height: '55%' }} /><i style={{ height: '78%' }} /><i style={{ height: '91%' }} /><i style={{ height: '82%' }} /><i style={{ height: '100%' }} /></div><span>Recent feedback volume</span></div></section>
    <div className="metric-grid"><MetricCard label="Total feedback" value={total.toLocaleString()} change="All captured signals" icon={<MessageSquareText />} tone="blue" /><MetricCard label="Negative signals" value={metrics.negative.toString()} change={`${Math.round((metrics.negative / sentimentTotal) * 100)}% of current view`} icon={<CircleAlert />} tone="coral" /><MetricCard label="Recurring issues" value={metrics.recurring.toString()} change="Matched to memory" icon={<RefreshCw />} tone="violet" /><MetricCard label="Average rating" value={metrics.average ? metrics.average.toFixed(1) : '—'} change="Out of 5.0" icon={<Activity />} tone="lime" /></div>
    <div className="content-grid two-col"><section className="panel"><div className="panel-heading"><div><p className="eyebrow">THE SIGNAL BOARD</p><h3>Emerging issues & themes</h3></div><button className="text-button" onClick={onOpenFeedback}>View all <ArrowUpRight size={14} /></button></div><div className="issue-list">{feedback.slice(0, 4).map((item) => <button className="issue-row" key={item.id} onClick={() => onSelect(item)}><div className={`issue-icon ${item.sentiment}`}><CircleAlert size={16} /></div><div className="issue-copy"><strong>{item.analysis_result?.topic ?? item.category}</strong><span>{item.analysis_result?.short_summary ?? item.feedback_text}</span></div><div className="issue-meta"><span className={`tag ${item.sentiment}`}>{sentimentLabel(item.sentiment)}</span><small>{formatDate(item.feedback_date)}</small></div></button>)}{feedback.length === 0 && <EmptyState text="No feedback yet. Ingest your first customer signal." />}</div></section><section className="panel"><div className="panel-heading"><div><p className="eyebrow">DISTRIBUTION</p><h3>Where the signal lives</h3></div><Database size={18} className="panel-icon" /></div><div className="distribution"><div className="donut" style={{ background: `conic-gradient(var(--coral) 0 ${metrics.negative / sentimentTotal * 100}%, var(--lime) ${metrics.negative / sentimentTotal * 100}% ${(metrics.negative + feedback.filter((item) => item.sentiment === 'positive').length) / sentimentTotal * 100}%, var(--line-strong) 0)` }}><div><strong>{feedback.length}</strong><span>signals</span></div></div><div className="legend"><div><span className="legend-dot coral" /> Negative <strong>{metrics.negative}</strong></div><div><span className="legend-dot lime" /> Positive <strong>{feedback.filter((item) => item.sentiment === 'positive').length}</strong></div><div><span className="legend-dot neutral" /> Neutral <strong>{feedback.filter((item) => item.sentiment === 'neutral').length}</strong></div></div></div><div className="category-bars">{categories.map(([name, count]) => <div className="bar-row" key={name}><span>{name}</span><div><i style={{ width: `${count / Math.max(1, categories[0]?.[1] ?? 1) * 100}%` }} /></div><strong>{count}</strong></div>)}</div></section></div>
  </div>
}

function MetricCard({ label, value, change, icon, tone }: { label: string; value: string; change: string; icon: React.ReactNode; tone: string }) { return <div className="metric-card"><div className={`metric-icon ${tone}`}>{icon}</div><span>{label}</span><strong>{value}</strong><small>{change}</small></div> }
function EmptyState({ text }: { text: string }) { return <div className="empty-state"><MessageSquareText size={22} /><span>{text}</span></div> }

function FeedbackExplorer({ initialItems, total, conversationIds, conversationOptions, onConversationChange, onSelect, onOpenIntake }: { initialItems: Feedback[]; total: number; conversationIds: string[]; conversationOptions: ImportedFile[]; onConversationChange: (ids: string[]) => void; onSelect: (item: Feedback) => void; onOpenIntake: () => void }) {
  const [items, setItems] = useState(initialItems)
  const [search, setSearch] = useState('')
  const [sentiment, setSentiment] = useState('')
  const [source, setSource] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  useEffect(() => { setItems(initialItems) }, [initialItems])
  async function applyFilters(nextPage = 1, selectedConversations = conversationIds) { setLoading(true); try { const result = await fetchFeedback({ search, sentiment, source, conversation_ids: selectedConversations, page: nextPage, limit: 20 }); setItems(result.items); setPage(nextPage) } finally { setLoading(false) } }
  return <div className="page animate-in"><div className="page-heading"><div><p className="eyebrow">RAW SIGNAL + TRIAGE</p><h1>Feedback explorer</h1><p className="subheading">Each conversation stays isolated so separate CSV datasets never mix.</p></div><button className="primary-button" onClick={onOpenIntake}><Plus size={17} /> Add feedback</button></div><section className="panel table-panel"><div className="filter-row"><div className="search-box"><Search size={17} /><input placeholder="Search feedback or customer" value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && void applyFilters()} /></div><fieldset className="dataset-checks"><legend>Datasets</legend><label className="dataset-check"><input type="checkbox" checked={!conversationIds.length} onChange={() => { onConversationChange([]); void applyFilters(1, []) }} /><span>All datasets</span></label>{conversationOptions.map((file) => <label className="dataset-check" key={file.conversationId}><input type="checkbox" checked={conversationIds.includes(file.conversationId)} onChange={(event) => { const next = event.target.checked ? [...conversationIds, file.conversationId] : conversationIds.filter((id) => id !== file.conversationId); onConversationChange(next); void applyFilters(1, next) }} /><span>{file.name}</span><em>{file.successful}</em></label>)}</fieldset><select value={sentiment} onChange={(event) => { setSentiment(event.target.value); void applyFilters() }}><option value="">All sentiment</option><option value="negative">Negative</option><option value="neutral">Neutral</option><option value="positive">Positive</option></select><select value={source} onChange={(event) => { setSource(event.target.value); void applyFilters() }}><option value="">All sources</option>{sourceOptions.map((option) => <option key={option}>{option}</option>)}</select><button className="icon-button" title="Apply filters" onClick={() => void applyFilters()}><Search size={17} /></button></div><div className="table-wrap"><table><thead><tr><th>Customer signal</th><th>Conversation</th><th>Theme</th><th>Sentiment</th><th>Urgency</th><th>Date</th><th /></tr></thead><tbody>{loading ? <tr><td colSpan={7} className="table-message"><LoaderCircle className="spin" size={19} /> Refreshing signals...</td></tr> : items.map((item) => <tr key={item.id} onClick={() => onSelect(item)}><td><div className="customer-cell"><div className="avatar small">{item.customer_name.slice(0, 2).toUpperCase()}</div><div><strong>{item.customer_name}</strong><span>{item.feedback_text}</span></div></div></td><td><span className="conversation-chip">{item.conversation_id?.slice(0, 8) ?? 'legacy'}</span></td><td><span className="topic-text">{item.analysis_result?.topic ?? item.category}</span></td><td><span className={`tag ${item.sentiment}`}>{sentimentLabel(item.sentiment)}</span></td><td><span className={`urgency ${item.analysis_result?.urgency ?? 'low'}`}>{item.analysis_result?.urgency ?? 'pending'}</span></td><td className="date-cell">{formatDate(item.feedback_date)}</td><td><ChevronRight size={16} className="row-chevron" /></td></tr>)}{!loading && items.length === 0 && <tr><td colSpan={7}><EmptyState text="No feedback matches these filters." /></td></tr>}</tbody></table></div><div className="table-footer"><span>Showing {items.length} of {total.toLocaleString()} feedback items</span><div><button className="pagination-button" disabled={page <= 1} onClick={() => void applyFilters(page - 1)}><ChevronLeft size={16} /></button><span>Page {page}</span><button className="pagination-button" disabled={items.length < 20} onClick={() => void applyFilters(page + 1)}><ChevronRight size={16} /></button></div></div></section></div>
}

function FeedbackDetail({ feedback, onClose, onUpdated }: { feedback: Feedback; onClose: () => void; onUpdated: (item: Feedback) => void }) {
  const [analyzing, setAnalyzing] = useState(false)
  async function refreshAnalysis() { setAnalyzing(true); try { onUpdated(await analyzeFeedback(feedback.id)) } finally { setAnalyzing(false) } }
  return <div className="drawer-backdrop" onClick={onClose}><aside className="detail-drawer" onClick={(event) => event.stopPropagation()}><div className="drawer-header"><div><p className="eyebrow">FEEDBACK DETAIL</p><h2>Signal analysis</h2></div><button className="icon-button" onClick={onClose}><X size={18} /></button></div><div className="detail-customer"><div className="avatar large">{feedback.customer_name.slice(0, 2).toUpperCase()}</div><div><strong>{feedback.customer_name}</strong><span>{feedback.source} · {formatDate(feedback.feedback_date)}</span></div><span className={`tag ${feedback.sentiment}`}>{sentimentLabel(feedback.sentiment)}</span></div><blockquote>“{feedback.feedback_text}”</blockquote><div className="detail-section"><div className="section-title"><span>Automated triage</span><button className="text-button" onClick={() => void refreshAnalysis()} disabled={analyzing}>{analyzing ? <LoaderCircle size={14} className="spin" /> : <RefreshCw size={14} />} Re-analyze</button></div>{feedback.analysis_result ? <><div className="analysis-hero"><div><span>Primary theme</span><strong>{feedback.analysis_result.topic}</strong></div><div className={`urgency-badge ${feedback.analysis_result.urgency}`}>{feedback.analysis_result.urgency} urgency</div></div><p className="analysis-summary">{feedback.analysis_result.short_summary}</p><div className="detail-grid"><div><span>Issue type</span><strong>{feedback.analysis_result.issue_type.replace('_', ' ')}</strong></div><div><span>Recurring</span><strong>{feedback.analysis_result.is_recurring ? 'Matched memory' : 'New pattern'}</strong></div><div><span>Category</span><strong>{feedback.category}</strong></div><div><span>Rating</span><strong>{feedback.rating ? `${feedback.rating} / 5` : 'Not rated'}</strong></div></div><div className="entity-list">{feedback.analysis_result.entities.map((entity) => <span key={entity}>{entity}</span>)}</div></> : <div className="empty-state compact"><CircleAlert size={18} /><span>No triage available yet.</span></div>}</div></aside></div>
}

function IntakeModal({ onClose, onCreated, onUploaded }: { onClose: () => void; onCreated: (item: Feedback) => void; onUploaded: (fileName: string, summary: UploadSummary) => void }) {
  const [mode, setMode] = useState<'single' | 'csv'>('single')
  const [form, setForm] = useState({ customer_name: '', source: 'Support Ticket', feedback_text: '', rating: '', category: 'General' })
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState<'success' | 'error'>('success')
  async function submit() { setBusy(true); setMessage(''); setMessageType('success'); try { if (mode === 'csv') { if (!file) throw new Error('Choose a CSV file first'); const result = await uploadCsv(file); setMessage(`${result.successful} feedback items ingested successfully${result.failed ? `; ${result.failed} rows failed` : ''}.`); onUploaded(file.name, result); setTimeout(onClose, 900) } else { const item = await submitFeedback({ ...form, rating: form.rating ? Number(form.rating) : null, customer_name: form.customer_name || 'Anonymous', feedback_text: form.feedback_text }); onCreated(item) } } catch (err) { setMessageType('error'); setMessage(err instanceof Error ? err.message : 'Unable to submit feedback') } finally { setBusy(false) } }
  return <div className="modal-backdrop" onClick={onClose}><div className="modal" onClick={(event) => event.stopPropagation()}><div className="modal-header"><div><p className="eyebrow">CAPTURE SIGNAL</p><h2>Bring feedback into focus</h2></div><button className="icon-button" onClick={onClose}><X size={18} /></button></div><div className="segmented"><button className={mode === 'single' ? 'selected' : ''} onClick={() => setMode('single')}><MessageSquareText size={15} /> Single signal</button><button className={mode === 'csv' ? 'selected' : ''} onClick={() => setMode('csv')}><FileUp size={15} /> CSV batch</button></div>{mode === 'single' ? <div className="form-grid"><label>Customer name<input value={form.customer_name} onChange={(event) => setForm({ ...form, customer_name: event.target.value })} placeholder="Anonymous" /></label><label>Source<select value={form.source} onChange={(event) => setForm({ ...form, source: event.target.value })}>{sourceOptions.map((option) => <option key={option}>{option}</option>)}</select></label><label>Category<select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>{categoryOptions.map((option) => <option key={option}>{option}</option>)}</select></label><label>Rating<input type="number" min="1" max="5" value={form.rating} onChange={(event) => setForm({ ...form, rating: event.target.value })} placeholder="1–5" /></label><label className="full">What did they say?<textarea rows={5} value={form.feedback_text} onChange={(event) => setForm({ ...form, feedback_text: event.target.value })} placeholder="Describe the customer signal..." /></label></div> : <label className="drop-zone"><Upload size={27} /><strong>{file ? file.name : 'Drop a CSV here or choose a file'}</strong><span>Rows are triaged automatically. Accepted format: .csv</span><input type="file" accept=".csv,text/csv" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label>}{message && <div className={`inline-message ${messageType}`}>{messageType === 'success' ? <Check size={16} /> : <CircleAlert size={16} />} {message}</div>}<div className="modal-actions"><button className="secondary-button" onClick={onClose}>Cancel</button><button className="primary-button" onClick={() => void submit()} disabled={busy}>{busy ? <LoaderCircle size={16} className="spin" /> : mode === 'csv' ? <Upload size={16} /> : <Send size={16} />} {busy ? 'Processing...' : mode === 'csv' ? 'Ingest CSV' : 'Analyze signal'}</button></div></div></div>
}

function ImportedFilesPage({ files, onOpenUpload, onDelete }: { files: ImportedFile[]; onOpenUpload: () => void; onDelete: (file: ImportedFile) => Promise<void> }) {
  return <div className="page animate-in"><div className="page-heading"><div><p className="eyebrow">DATA WORKSPACE</p><h1>Imported files</h1><p className="subheading">A durable record of every CSV batch added to the intelligence workspace.</p></div><button className="primary-button" onClick={onOpenUpload}><Upload size={16} /> Upload CSV</button></div><section className="panel file-history-panel"><div className="panel-heading"><div><p className="eyebrow">INGESTION HISTORY</p><h3>Previous imports</h3></div><FileSpreadsheet size={18} className="panel-icon" /></div>{files.length ? <div className="file-list">{files.map((file) => <div className="file-row" key={file.id}><div className="file-icon"><FileSpreadsheet size={18} /></div><div className="file-copy"><strong>{file.name}</strong><span>Conversation {file.conversationId.slice(0, 8)} · Imported {formatDate(file.uploadedAt)}</span></div><div className="file-count"><strong>{file.successful}</strong><span>success</span></div>{file.failed > 0 && <div className="file-count failed"><strong>{file.failed}</strong><span>failed</span></div>}<button className="icon-button danger-button" title={`Delete ${file.name} and its feedback`} onClick={() => void onDelete(file)}><Trash2 size={16} /></button></div>)}</div> : <EmptyState text="No CSV imports recorded yet. Upload your first batch to start the history." />}</section></div>
}

function ConversationsPage({ conversations, onPin, onDelete, onOpenAssistant }: { conversations: Conversation[]; onPin: (id: string) => void; onDelete: (id: string) => void; onOpenAssistant: () => void }) {
  return <div className="page animate-in"><div className="page-heading"><div><p className="eyebrow">AGENT WORKSPACE</p><h1>Conversations</h1><p className="subheading">Your questions and the intelligence agent's answers, kept together for later decisions.</p></div><button className="primary-button" onClick={onOpenAssistant}><Plus size={16} /> New conversation</button></div><section className="panel conversation-history-panel"><div className="panel-heading"><div><p className="eyebrow">HISTORY</p><h3>All conversations</h3></div><MessageSquareText size={18} className="panel-icon" /></div>{conversations.length ? <div className="conversation-list">{conversations.map((conversation) => <article className="conversation-row" key={conversation.id}><div className="conversation-icon"><MessageSquareText size={17} /></div><div className="conversation-copy"><strong>{conversation.title}</strong><span>{formatDate(conversation.createdAt)} · {conversation.messages.length} messages</span><div className="conversation-meta"><em className={`workspace-badge ${conversation.workspace ?? 'assistant'}`}>{conversation.workspace === 'memory' ? 'Memory inspector' : 'Intelligence assistant'}</em><small>{conversation.datasetIds?.length ? `${conversation.datasetIds.length} dataset${conversation.datasetIds.length === 1 ? '' : 's'} selected` : 'All datasets'}</small></div><p>{conversation.messages.find((message) => message.role === 'agent')?.content.slice(0, 180) ?? 'No agent response yet.'}</p></div><div className="conversation-actions"><button className={`icon-button ${conversation.pinned ? 'pinned' : ''}`} title={conversation.pinned ? 'Unpin conversation' : 'Pin conversation'} onClick={() => onPin(conversation.id)}><Pin size={16} /></button><button className="icon-button danger-button" title="Delete conversation" onClick={() => onDelete(conversation.id)}><Trash2 size={16} /></button></div></article>)}</div> : <EmptyState text="No conversations yet. Ask the intelligence assistant your first question." />}</section></div>
}

function MemoryWorkflowCharts({ memory, onOpenUpload }: { memory: MemoryOverview | null; onOpenUpload: () => void }) {
  const memories = memory?.memories ?? []
  const activity = Object.entries(memories.reduce<Record<string, number>>((counts, item) => { const date = String(item.timestamp ?? '').slice(0, 10) || 'undated'; counts[date] = (counts[date] ?? 0) + 1; return counts }, {})).sort(([a], [b]) => a.localeCompare(b)).slice(-7)
  const maxActivity = Math.max(1, ...activity.map(([, count]) => count))
  const types = Object.entries(memory?.memory_types ?? {}).sort(([, a], [, b]) => b - a)
  const maxType = Math.max(1, ...types.map(([, count]) => count))
  const proofTotal = memories.reduce((sum, item) => sum + Number(item.proof_count ?? 1), 0)
  return <section className="memory-workflow"><div className="memory-chart panel"><div className="panel-heading"><div><p className="eyebrow">AGENT HISTORY</p><h3>Previous memory work</h3></div><Activity size={18} className="panel-icon" /></div><p className="chart-caption">Retained observations by the day the agents created or consolidated them.</p>{activity.length ? <div className="activity-chart">{activity.map(([date, count]) => <div className="activity-column" key={date}><div className="activity-bar-wrap"><i style={{ height: `${Math.max(8, count / maxActivity * 100)}%` }}><b>{count}</b></i></div><span>{date === 'undated' ? '—' : date.slice(5)}</span></div>)}</div> : <EmptyState text="No agent memory work recorded yet." />}</div><div className="memory-chart panel"><div className="panel-heading"><div><p className="eyebrow">MEMORY MIX</p><h3>What the agent remembers</h3></div><Brain size={18} className="panel-icon" /></div><p className="chart-caption">{proofTotal} total evidence proofs across {memories.length} retained observations.</p>{types.length ? <div className="type-chart">{types.map(([type, count]) => <div className="type-chart-row" key={type}><div><span>{type.replaceAll('_', ' ')}</span><strong>{count}</strong></div><div className="type-track"><i style={{ width: `${count / maxType * 100}%` }} /></div></div>)}</div> : <EmptyState text="Memory types will appear after agent work is retained." />}</div><div className="memory-upload-card"><div className="upload-card-icon"><FileUp size={20} /></div><p className="eyebrow">NEW MEMORY WORKFLOW</p><h3>Upload the next CSV batch</h3><p>Bring in fresh customer signals, triage them, and return here to compare the new memory against previous agent work.</p><button className="primary-button" onClick={onOpenUpload}><Upload size={16} /> Upload CSV batch</button></div></section>
}

function MemoryInspector({ memory, onRefresh, onOpenUpload, onActivity }: { memory: MemoryOverview | null; onRefresh: () => void; onOpenUpload: () => void; onActivity: (query: string, response: string) => void }) { const [query, setQuery] = useState(''); const [results, setResults] = useState<Array<Record<string, unknown>>>([]); const [busy, setBusy] = useState(false); async function search() { if (query.trim().length < 2) return; setBusy(true); try { const nextResults = await searchMemory(query); setResults(nextResults); onActivity(`Memory recall: ${query}`,  nextResults.length ? nextResults.map((item) => String(item.text ?? item.content ?? '')).join('\\n') : 'No matching memories found.') } finally { setBusy(false) } } return <div className="page animate-in"><div className="page-heading"><div><p className="eyebrow">HINDSIGHT · TEMPR MEMORY</p><h1>Memory inspector</h1><p className="subheading">See what the product intelligence layer remembers beyond individual rows.</p></div><button className="secondary-button" onClick={onRefresh}><RefreshCw size={16} /> Refresh bank</button></div><div className="memory-overview"><div className="memory-stat"><div className="memory-orbit large"><Brain size={21} /></div><div><span>Bank status</span><strong>{memory?.is_live_service ? 'Live Hindsight service' : 'Local memory fallback'}</strong><small>{memory?.bank_id ?? 'flowdesk-feedback-bank'}</small></div></div><div><span>Stored observations</span><strong>{memory?.total_memories ?? 0}</strong></div>{Object.entries(memory?.memory_types ?? {}).slice(0, 3).map(([type, count]) => <div key={type}><span>{type.replace('_', ' ')}</span><strong>{count}</strong></div>)}</div><MemoryWorkflowCharts memory={memory} onOpenUpload={onOpenUpload} /><section className="content-grid two-col memory-grid"><div className="panel"><div className="panel-heading"><div><p className="eyebrow">RECALL</p><h3>Search the memory bank</h3></div><Search size={18} className="panel-icon" /></div><div className="search-box wide"><Search size={17} /><input placeholder="e.g. recurring upload complaints" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && void search()} /><button onClick={() => void search()}>{busy ? <LoaderCircle size={15} className="spin" /> : 'Recall'}</button></div><div className="memory-results">{results.length ? results.map((result, index) => <div className="memory-result" key={index}><span className="memory-result-type">{String(result.memory_type ?? 'observation')}</span><p>{String(result.content ?? result.text ?? result.observation ?? JSON.stringify(result))}</p><small>{result.proof_count ? `${result.proof_count} proofs` : 'Remembered signal'}</small></div>) : <EmptyState text="Search for a theme, pain point, or release memory." />}</div></div><div className="panel"><div className="panel-heading"><div><p className="eyebrow">OBSERVATIONS</p><h3>Recent high-signal memories</h3></div><Zap size={18} className="panel-icon" /></div><div className="memory-results">{memory?.memories?.length ? memory.memories.slice(0, 6).map((item, index) => <div className="memory-result" key={index}><span className="memory-result-type">{String(item.memory_type ?? 'observation')}</span><p>{String(item.content ?? item.text ?? JSON.stringify(item))}</p></div>) : <EmptyState text="No retained memories yet. Add one from the assistant workflow." />}</div></div></section></div> }

function Assistant({ onConversation }: { onConversation: (query: string, response: string) => void }) { const [query, setQuery] = useState(''); const [context, setContext] = useState(''); const [response, setResponse] = useState<Record<string, unknown> | null>(null); const [busy, setBusy] = useState(false); const [memoryText, setMemoryText] = useState(''); const [saved, setSaved] = useState(false); async function ask() { if (query.trim().length < 2) return; setBusy(true); setSaved(false); try { const nextResponse = await reflectMemory(query, context); setResponse(nextResponse); onConversation(query, String(nextResponse.reflection ?? nextResponse.answer ?? nextResponse.summary ?? 'Agent response recorded.')) } finally { setBusy(false) } } async function save() { if (!memoryText.trim()) return; await retainMemory({ content: memoryText, context: query, tags: ['assistant', 'product-intelligence'], memory_type: 'observation' }); setSaved(true); setMemoryText('') } return <div className="page animate-in"><div className="page-heading"><div><p className="eyebrow">PRODUCT INTELLIGENCE AGENT</p><h1>Ask the signal, not the spreadsheet.</h1><p className="subheading">Reflect across customer feedback and persistent memory to make the next decision clearer.</p></div></div><div className="assistant-layout"><section className="assistant-prompt"><div className="assistant-badge"><Sparkles size={17} /> Hindsight reflection</div><h2>What do you want to understand?</h2><textarea value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Which customer pain point should we prioritize next?" rows={5} /><label>Optional context<input value={context} onChange={(event) => setContext(event.target.value)} placeholder="Add a release, segment, or time period" /></label><button className="primary-button full-button" onClick={() => void ask()} disabled={busy}>{busy ? <LoaderCircle size={17} className="spin" /> : <Send size={17} />} {busy ? 'Reflecting across memory...' : 'Run reflection'}</button></section><section className="assistant-response"><div className="panel-heading"><div><p className="eyebrow">ANALYSIS OUTPUT</p><h3>{response ? 'The intelligence layer says' : 'Your answer will appear here'}</h3></div><Brain size={19} className="panel-icon" /></div>{response ? <><div className="response-copy">{String(response.reflection ?? response.answer ?? response.summary ?? JSON.stringify(response))}</div><div className="response-meta"><span><Check size={14} /> Grounded in memory</span><span>{String(response.bank_id ?? 'flowdesk-feedback-bank')}</span></div><div className="retain-box"><label>Retain a high-signal observation<textarea rows={3} value={memoryText} onChange={(event) => setMemoryText(event.target.value)} placeholder="Capture the conclusion your team should remember..." /></label><button className="secondary-button" onClick={() => void save()}>{saved ? <><Check size={15} /> Saved to memory</> : <><Database size={15} /> Retain observation</>}</button></div></> : <div className="assistant-empty"><div className="assistant-empty-icon"><Sparkles size={22} /></div><p>Ask a question about recurring issues, customer pain, or how sentiment is changing. The assistant will synthesize what the workspace has learned.</p></div>}</section></div></div> }

export default App
