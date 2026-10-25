import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CircleCheck, CircleHelp, Lightbulb, Send, Trash2 } from 'lucide-react'
import './Feed.css'
import HomeSidebar from '../components/HomeSidebar'
import { Ladder, OrgsCard } from '../components/Community'
import Avatar from '../components/Avatar'
import { api, del, post } from '../lib/api'
import { headline, useMe } from '../lib/auth'
import type { FeedItem, LogEntry } from '../lib/types'

const ago = (iso: string) => {
  const mins = Math.round((Date.now() - new Date(iso.endsWith('Z') ? iso : iso + 'Z').getTime()) / 60000)
  if (mins < 60) return `${Math.max(mins, 1)}m`
  if (mins < 1440) return `${Math.round(mins / 60)}h`
  return `${Math.round(mins / 1440)}d`
}

function Composer({ onPosted }: { onPosted: () => void }) {
  const { data: me } = useMe()
  const [body, setBody] = useState('')
  if (!me) return null

  async function submit() {
    if (!body.trim()) return
    await post('/posts', { body })
    setBody('')
    onPosted()
  }

  return (
    <div className="flex gap-3 rounded-2xl border border-edge bg-card p-4">
      <Avatar user={me} />
      <div className="min-w-0 flex-1">
        <textarea
          id="composer"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Share what you built or what you're stuck on…"
          rows={2}
          className="w-full resize-none bg-transparent text-[15px] placeholder:text-muted focus:outline-none"
        />
        <div className="flex justify-end">
          <button
            onClick={submit}
            disabled={!body.trim()}
            className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            Post
          </button>
        </div>
      </div>
    </div>
  )
}

