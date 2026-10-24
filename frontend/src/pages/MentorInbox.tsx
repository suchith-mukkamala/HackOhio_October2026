import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, api, post } from '../lib/api'
import type { HelpRequest } from '../lib/types'

// Open help requests, best skill match first. Industry pros and faculty can answer and endorse.
function RequestCard({ r, onAnswered }: { r: HelpRequest; onAnswered: () => void }) {
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
    <li className="rounded-2xl border border-edge bg-card p-5">
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

export default function MentorInbox() {
  const qc = useQueryClient()
  const inbox = useQuery({ queryKey: ['inbox'], queryFn: () => api<HelpRequest[]>('/help/inbox') })

  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-mono text-sm text-muted">{'// help requests for you'}</h2>
      {inbox.data?.length === 0 && <p className="text-sm text-muted">No open requests right now.</p>}
      <ul className="flex flex-col gap-3">
        {inbox.data?.map((r) => (
          <RequestCard key={r.id} r={r} onAnswered={() => qc.invalidateQueries({ queryKey: ['inbox'] })} />
        ))}
      </ul>
    </section>
  )
}
