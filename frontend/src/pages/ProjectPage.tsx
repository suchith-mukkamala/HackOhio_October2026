import { useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Github, Sparkles } from 'lucide-react'
import NewProject from './NewProject'
import Avatar from '../components/Avatar'
import { LogBody } from './Feed'
import { ApiError, api, post } from '../lib/api'
import { useMe } from '../lib/auth'
import type { Comment, HelpRequest, LogEntry, Project, User } from '../lib/types'

interface ProjectData {
  project: Project
  members: { role: string; user: User }[]
  timeline: LogEntry[]
  help_requests: HelpRequest[]
  comments: Comment[]
}

type Draft = Pick<LogEntry, 'week_label' | 'title' | 'built' | 'learned' | 'stuck' | 'skills' | 'source'> & {
  commit_shas?: string[]
}

const Label = ({ children }: { children: string }) => (
  <h2 className="mb-3 font-mono text-sm text-muted">{`// ${children}`}</h2>
)

const day = (d?: string) => (d ? new Date(d + 'T00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '?')

// "Week 3 of 6" from the project's start and end dates
function weekOf(p: Project) {
  if (!p.start_date || !p.end_date) return null
  const start = new Date(p.start_date).getTime()
  const total = Math.max(1, Math.round((new Date(p.end_date).getTime() - start) / 6048e5))
  const now = Math.min(total, Math.max(1, Math.ceil((Date.now() - start) / 6048e5)))
  return { now, total }
}

const lines = (s: string) => s.split('\n').map((l) => l.trim()).filter(Boolean)

function LogEditor({ project, log, onDone }: { project: Project; log?: LogEntry; onDone: () => void }) {
  const blank: Draft = { week_label: `Week of ${day(new Date().toISOString().slice(0, 10))}`, title: '', built: [], learned: [], stuck: [], skills: [], source: 'manual' }
  const [draft, setDraft] = useState<Draft>(log ?? blank)
  const [status, setStatus] = useState('')
  const [saving, setSaving] = useState(false)

  async function generate() {
    setStatus('Reading your commits…')
    try {
      setDraft(await post<Draft>(`/projects/${project.id}/logs/draft`))
      setStatus('Draft ready. Edit anything that isn’t right, then publish.')
    } catch (e) {
      setStatus(e instanceof ApiError ? e.message : 'Could not draft this log.')
    }
  }

  async function publish() {
    setSaving(true); setStatus('')
    try {
      const body = { ...draft, built: lines(draft.built.join('\n')), learned: lines(draft.learned.join('\n')), stuck: lines(draft.stuck.join('\n')) }
      if (log) await api(`/projects/${project.id}/logs/${log.id}`, { method: 'PUT', body: JSON.stringify(body) })
      else await post(`/projects/${project.id}/logs`, body)
      onDone()
    } catch (error) { setStatus(error instanceof Error ? error.message : 'Could not save this log.') }
    finally { setSaving(false) }
  }

  const field = 'w-full rounded-lg bg-tile px-3 py-2 text-sm placeholder:text-muted focus:ring-1 focus:ring-accent focus:outline-none'
  const list = (key: 'built' | 'learned' | 'stuck', placeholder: string) => (
    <textarea
      id={`log-${key}`}
      rows={3}
      placeholder={placeholder}
      value={draft[key].join('\n')}
      onChange={(e) => setDraft({ ...draft, [key]: e.target.value.split('\n') })}
      onBlur={(e) => setDraft({ ...draft, [key]: lines(e.target.value) })}
      className={field}
    />
  )

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-accent/40 bg-card p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="font-semibold">This week’s log</p>
        {!log && project.repo_full_name && (
          <button onClick={generate} className="flex items-center gap-1.5 rounded-lg bg-accent-soft px-3 py-1.5 text-sm font-medium text-accent">
            <Sparkles size={15} /> Draft from commits
          </button>
        )}
      </div>
      {status && <p className="text-sm text-muted">{status}</p>}
      <label className="text-xs text-muted">Week label<input aria-label="Week label" value={draft.week_label} onChange={event => setDraft({ ...draft, week_label: event.target.value })} className={field} /></label>
      <input aria-label="Log title" id="log-title" placeholder="Headline for the week" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} className={field} />
      {list('built', 'What you built, one per line')}
      {list('learned', 'What you learned, one per line')}
      {list('stuck', 'Where you’re stuck, one per line (mentors can help)')}
      <label className="text-xs text-muted">Skills (comma separated)<input value={draft.skills.join(',')} onChange={event => setDraft({ ...draft, skills: event.target.value.split(',') })} onBlur={() => setDraft({ ...draft, skills: draft.skills.map(skill => skill.trim()).filter(Boolean) })} className={field} /></label>
      <div className="flex justify-end gap-2">
        <button disabled={saving} onClick={onDone} className="rounded-lg px-4 py-2 text-sm text-muted hover:text-ink">Cancel</button>
        <button onClick={publish} disabled={saving || !draft.title.trim() || !draft.week_label.trim()} className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">
          {saving ? 'Saving...' : log ? 'Save changes' : 'Publish to timeline'}
        </button>
      </div>
    </div>
  )
}

