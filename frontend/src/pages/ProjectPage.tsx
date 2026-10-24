import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Github, Sparkles } from 'lucide-react'
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

function LogEditor({ project, onDone }: { project: Project; onDone: () => void }) {
  const blank: Draft = { week_label: `Week of ${day(new Date().toISOString().slice(0, 10))}`, title: '', built: [], learned: [], stuck: [], skills: [], source: 'manual' }
  const [draft, setDraft] = useState<Draft>(blank)
  const [status, setStatus] = useState('')

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
    await post(`/projects/${project.id}/logs`, draft)
    onDone()
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
        {project.repo_full_name && (
          <button onClick={generate} className="flex items-center gap-1.5 rounded-lg bg-accent-soft px-3 py-1.5 text-sm font-medium text-accent">
            <Sparkles size={15} /> Draft from commits
          </button>
        )}
      </div>
      {status && <p className="text-sm text-muted">{status}</p>}
      <input id="log-title" placeholder="Headline for the week" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} className={field} />
      {list('built', 'What you built, one per line')}
      {list('learned', 'What you learned, one per line')}
      {list('stuck', 'Where you’re stuck, one per line (mentors can help)')}
      <div className="flex justify-end gap-2">
        <button onClick={onDone} className="rounded-lg px-4 py-2 text-sm text-muted hover:text-ink">Cancel</button>
        <button onClick={publish} disabled={!draft.title.trim()} className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">
          Publish to timeline
        </button>
      </div>
    </div>
  )
}

export default function ProjectPage() {
  const id = Number(useParams().id)
  const qc = useQueryClient()
  const { data: me } = useMe()
  const [writing, setWriting] = useState(false)
  const [comment, setComment] = useState('')
  const q = useQuery({ queryKey: ['project', id], queryFn: () => api<ProjectData>(`/projects/${id}`) })
  const refresh = () => qc.invalidateQueries({ queryKey: ['project', id] })

  if (!q.data) return <p className="text-muted">{q.isError ? 'Project not found.' : 'Loading…'}</p>
  const { project: p, members, timeline, help_requests, comments } = q.data
  const isMember = members.some((m) => m.user.id === me?.id)
  const week = weekOf(p)

  async function sendComment() {
    if (!comment.trim()) return
    await post('/comments', { body: comment, project_id: p.id })
    setComment('')
    refresh()
  }

  return (
    <div className="flex flex-col gap-8">
      <header className="rounded-2xl border border-edge bg-card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-3xl font-semibold tracking-tight">{p.title}</h1>
            <p className="mt-2 max-w-2xl text-ink/85">{p.description}</p>
          </div>
          <span className={`rounded-full px-3 py-1 font-mono text-xs ${p.status === 'active' ? 'bg-good-soft text-good' : 'bg-tile text-muted'}`}>
            {p.status}
          </span>
        </div>

        {week && (
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

        {p.looking_for.length > 0 && (
          <p className="mt-4 flex flex-wrap items-center gap-2 text-sm">
            <span className="text-muted">Looking for</span>
            {p.looking_for.map((r) => (
              <span key={r} className="rounded-full border border-dashed border-accent/60 px-3 py-1 text-accent">{r}</span>
            ))}
          </p>
        )}
      </header>

      <div className="grid items-start gap-8 lg:grid-cols-[1fr_20rem]">
        <section className="min-w-0">
          <div className="flex items-center justify-between">
            <Label>timeline</Label>
            {isMember && !writing && (
              <button onClick={() => setWriting(true)} className="mb-3 rounded-lg bg-accent px-3 py-1.5 text-sm font-semibold text-white">
                Write this week’s log
              </button>
            )}
          </div>
          {writing && <LogEditor project={p} onDone={() => { setWriting(false); refresh() }} />}
          {timeline.length === 0 && !writing && <p className="text-sm text-muted">No logs yet.</p>}
          <ol className="mt-2 border-l border-edge">
            {timeline.map((log) => (
              <li key={log.id} className="relative pb-6 pl-6">
                <span className="absolute top-5 -left-[5px] h-2.5 w-2.5 rounded-full bg-accent ring-4 ring-base" />
                <LogBody log={log} canAsk={log.author_id === me?.id} />
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
