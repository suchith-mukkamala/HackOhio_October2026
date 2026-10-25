import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CircleCheck, CircleHelp, ImagePlus, Lightbulb, Link2, Send, Trash2, X } from 'lucide-react'
import './Feed.css'
import HomeSidebar from '../components/HomeSidebar'
import { Ladder, OrgsCard } from '../components/Community'
import Avatar from '../components/Avatar'
import { ApiError, api, post } from '../lib/api'
import { headline, useMe } from '../lib/auth'
import type { FeedItem, LogEntry, MediaKind } from '../lib/types'

const ago = (iso: string) => {
  const mins = Math.round((Date.now() - new Date(iso.endsWith('Z') ? iso : iso + 'Z').getTime()) / 60000)
  if (mins < 60) return `${Math.max(mins, 1)}m`
  if (mins < 1440) return `${Math.round(mins / 60)}h`
  return `${Math.round(mins / 1440)}d`
}

const kindOf = (url: string): MediaKind =>
  /youtube\.com|youtu\.be/.test(url) ? 'youtube' : /\.(mp4|webm|mov)(\?|$)/i.test(url) ? 'video' : 'image'

const youtubeId = (url: string) => url.match(/(?:v=|youtu\.be\/|embed\/|shorts\/)([\w-]{11})/)?.[1]

function Media({ url, kind }: { url: string; kind: MediaKind }) {
  const box = 'max-h-[28rem] w-full rounded-xl border border-edge bg-tile object-cover'
  const id = kind === 'youtube' ? youtubeId(url) : undefined
  if (id) return <iframe src={`https://www.youtube-nocookie.com/embed/${id}`} title="Video" allowFullScreen className="aspect-video w-full rounded-xl border border-edge" />
  if (kind === 'video') return <video src={url} controls playsInline className={box} />
  return <img src={url} alt="" loading="lazy" className={box} />
}

function Composer({ onPosted }: { onPosted: () => void }) {
  const { data: me } = useMe()
  const [body, setBody] = useState('')
  const [media, setMedia] = useState<{ url: string; kind: MediaKind } | null>(null)
  const [linking, setLinking] = useState(false)
  const [error, setError] = useState('')
  if (!me) return null

  function attachFile(file: File) {
    // Stored with the post; Vercel caps requests at 4.5 MB, so keep files small
    if (file.size > 3_000_000) return setError('Pick a file under 3 MB, or paste a link instead.')
    const reader = new FileReader()
    reader.onload = () => setMedia({ url: reader.result as string, kind: file.type.startsWith('video') ? 'video' : 'image' })
    reader.readAsDataURL(file)
    setError('')
  }

  function attachLink(url: string) {
    if (!url.startsWith('https://')) return setError('Links must start with https://')
    setMedia({ url, kind: kindOf(url) })
    setError('')
  }

  async function submit() {
    if (!body.trim()) return
    try {
      await post('/posts', { body, media_url: media?.url, media_kind: media?.kind })
      setBody('')
      setMedia(null)
      setLinking(false)
      onPosted()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not post.')
    }
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
        {media && (
          <div className="relative mt-2">
            <Media url={media.url} kind={media.kind} />
            <button onClick={() => setMedia(null)} title="Remove" className="absolute top-2 right-2 rounded-full bg-base/80 p-1 text-ink hover:text-warn">
              <X size={14} />
            </button>
          </div>
        )}
        {linking && !media && (
          <input
            id="media-link"
            autoFocus
            placeholder="Paste an image, .mp4 or YouTube link, then press Enter"
            onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.value.trim() && attachLink(e.currentTarget.value.trim())}
            className="mt-2 w-full rounded-lg bg-tile px-3 py-2 text-sm placeholder:text-muted focus:ring-1 focus:ring-accent focus:outline-none"
          />
        )}
        {error && <p className="mt-2 text-sm text-warn">{error}</p>}
        <div className="mt-2 flex items-center gap-1">
          <label title="Add a photo or video" className="cursor-pointer rounded-lg p-2 text-muted hover:bg-tile hover:text-accent">
            <ImagePlus size={18} />
            <input id="media-file" type="file" accept="image/*,video/*" hidden onChange={(e) => { if (e.target.files?.[0]) attachFile(e.target.files[0]); e.target.value = '' }} />
          </label>
          <button onClick={() => setLinking(!linking)} title="Add an image or video link" className="rounded-lg p-2 text-muted hover:bg-tile hover:text-accent">
            <Link2 size={18} />
          </button>
          <button
            onClick={submit}
            disabled={!body.trim()}
            className="ml-auto rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
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
  const { data: me } = useMe()
  const canDelete = (authorId: number) => me?.id === authorId || !!me?.is_admin

  async function remove(path: string, what: string) {
    if (!window.confirm(`Delete this ${what}?`)) return
    await api(path, { method: 'DELETE' })
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
        {canDelete(p.author_id) && (
          <button onClick={() => remove(`/posts/${p.id}`, 'post')} title="Delete post" className="rounded-lg p-2 text-muted hover:bg-tile hover:text-warn">
            <Trash2 size={16} />
          </button>
        )}
      </header>

      {log ? <LogBody log={log} canAsk={log.author_id === meId} /> : <p className="mt-3 text-[15px] whitespace-pre-wrap break-words">{p.body}</p>}

      {p.media_url && p.media_kind && <div className="mt-3"><Media url={p.media_url} kind={p.media_kind} /></div>}

      {log && log.author_id === meId && <Link to={`/projects/${log.project_id}`} className="mt-3 inline-block text-sm text-accent hover:underline">Manage weekly log in project</Link>}

      <footer className="mt-4 border-t border-edge pt-3">
        {comments.map((c) => (
          <div key={c.id} className="mb-2 flex items-start gap-2 rounded-lg bg-tile px-3 py-2 text-sm text-ink/85">
            <p className="min-w-0 flex-1 break-words">
              {c.author_name && <span className="mr-1.5 font-semibold text-ink">{c.author_name}</span>}
              {c.body}
            </p>
            {canDelete(c.author_id) && (
              <button onClick={() => remove(`/comments/${c.id}`, 'comment')} title="Delete comment" className="shrink-0 text-muted hover:text-warn">
                <Trash2 size={14} />
              </button>
            )}
          </div>
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
