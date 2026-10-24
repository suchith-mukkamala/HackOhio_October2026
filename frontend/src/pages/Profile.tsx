import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Briefcase, Github, GraduationCap, MessageSquare, Upload } from 'lucide-react'
import Avatar from '../components/Avatar'
import SkillGraphView from '../components/SkillGraphView'
import { api } from '../lib/api'
import { headline, useMe } from '../lib/auth'
import type { Project, SkillGraph, User } from '../lib/types'

interface ProfileData {
  user: User
  projects: Project[]
  endorsements: { id: number }[]
  experience: { id: number; kind: 'work' | 'education'; title: string; org: string; start: string; end: string; summary: string; skills: string[] }[]
}

// Evidence kinds, weakest to strongest (see backend/app/services/skills.py)
const KINDS: Record<string, { label: string; dot: string; color: string }> = {
  claimed: { label: 'claimed', dot: 'bg-muted', color: 'var(--color-muted)' },
  code: { label: 'shipped code', dot: 'bg-accent', color: 'var(--color-accent)' },
  peer: { label: 'peer-endorsed', dot: 'bg-good', color: 'var(--color-good)' },
  mentor: { label: 'mentor-verified', dot: 'bg-warn', color: 'var(--color-warn)' },
  help_given: { label: 'helped others', dot: 'bg-avatar', color: 'var(--color-avatar)' },
}

// Avatar ring split by where this person's evidence comes from
function evidenceRing(kinds: string[]) {
  if (!kinds.length) return 'var(--color-edge)'
  let at = 0
  const stops = Object.keys(KINDS).flatMap((k) => {
    const share = (kinds.filter((x) => x === k).length / kinds.length) * 100
    if (!share) return []
    const stop = `${KINDS[k].color} ${at}% ${(at += share)}%`
    return [stop]
  })
  return `conic-gradient(${stops.join(', ')})`
}

const Label = ({ children }: { children: string }) => (
  <h2 className="mb-3 font-mono text-sm text-muted">{`// ${children}`}</h2>
)

