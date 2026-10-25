import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Dice5, Timer, Trophy } from 'lucide-react'
import Avatar from '../components/Avatar'
import { ApiError, api, post } from '../lib/api'
import { useMe } from '../lib/auth'
import type { User } from '../lib/types'

type Challenge = {
  id: number; user_id: number; prompt: string; hours: number; started_at: string; ends_at: string
  writeup: string; link: string; submitted_at: string | null; score: number | null; feedback: string
  user: User | null; judge_name: string | null
}

const LENGTHS = [[24, '24 hours'], [48, '48 hours'], [168, '1 week'], [336, '2 weeks']] as const
const utc = (s: string) => new Date(/Z$|[+-]\d\d:\d\d$/.test(s) ? s : s + 'Z').getTime()
const Label = ({ children }: { children: string }) => <h2 className="mb-3 font-mono text-sm text-muted">{`// ${children}`}</h2>

function Countdown({ endsAt }: { endsAt: string }) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [])
  const s = Math.max(0, Math.floor((utc(endsAt) - now) / 1000))
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60)
  return <span className="font-mono tabular-nums">{d ? `${d}d ${h}h ${m}m` : `${h}h ${m}m ${s % 60}s`} left</span>
}

function JudgeForm({ c, onDone }: { c: Challenge; onDone: () => void }) {
  const [score, setScore] = useState(c.score ?? 7)
  const [feedback, setFeedback] = useState(c.feedback)
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-edge pt-3">
      <select id={`score-${c.id}`} value={score} onChange={(e) => setScore(Number(e.target.value))} className="rounded-lg bg-tile px-2 py-2 text-sm">
        {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => <option key={n} value={n}>{n}/10</option>)}
      </select>
      <input id={`feedback-${c.id}`} value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="Feedback for the builder"
        className="min-w-0 flex-1 rounded-lg bg-tile px-3 py-2 text-sm placeholder:text-muted focus:ring-1 focus:ring-accent focus:outline-none" />
      <button onClick={async () => { await post(`/challenges/${c.id}/judge`, { score, feedback }); onDone() }}
        className="rounded-lg bg-accent px-3 py-2 text-sm font-semibold text-white">{c.score ? 'Update score' : 'Judge'}</button>
    </div>
  )
}

export default function Challenges() {
  const qc = useQueryClient()
  const { data: me } = useMe()
  const [hours, setHours] = useState<number>(24)
  const [writeup, setWriteup] = useState('')
  const [link, setLink] = useState('')
  const [error, setError] = useState('')
  const data = useQuery({ queryKey: ['challenges'], queryFn: () => api<{ mine: Challenge[]; entries: Challenge[] }>('/challenges') })
  const refresh = () => Promise.all([['challenges'], ['ladder'], ['feed']].map((queryKey) => qc.invalidateQueries({ queryKey })))
  const active = data.data?.mine.find((c) => !c.submitted_at && utc(c.ends_at) > Date.now())
  const canJudge = me?.role === 'mentor' || me?.role === 'faculty'

  async function run(fn: () => Promise<unknown>) {
    setError('')
    try { await fn(); await refresh() } catch (e) { setError(e instanceof ApiError ? e.message : 'Something went wrong.') }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-8">
      <section className="rounded-2xl border border-edge bg-card p-6">
        {active ? (
          <>
            <p className="flex items-center justify-between gap-3 text-sm text-muted">
              <span className="flex items-center gap-2"><Timer size={16} className="text-warn" /> Your {active.hours}-hour challenge</span>
              <span className="text-warn"><Countdown endsAt={active.ends_at} /></span>
            </p>
            <p className="mt-3 text-2xl leading-snug font-semibold">{active.prompt}</p>
            <textarea id="writeup" rows={4} value={writeup} onChange={(e) => setWriteup(e.target.value)} placeholder="What did you build, and what did you learn?"
              className="mt-5 w-full rounded-lg bg-tile px-3 py-2 text-sm placeholder:text-muted focus:ring-1 focus:ring-accent focus:outline-none" />
            <input id="link" value={link} onChange={(e) => setLink(e.target.value)} placeholder="Link to a demo or repo (optional)"
              className="mt-2 w-full rounded-lg bg-tile px-3 py-2 font-mono text-sm placeholder:text-muted focus:ring-1 focus:ring-accent focus:outline-none" />
            <button disabled={!writeup.trim()} onClick={() => run(() => post(`/challenges/${active.id}/submit`, { writeup, link }))}
              className="mt-3 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">Submit and share to the feed</button>
          </>
        ) : (
          <>
            <h1 className="flex items-center gap-2 text-2xl font-semibold"><Trophy size={22} className="text-warn" /> Take on a challenge</h1>
            <p className="mt-2 text-muted">Get a random prompt, build something before the clock runs out, and a mentor will judge it.</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {LENGTHS.map(([h, label]) => (
                <button key={h} onClick={() => setHours(h)}
                  className={`rounded-full border px-4 py-1.5 text-sm ${hours === h ? 'border-accent bg-accent-soft text-accent' : 'border-edge text-muted hover:text-ink'}`}>{label}</button>
              ))}
            </div>
            <button onClick={() => run(() => post('/challenges', { hours }))} className="mt-4 flex items-center gap-2 rounded-lg bg-accent px-4 py-2 font-semibold text-white">
              <Dice5 size={18} /> Give me a prompt
            </button>
          </>
        )}
        {error && <p className="mt-3 text-sm text-warn">{error}</p>}
      </section>

      <section>
        <Label>entries</Label>
        {data.data?.entries.length === 0 && <p className="text-sm text-muted">No entries yet. Be the first.</p>}
        <ul className="flex flex-col gap-3">
          {data.data?.entries.map((c) => (
            <li key={c.id} className="rounded-2xl border border-edge bg-card p-5">
              <div className="flex items-center gap-3">
                {c.user && <Avatar user={c.user} size={32} />}
                <Link to={`/u/${c.user_id}`} className="font-semibold hover:underline">{c.user?.name}</Link>
                <span className="font-mono text-xs text-muted">{c.hours}h challenge</span>
                {c.score && <span className="ml-auto rounded-full bg-warn/15 px-2.5 py-0.5 font-mono text-sm text-warn">{c.score}/10</span>}
              </div>
              <p className="mt-3 font-medium">{c.prompt}</p>
              <p className="mt-2 text-sm whitespace-pre-wrap text-ink/85">{c.writeup}</p>
              {c.link && <a href={c.link} target="_blank" rel="noreferrer" className="mt-2 inline-block font-mono text-sm text-accent break-all hover:underline">{c.link}</a>}
              {c.feedback && <p className="mt-3 border-l-2 border-warn pl-3 text-sm text-ink/80">{c.judge_name}: {c.feedback}</p>}
              {canJudge && c.user_id !== me?.id && <JudgeForm c={c} onDone={refresh} />}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