export default function ProjectPage() {
  const id = Number(useParams().id)
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [editing, setEditing] = useState(false)
  const [completionAction, setCompletionAction] = useState<'archive' | 'reopen' | null>(null)
  const [completionError, setCompletionError] = useState('')
  const [completing, setCompleting] = useState(false)
  const [shareStatus, setShareStatus] = useState('')
  const [action, setAction] = useState<'delete' | 'leave' | null>(null)
  const [actionError, setActionError] = useState('')
  const [busy, setBusy] = useState(false)
  const { data: me } = useMe()
  const [params] = useSearchParams()
  const [writing, setWriting] = useState(params.get('write') === '1')
  const [editingLog, setEditingLog] = useState<number | null>(null)
  const [deletingLog, setDeletingLog] = useState<number | null>(null)
  const [logError, setLogError] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [comment, setComment] = useState('')
  const q = useQuery({ queryKey: ['project', id], queryFn: () => api<ProjectData>(`/projects/${id}`) })
  const refresh = () => qc.invalidateQueries({ queryKey: ['project', id] })

  if (!q.data) return <p className="text-muted">{q.isError ? 'Project not found.' : 'Loading…'}</p>
  const { project: p, members, timeline, help_requests, comments } = q.data
  const isMember = p.owner_id === me?.id || members.some((m) => m.user.id === me?.id)
  const isGroup = new Set([p.owner_id, ...members.map(m => m.user.id)]).size > 1
  const week = weekOf(p)

  async function changeCompletion() {
    if (!completionAction) return
    setCompleting(true); setCompletionError('')
    try {
      await post(`/projects/${p.id}/${completionAction}`)
      setCompletionAction(null); setWriting(false)
      await qc.invalidateQueries()
    } catch (error) { setCompletionError(error instanceof Error ? error.message : 'Unable to update this project.') }
    finally { setCompleting(false) }
  }

  async function shareProject() {
    const url = new URL(`/projects/${p.id}`, window.location.origin).href
    try { await navigator.clipboard.writeText(url); setShareStatus('Public project link copied.') }
    catch { setShareStatus(`Public link: ${url}`) }
  }

  async function confirmAction() {
    if (!action) return
    setBusy(true); setActionError('')
    try {
      if (action === 'leave') await post(`/projects/${p.id}/leave`)
      else await api(`/projects/${p.id}`, { method: 'DELETE' })
      await qc.invalidateQueries()
      navigate(action === 'delete' ? '/explore' : `/u/${me!.id}`)
    } catch (error) { setActionError(error instanceof Error ? error.message : 'Unable to complete this action.') }
    finally { setBusy(false) }
  }

  async function removeLog(logId: number) {
    setDeleting(true); setLogError('')
    try {
      await api(`/projects/${p.id}/logs/${logId}`, { method: 'DELETE' })
      setDeletingLog(null)
      await qc.invalidateQueries()
    } catch (error) { setLogError(error instanceof Error ? error.message : 'Could not delete this log.') }
    finally { setDeleting(false) }
  }

  async function sendComment() {
    if (!comment.trim()) return
    await post('/comments', { body: comment, project_id: p.id })
    setComment('')
    refresh()
  }

  return (
    <div className="flex flex-col gap-8">
      {isMember && <div className="flex flex-wrap gap-3"><button onClick={() => setEditing(true)} className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white">Edit project</button><button onClick={() => { setAction(isGroup ? 'leave' : 'delete'); setActionError('') }} className="rounded-lg border border-edge px-4 py-2 text-sm">{isGroup ? 'Leave project' : 'Delete project'}</button></div>}
      {p.owner_id === me?.id && <button onClick={() => { setCompletionAction(p.status === 'active' ? 'archive' : 'reopen'); setCompletionError('') }} className="w-fit rounded-lg border border-accent/50 bg-accent-soft px-4 py-2 text-sm font-semibold text-accent">{p.status === 'active' ? 'Mark complete & showcase' : 'Reopen project'}</button>}
      {completionAction && p.owner_id === me?.id && <section aria-label="Confirm project completion" className="rounded-xl border border-edge bg-card p-5"><h2 className="font-semibold">{completionAction === 'archive' ? 'Complete and showcase this project?' : 'Reopen this project?'}</h2><p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">{completionAction === 'archive' ? 'The project will be archived and listed in the public showcase. Your team, repository, and published weekly logs will remain visible at the same shareable link. New logs, invitations, and help requests pause until you reopen it.' : 'The project will return to active projects and leave the completed showcase. Your team and history will stay intact.'}</p>{completionError && <p role="alert" className="mt-3 text-sm text-warn">{completionError}</p>}<div className="mt-4 flex gap-3"><button disabled={completing} onClick={() => void changeCompletion()} className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">{completing ? 'Saving...' : completionAction === 'archive' ? 'Complete & publish to showcase' : 'Confirm reopen'}</button><button disabled={completing} onClick={() => setCompletionAction(null)} className="px-3 py-2 text-sm">Cancel</button></div></section>}
      {editing && isMember && <NewProject key={p.id} project={p} onDone={() => { setEditing(false); void refresh() }} />}
      {action && isMember && <section aria-label="Confirm project action" className="rounded-xl border border-edge bg-card p-5"><h2 className="font-semibold">{action === 'leave' ? 'Leave this project?' : 'Delete this project?'}</h2><p className="mt-2 text-sm text-muted">{action === 'leave' ? (p.owner_id === me?.id ? 'Your teammates will keep the project. Ownership will pass to a remaining participant.' : 'Your teammates will keep the project. You will lose editing access.') : 'This permanently removes the project and its logs, feedback, and related activity.'}</p>{actionError && <p role="alert" className="mt-3 text-sm text-warn">{actionError}</p>}<div className="mt-4 flex gap-3"><button disabled={busy} onClick={() => void confirmAction()} className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">{busy ? 'Working...' : action === 'leave' ? 'Confirm leave' : 'Confirm delete'}</button><button disabled={busy} onClick={() => setAction(null)} className="px-4 py-2 text-sm">Cancel</button></div></section>}
      <header className="rounded-2xl border border-edge bg-card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-3xl font-semibold tracking-tight">{p.title}</h1>
            <p className="mt-2 max-w-2xl text-ink/85">{p.description}</p>
          </div>
          <span className={`rounded-full px-3 py-1 font-mono text-xs ${p.status === 'active' ? 'bg-good-soft text-good' : 'bg-tile text-muted'}`}>
            {p.status === 'archived' ? 'Completed / Archived' : 'In progress'}
          </span>
        </div>

        {week && p.status === 'active' && (
          <div className="mt-5">
            <div className="flex justify-between font-mono text-xs text-muted">
              <span>week {week.now} of {week.total}</span>
              <span>{day(p.start_date)} → {day(p.end_date)}</span>
            </div>
            <div className="mt-1.5 flex gap-1">
              {Array.from({ length: week.total }, (_, i) => (
                <span key={i} className={`h-1.5 flex-1 rounded-full ${i < week.now ? 'bg-accent' : 'bg-tile'}`} />
              ))}
            </div>
          </div>
        )}

        <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm">
          <div className="flex -space-x-2">
            {members.map((m) => (
              <Link key={m.user.id} to={`/u/${m.user.id}`} title={`${m.user.name} (${m.role})`} className="rounded-full ring-2 ring-card">
                <Avatar user={m.user} size={32} />
              </Link>
            ))}
          </div>
          {p.repo_full_name && (
            <a href={`https://github.com/${p.repo_full_name}`} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 font-mono text-muted hover:text-accent">
              <Github size={15} /> {p.repo_full_name}
            </a>
          )}
          <span className="font-mono text-muted">{p.tags.join(' · ')}</span>
        </div>

        {p.status === 'active' && p.looking_for.length > 0 && (
          <p className="mt-4 flex flex-wrap items-center gap-2 text-sm">
            <span className="text-muted">Looking for</span>
            {p.looking_for.map((r) => (
              <span key={r} className="rounded-full border border-dashed border-accent/60 px-3 py-1 text-accent">{r}</span>
            ))}
          </p>
        )}
        {p.status === 'archived' && <div className="mt-5 rounded-xl border border-good/20 bg-good-soft p-4"><p className="text-sm font-semibold text-good">Completed project</p><p className="mt-1 text-sm text-muted">{p.end_date ? `Completed on ${new Date(p.end_date + 'T00:00').toLocaleDateString()}. ` : ''}Explore the team's work and the timeline below.</p><div className="mt-3 flex flex-wrap gap-4 text-sm"><Link to="/showcase" className="text-accent hover:underline">Browse the public showcase</Link><button onClick={() => void shareProject()} className="text-accent hover:underline">Copy public link</button></div>{shareStatus && <p role="status" className="mt-2 break-all text-xs text-muted">{shareStatus}</p>}</div>}
      </header>

      <div className="grid items-start gap-8 lg:grid-cols-[1fr_20rem]">
        <section className="min-w-0">
          <div className="flex items-center justify-between">
            <Label>timeline</Label>
            {isMember && p.status === 'active' && !writing && (
              <button onClick={() => setWriting(true)} className="mb-3 rounded-lg bg-accent px-3 py-1.5 text-sm font-semibold text-white">
                Write this week’s log
              </button>
            )}
          </div>
          {writing && isMember && p.status === 'active' && <LogEditor project={p} onDone={() => { setWriting(false); refresh() }} />}
          {timeline.length === 0 && (!writing || p.status === 'archived') && <p className="text-sm text-muted">No logs yet.</p>}
          <ol className="mt-2 border-l border-edge">
            {timeline.map((log) => (
              <li key={log.id} className="relative pb-6 pl-6">
                <span className="absolute top-5 -left-[5px] h-2.5 w-2.5 rounded-full bg-accent ring-4 ring-base" />
                <LogBody log={log} canAsk={isMember && log.author_id === me?.id} />
                {isMember && log.author_id === me?.id && <div className="mt-3 flex gap-3"><button onClick={() => { setEditingLog(log.id); setDeletingLog(null) }} className="text-sm text-accent">Edit log</button><button onClick={() => { setDeletingLog(log.id); setEditingLog(null); setLogError('') }} className="text-sm text-muted">Delete log</button></div>}
                {isMember && log.author_id === me?.id && editingLog === log.id && <LogEditor key={log.id} project={p} log={log} onDone={() => { setEditingLog(null); void qc.invalidateQueries() }} />}
                {isMember && log.author_id === me?.id && deletingLog === log.id && <div className="mt-3 rounded-xl border border-edge p-4"><p className="text-sm">Delete this weekly log? Its feed post and comments will also be removed.</p>{logError && <p role="alert" className="mt-2 text-sm text-warn">{logError}</p>}<div className="mt-3 flex gap-3"><button disabled={deleting} onClick={() => void removeLog(log.id)} className="text-sm text-accent">{deleting ? 'Deleting...' : 'Confirm delete'}</button><button disabled={deleting} onClick={() => setDeletingLog(null)} className="text-sm text-muted">Cancel</button></div></div>}
              </li>
            ))}
          </ol>
        </section>

        <aside className="flex flex-col gap-8">
          <section>
            <Label>help requests</Label>
            {help_requests.length === 0 && <p className="text-sm text-muted">None yet.</p>}
            <ul className="space-y-3">
              {help_requests.map((h) => (
                <li key={h.id} className="rounded-xl border border-edge bg-card p-4 text-sm">
                  <p className="flex justify-between font-mono text-xs text-muted">
                    <span>{h.minutes} min ask</span>
                    <span className={h.status === 'open' ? 'text-warn' : 'text-good'}>{h.status}</span>
                  </p>
                  <p className="mt-1.5">{h.question}</p>
                  {h.answer && <p className="mt-2 border-l-2 border-good pl-3 text-ink/80">{h.answer}</p>}
                </li>
              ))}
            </ul>
          </section>

          <section>
            <Label>feedback</Label>
            <ul className="space-y-2">
              {comments.map((c) => (
                <li key={c.id} className="rounded-xl bg-tile px-3 py-2 text-sm text-ink/85">{c.body}</li>
              ))}
            </ul>
            <input
              id="project-comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendComment()}
              placeholder="Leave feedback and press Enter"
              className="mt-2 w-full rounded-lg bg-tile px-3 py-2 text-sm placeholder:text-muted focus:ring-1 focus:ring-accent focus:outline-none"
            />
          </section>
        </aside>
      </div>
    </div>
  )
}