export function LogBody({ log, canAsk }: { log: LogEntry; canAsk: boolean }) {
  const [asked, setAsked] = useState<string[]>([])

  async function ask(question: string) {
    await post('/help', { project_id: log.project_id, question, tags: log.skills, minutes: 15 })
    setAsked((a) => [...a, question])
  }

  const rows = [
    { label: 'Built', items: log.built, icon: CircleCheck, color: 'text-good' },
    { label: 'Learned', items: log.learned, icon: Lightbulb, color: 'text-accent' },
    { label: 'Stuck on', items: log.stuck, icon: CircleHelp, color: 'text-warn' },
  ]

  return (
    <div className="mt-3 rounded-xl bg-tile p-4">
      <p className="text-xs font-semibold tracking-widest text-muted uppercase">Weekly log · {log.week_label}</p>
      <h3 className="mt-1 text-lg font-semibold">{log.title}</h3>
      {rows.map(({ label, items, icon: Icon, color }) =>
        items.length ? (
          <div key={label} className="mt-3">
            <p className={`flex items-center gap-1.5 text-sm font-semibold ${color}`}>
              <Icon size={16} /> {label}
            </p>
            <ul className="mt-1 space-y-1 pl-6 text-sm text-ink/85">
              {items.map((i) => (
                <li key={i} className="flex items-start justify-between gap-3">
                  <span className="list-item list-disc">{i}</span>
                  {label === 'Stuck on' && canAsk && (
                    <button
                      onClick={() => ask(i)}
                      disabled={asked.includes(i)}
                      className="shrink-0 rounded-lg border border-edge px-2.5 py-1 text-xs font-medium text-accent hover:bg-accent-soft disabled:text-good"
                    >
                      {asked.includes(i) ? 'Asked a mentor' : 'Ask a mentor'}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ) : null,
      )}
      {log.skills.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {log.skills.map((s) => (
            <span key={s} className="rounded-full bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent">
              {s}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export function PostCard({ item, meId, onChange }: { item: FeedItem; meId?: number; onChange: () => void }) {
  const [comment, setComment] = useState('')
  const { post: p, author, project, log, comments } = item

    const { data: viewer } = useMe()
    const isAdmin = !!viewer?.is_admin

    async function removePost() {
      if (!window.confirm('Delete this post and its comments?')) return
      await del(`/admin/posts/${p.id}`)
      onChange()
    }

    async function removeComment(id: number) {
      if (!window.confirm('Delete this comment?')) return
      await del(`/admin/comments/${id}`)
      onChange()
    }

  async function sendComment() {
    if (!comment.trim()) return
    await post('/comments', { body: comment, post_id: p.id })
    setComment('')
    onChange()
  }

  return (
    <article className="rounded-2xl border border-edge bg-card p-5">
      <header className="flex items-center gap-3">
        {author && <Avatar user={author} />}
        <div className="min-w-0 flex-1">
          <Link to={`/u/${author?.id}`} className="font-semibold hover:underline">
            {author?.name}
          </Link>
          <p className="truncate text-sm text-muted">
            {author?.company ?? author?.major} · {ago(p.created_at)}
          </p>
        </div>
        {project && (
          <Link
            to={`/projects/${project.id}`}
            className="truncate rounded-full border border-edge px-3 py-1 text-xs font-medium text-ink/85 hover:border-accent"
          >
            {project.title}
          </Link>
        )}
        {isAdmin && (
            <button onClick={removePost} title="Delete post (admin)" className="rounded-lg p-2 text-muted hover:bg-tile hover:text-warn">
              <Trash2 size={16} />
            </button>
          )}
      </header>

      {log ? <LogBody log={log} canAsk={log.author_id === meId} /> : <p className="mt-3 text-[15px] whitespace-pre-wrap break-words">{p.body}</p>}

      {log && log.author_id === meId && <Link to={`/projects/${log.project_id}`} className="mt-3 inline-block text-sm text-accent hover:underline">Manage weekly log in project</Link>}

      <footer className="mt-4 border-t border-edge pt-3">
        {comments.map((c) => (
          <p key={c.id} className="mb-2 rounded-lg bg-tile px-3 py-2 text-sm text-ink/85">{c.body}</p>
        ))}
        <div className="flex items-center gap-2">
          <input
            id={`comment-${p.id}`}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendComment()}
            placeholder="Give feedback…"
            className="min-w-0 flex-1 rounded-lg bg-tile px-3 py-2 text-sm placeholder:text-muted focus:ring-1 focus:ring-accent focus:outline-none"
          />
          <button onClick={sendComment} title="Send" className="rounded-lg p-2 text-muted hover:bg-tile hover:text-accent">
            <Send size={16} />
          </button>
        </div>
      </footer>
    </article>
  )
}

export default function Feed() {
  const qc = useQueryClient()
  const { data: me } = useMe()
  const feed = useQuery({ queryKey: ['feed'], queryFn: () => api<FeedItem[]>('/feed') })
  const refresh = () => qc.invalidateQueries({ queryKey: ['feed'] })

  return (
    <div className={me ? 'home-feed grid w-full min-w-0 items-start gap-4 md:grid-cols-[11rem_minmax(0,1fr)] lg:grid-cols-[11rem_minmax(0,1fr)_15rem] xl:gap-5' : 'mx-auto max-w-2xl'}>
      {me && (
        <div className="sticky top-20 hidden flex-col gap-4 md:flex">
          <Link to={`/u/${me.id}`} className="overflow-hidden rounded-2xl border border-edge bg-card text-center">
            <div className="h-14 bg-accent" />
            <span className="-mt-8 inline-block rounded-full ring-4 ring-card">
              <Avatar user={me} size={64} />
            </span>
            <p className="mt-2 break-words px-4 font-semibold">{me.name}</p>
            <p className="break-words px-4 pb-4 text-sm text-muted">{headline(me)}</p>
            <p className="border-t border-edge py-3 text-sm font-medium text-accent">View profile</p>
          </Link>
          <OrgsCard />
        </div>
      )}
      <div id="feed" className="flex min-w-0 flex-col gap-4">
        {me?.role === 'student' && <Ladder />}
        <Composer onPosted={refresh} />
        {feed.data?.length === 0 && <p className="text-muted">Nothing here yet. Post the first update.</p>}
        {feed.data?.map((item) => <PostCard key={item.post.id} item={item} meId={me?.id} onChange={refresh} />)}
      </div>
      {me && <div className="home-sidebar-shell min-w-0 md:col-start-2 lg:col-start-3 lg:row-start-1 lg:sticky lg:top-20"><HomeSidebar me={me} /></div>}
    </div>
  )
}
