import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Check } from 'lucide-react'
import { api, post } from '../lib/api'

type Rung = { name: string; done: boolean; link: string }
type Club = { id: number; name: string; kind: string; blurb: string; color: string; members: number; projects: number; joined: boolean }

// What to do to climb to each rung (the challenge's Ladder)
const NEXT: Record<string, string> = {
  'Show up': 'Join an org you already belong to, or ask a mentor a question',
  'Try something small': "Leave feedback on someone else's update",
  'Join a project': 'Find a team that is looking for someone like you',
  'Give back': 'Answer a question or endorse a teammate',
}

// A ladder laid on its side: two rails, five rungs, lit as you earn them
export function Ladder() {
  const rungs = useQuery({ queryKey: ['ladder'], queryFn: () => api<Rung[]>('/home/ladder') })
  if (!rungs.data) return null
  const next = rungs.data.find((r) => !r.done)
  return (
    <section className="rounded-2xl border border-edge bg-card p-4">
      <div className="flex items-baseline justify-between">
        <h2 className="font-mono text-sm text-muted">{'// your ladder'}</h2>
        <span className="font-mono text-xs text-muted">{rungs.data.filter((r) => r.done).length}/5 rungs</span>
      </div>
      <ol className="mt-3 grid grid-cols-5 border-y-2 border-edge">
        {rungs.data.map((r) => (
          <li
            key={r.name}
            className={`flex min-h-14 flex-col items-center justify-center gap-1 border-l-4 px-1 py-2 text-center text-[11px] leading-tight last:border-r-4 ${
              r.done ? 'border-accent bg-accent-soft text-accent' : r === next ? 'border-warn text-ink' : 'border-edge text-muted'
            }`}
          >
            {r.done ? <Check size={14} /> : r === next ? <span className="h-2 w-2 animate-pulse rounded-full bg-warn" /> : <span className="h-2" />}
            {r.name}
          </li>
        ))}
      </ol>
      {next ? (
        <p className="mt-3 text-sm">
          <span className="text-muted">Next rung: </span>
          {next.link.startsWith('/') ? <Link to={next.link} className="text-accent hover:underline">{NEXT[next.name]}</Link> : <a href={next.link} className="text-accent hover:underline">{NEXT[next.name]}</a>}
        </p>
      ) : (
        <p className="mt-3 text-sm text-good">Top of the ladder. Now pull someone else up.</p>
      )}
    </section>
  )
}

// Student orgs: the communities people already belong to are how they find each other here
export function OrgsCard() {
  const qc = useQueryClient()
  const [all, setAll] = useState(false)
  const clubs = useQuery({ queryKey: ['clubs'], queryFn: () => api<Club[]>('/clubs') })
  if (!clubs.data?.length) return null
  const sorted = [...clubs.data].sort((a, b) => Number(b.joined) - Number(a.joined))
  const shown = all ? sorted : sorted.filter((c) => c.joined).concat(sorted.filter((c) => !c.joined).slice(0, 3))

  async function toggle(id: number) {
    await post(`/clubs/${id}/join`)
    await Promise.all([['clubs'], ['ladder']].map((queryKey) => qc.invalidateQueries({ queryKey })))
  }

  return (
    <section id="orgs" className="rounded-2xl border border-edge bg-card p-3">
      <h2 className="mb-2 font-mono text-xs text-muted">{'// your orgs'}</h2>
      <ul className="flex flex-col gap-2.5">
        {shown.map((c) => (
          <li key={c.id} title={c.blurb} className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: c.color }} />
              <span className="truncate text-xs font-medium">{c.name}</span>
            </div>
            <div className="mt-0.5 flex items-center justify-between gap-1 pl-3.5">
              <span className="truncate font-mono text-[10px] text-muted">{c.members} in · {c.projects} proj</span>
              <button onClick={() => toggle(c.id)} className={`shrink-0 text-[11px] font-medium ${c.joined ? 'text-good' : 'text-accent hover:underline'}`}>
                {c.joined ? 'Joined' : 'Join'}
              </button>
            </div>
          </li>
        ))}
      </ul>
      {clubs.data.length > shown.length || all ? (
        <button onClick={() => setAll(!all)} className="mt-2.5 text-[11px] text-muted hover:text-ink">
          {all ? 'Show less' : `All ${clubs.data.length} orgs`}
        </button>
      ) : null}
    </section>
  )
}