export default function Profile() {
  const id = Number(useParams().id)
  const { data: me } = useMe()
  const profile = useQuery({ queryKey: ['user', id], queryFn: () => api<ProfileData>(`/users/${id}`) })
  const graph = useQuery({ queryKey: ['skills', id], queryFn: () => api<SkillGraph>(`/users/${id}/skills`) })
  const qc = useQueryClient()
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [uploadNote, setUploadNote] = useState('')

  async function uploadResume(file: File) {
    setUploading(true)
    setUploadError('')
    setUploadNote('')
    const body = new FormData()
    body.append('file', file)
    const res = await fetch('/api/me/resume', { method: 'POST', body, credentials: 'include' })
    if (!res.ok) setUploadError((await res.json().catch(() => ({}))).detail ?? 'Upload failed.')
    else {
      const r: { entries: number; skills: string[]; filled: string[] } = await res.json()
      setUploadNote(`Added ${r.entries} entries and ${r.skills.length} skills to your graph${r.filled.length ? `, and filled in your ${r.filled.join(' and ')}` : ''}.`)
    }
    // The resume can change the graph and empty profile fields, not just the timeline
    await Promise.all([['user', id], ['skills', id], ['me']].map((queryKey) => qc.invalidateQueries({ queryKey })))
    setUploading(false)
  }

  if (!profile.data) return <p className="text-muted">{profile.isError ? 'Profile not found.' : 'Loading…'}</p>
  const { user, projects, endorsements, experience } = profile.data
  const skills = (graph.data?.nodes ?? []).filter((n) => n.tier in KINDS)
  const evidence = skills.flatMap((n) => n.evidence.map((e) => ({ ...e, skill: n.skill })))
  const handle = user.github_username ?? user.name.toLowerCase().replace(/[^a-z]+/g, '-')

  return (
    <div className="grid items-start gap-8 md:grid-cols-[17rem_1fr]">
      {/* Identity column */}
      <aside className="flex flex-col gap-4 md:sticky md:top-20">
        <span className="w-fit rounded-full p-1.5" style={{ background: evidenceRing(evidence.map((e) => e.kind)) }} title="Evidence ring">
          <span className="block rounded-full p-1 bg-base">
            <Avatar user={user} size={200} />
          </span>
        </span>
        <div>
          <h1 className="text-2xl font-semibold">{user.name}</h1>
          <p className="font-mono text-muted">@{handle}</p>
        </div>
        {user.bio && <p className="text-[15px] text-ink/85">{user.bio}</p>}
        {me && me.id !== user.id && (
          <Link to={`/messages?to=${user.id}`} className="flex items-center justify-center gap-2 rounded-lg border border-edge bg-tile py-2 text-sm font-medium hover:border-accent">
            <MessageSquare size={16} /> Message
          </Link>
        )}
        <p className="font-mono text-sm text-muted">
          <b className="text-ink">{skills.length}</b> skills · <b className="text-ink">{endorsements.length}</b> endorsements
        </p>
        <ul className="space-y-1.5 text-sm text-ink/85">
          <li className="flex items-center gap-2">
            {user.role === 'student' ? <GraduationCap size={16} /> : <Briefcase size={16} />} {headline(user)}
          </li>
          {user.github_username && (
            <li>
              <a href={`https://github.com/${user.github_username}`} target="_blank" rel="noreferrer" className="flex items-center gap-2 hover:text-accent">
                <Github size={16} /> github.com/{user.github_username}
              </a>
            </li>
          )}
        </ul>
      </aside>

      <div className="flex min-w-0 flex-col gap-8">
        {/* Centerpiece: the skill graph */}
        <section>
          <Label>skill graph</Label>
          <div
            id="skill-graph-slot"
            className="relative overflow-hidden rounded-2xl border border-edge bg-card bg-[radial-gradient(var(--color-edge)_1px,transparent_1px)] bg-[size:20px_20px] p-4 pb-12"
          >
            {graph.data ? (
              <SkillGraphView graph={graph.data} name={user.name} />
            ) : (
              <p className="py-24 text-center font-mono text-sm text-muted">Loading…</p>
            )}
            <ul className="absolute bottom-3 left-4 flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs text-muted">
              {Object.entries(KINDS).map(([k, v]) => (
                <li key={k} className="flex items-center gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${v.dot}`} /> {v.label}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section>
          <div className="flex items-start justify-between gap-3">
            <Label>experience</Label>
            {me?.id === user.id && (
              <label className="flex cursor-pointer items-center gap-1.5 rounded-lg border border-edge px-3 py-1.5 text-sm hover:border-accent">
                <Upload size={15} /> {uploading ? 'Reading resume…' : 'Upload resume'}
                <input id="resume" type="file" accept="application/pdf" hidden disabled={uploading} onChange={(e) => e.target.files?.[0] && uploadResume(e.target.files[0])} />
              </label>
            )}
          </div>
          {uploadError && <p className="mb-3 text-sm text-warn">{uploadError}</p>}
          {uploadNote && <p className="mb-3 text-sm text-good">{uploadNote}</p>}
          {experience.length === 0 && (
            <p className="text-sm text-muted">{me?.id === user.id ? 'Upload a PDF resume to fill this in.' : 'No experience added yet.'}</p>
          )}
          <ol className="border-l border-edge">
            {experience.map((x) => (
              <li key={x.id} className="relative py-2.5 pl-6">
                <span className="absolute top-3.5 -left-[13px] grid h-6 w-6 place-items-center rounded-full bg-tile text-muted ring-4 ring-base">
                  {x.kind === 'education' ? <GraduationCap size={13} /> : <Briefcase size={13} />}
                </span>
                <p className="font-semibold">
                  {x.title} <span className="font-normal text-muted">· {x.org}</span>
                </p>
                <p className="font-mono text-xs text-muted">{[x.start, x.end].filter(Boolean).join(' → ')}</p>
                {x.summary && <p className="mt-1 text-sm text-ink/80">{x.summary}</p>}
                {x.skills?.length > 0 && (
                  <p className="mt-1.5 flex flex-wrap gap-1.5">
                    {x.skills.map((s) => <span key={s} className="rounded-full bg-tile px-2 py-0.5 font-mono text-xs text-muted">{s}</span>)}
                  </p>
                )}
              </li>
            ))}
          </ol>
          {experience.length > 0 && <p className="mt-2 font-mono text-xs text-muted">from resume · self-reported</p>}
        </section>

        <section>
          <Label>pinned projects</Label>
          {projects.length === 0 && <p className="text-sm text-muted">No projects yet.</p>}
          <div className="grid gap-3 sm:grid-cols-2">
            {projects.map((p) => (
              <Link key={p.id} to={`/projects/${p.id}`} className="flex flex-col rounded-xl border border-edge p-4 hover:border-accent">
                <p className="font-mono font-medium text-accent">{p.title}</p>
                <p className="mt-1 line-clamp-2 flex-1 text-sm text-muted">{p.description}</p>
                <p className="mt-3 font-mono text-xs text-muted">{p.tags.join(' · ')}</p>
              </Link>
            ))}
          </div>
        </section>

        <section>
          <Label>evidence log</Label>
          {evidence.length === 0 && <p className="text-sm text-muted">No evidence yet.</p>}
          <ol className="border-l border-edge">
            {evidence.map((e, i) => (
              <li key={i} className="relative py-2 pl-6 text-sm">
                <span className={`absolute top-3.5 -left-[5px] h-2.5 w-2.5 rounded-full ring-4 ring-base ${KINDS[e.kind].dot}`} />
                <span className="font-mono text-xs text-muted">{KINDS[e.kind].label}</span>{' '}
                <span className="font-semibold">{e.skill}</span>
                <p className="text-ink/80">{e.label}</p>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </div>
  )
}