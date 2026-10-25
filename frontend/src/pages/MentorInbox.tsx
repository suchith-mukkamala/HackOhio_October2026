import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, api, post } from '../lib/api'
import type { HelpRequest } from '../lib/types'

// Open help requests, best skill match first. Industry pros and faculty can answer and endorse.
function RequestCard({ r, onAnswered, highlighted = false }: { r: HelpRequest; onAnswered: () => void; highlighted?: boolean }) {
  const [answer, setAnswer] = useState('')
  const [skill, setSkill] = useState('')
  const [error, setError] = useState('')

  async function send() {
    try {
      await post(`/help/${r.id}/answer`, { answer, endorse_skill: skill || null, endorse_note: skill ? answer.slice(0, 140) : '' })
      onAnswered()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not send your answer.')
    }
  }

  return (
    <li id={`request-${r.id}`} className={`rounded-2xl border bg-card p-5 ${highlighted ? 'border-accent ring-1 ring-accent/30' : 'border-edge'}`}>
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-xs text-muted">
        <span className="rounded-full bg-accent-soft px-2 py-0.5 text-accent">{Math.min(100, Math.round((r.match_score ?? 0) * 100))}% match</span>
        <span>{r.minutes} min ask</span>
        <Link to={`/projects/${r.project_id}`} className="hover:text-accent">view project →</Link>
      </p>
      <p className="mt-3 text-[15px]">{r.question}</p>
      {r.tags.length > 0 && <p className="mt-2 font-mono text-xs text-muted">{r.tags.join(' · ')}</p>}
      <textarea
        id={`answer-${r.id}`}
        rows={2}
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder="Your answer: a few sentences is plenty"
        className="mt-3 w-full rounded-lg bg-tile px-3 py-2 text-sm placeholder:text-muted focus:ring-1 focus:ring-accent focus:outline-none"
      />
      {error && <p className="mt-1 text-sm text-warn">{error}</p>}
      <div className="mt-2 flex flex-wrap items-center justify-end gap-2">
        {r.tags.length > 0 && (
          <select id={`endorse-${r.id}`} value={skill} onChange={(e) => setSkill(e.target.value)} className="rounded-lg bg-tile px-2 py-2 text-sm">
            <option value="">No endorsement</option>
            {r.tags.map((t) => <option key={t} value={t}>Endorse {t}</option>)}
          </select>
        )}
        <button onClick={send} disabled={!answer.trim()} className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">
          Send answer
        </button>
      </div>
    </li>
  )
}

type Impact = { answered: number; students_helped: number; marked_helpful: number; skills_endorsed: number }

// How much you've helped so far. "Waiting" comes from the inbox below, the rest from /help/impact.
function ImpactStrip({ waiting }: { waiting?: number }) {
  const impact = useQuery({ queryKey: ['impact'], queryFn: () => api<Impact>('/help/impact') })
  const tiles = [
    { label: 'Waiting for you', value: waiting, highlight: (waiting ?? 0) > 0 },
    { label: 'Students helped', value: impact.data?.students_helped },
    { label: 'Marked helpful', value: impact.data?.marked_helpful },
    { label: 'Skills endorsed', value: impact.data?.skills_endorsed },
  ]
  return (
    <section aria-label="Your impact" className="flex flex-col gap-3">
      <h2 className="font-mono text-sm text-muted">{'// your impact'}</h2>
      <ul className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {tiles.map((t) => (
          <li key={t.label} className="rounded-2xl border border-edge bg-card p-4">
            <span className={`block text-2xl font-semibold ${t.highlight ? 'text-accent' : ''}`}>{t.value ?? '–'}</span>
            <span className="mt-1 block text-xs text-muted" title={t.label === 'Students helped' ? 'Each answered request counts, including repeat help for the same student.' : undefined}>{t.label}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

const TIMES = [5, 15, 30] as const

const chip = (on: boolean) =>
  `rounded-full border px-3 py-1 text-xs font-medium ${on ? 'border-accent bg-accent-soft text-accent' : 'border-edge text-muted hover:border-accent'}`

export default function MentorInbox() {
  const qc = useQueryClient()
  const [params] = useSearchParams()
  const requestedId = Number(params.get('request'))
  const inbox = useQuery({ queryKey: ['inbox'], queryFn: () => api<HelpRequest[]>('/help/inbox') })
  const [minutes, setMinutes] = useState<number | null>(null)
  const [skill, setSkill] = useState('')

  const all = inbox.data ?? []
  const skills = [...new Set(all.flatMap((r) => r.tags))].sort()
  const activeSkill = skills.includes(skill) ? skill : '' // a skill that is no longer in the inbox stops filtering
  const filtering = minutes !== null || activeSkill !== ''
  // A request you were sent here to answer is never filtered out
  const shown = all.filter(
    (r) => r.id === requestedId || ((minutes === null || r.minutes === minutes) && (!activeSkill || r.tags.includes(activeSkill))),
  )
  const requests = [...shown].sort((a, b) => Number(b.id === requestedId) - Number(a.id === requestedId))

  return (
    <div className="flex flex-col gap-8">
      <ImpactStrip waiting={inbox.data?.length} />
      <section className="flex flex-col gap-3">
        <h2 className="font-mono text-sm text-muted">{'// help requests for you'}</h2>
        {all.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <button aria-pressed={minutes === null} onClick={() => setMinutes(null)} className={chip(minutes === null)}>
              Any time
            </button>
            {TIMES.map((m) => (
              <button key={m} aria-pressed={minutes === m} onClick={() => setMinutes(m)} className={chip(minutes === m)}>
                {m} min
              </button>
            ))}
            {skills.length > 0 && (
              <select
                id="filter-skill"
                aria-label="Filter by skill"
                value={activeSkill}
                onChange={(e) => setSkill(e.target.value)}
                className="rounded-lg bg-tile px-2 py-1.5 text-xs"
              >
                <option value="">All skills</option>
                {skills.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            )}
            {filtering && (
              <button onClick={() => { setMinutes(null); setSkill('') }} className="text-xs text-accent hover:underline">
                Clear filters
              </button>
            )}
            <span className="ml-auto font-mono text-xs text-muted">
              {requests.length} of {all.length}
            </span>
          </div>
        )}
        {inbox.data?.length === 0 && <p className="text-sm text-muted">No open requests right now.</p>}
        {all.length > 0 && requests.length === 0 && <p className="text-sm text-muted">No requests match these filters.</p>}
        <ul className="flex flex-col gap-3">
          {requests.map((r) => (
            <RequestCard key={r.id} r={r} highlighted={r.id === requestedId} onAnswered={() => { void qc.invalidateQueries({ queryKey: ['inbox'] }); void qc.invalidateQueries({ queryKey: ['impact'] }); void qc.invalidateQueries({ queryKey: ['home-sidebar'] }) }} />
          ))}
        </ul>
      </section>
    </div>
  )
}
