import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Briefcase, Github, GraduationCap, MessageSquare, Pencil, Upload, X } from 'lucide-react' // CHANGED: added X
import Avatar from '../components/Avatar'
import SkillGraphView from '../components/SkillGraphView'
import { ApiError, api, put } from '../lib/api'
import { headline, useMe } from '../lib/auth'
import type { FeedItem, MeUpdate, Project, SkillGraph, SkillVocabulary, User } from '../lib/types' // CHANGED: added MeUpdate, SkillVocabulary

interface ProfileData {
  user: User
  projects: Project[]
  endorsements: { id: number }[]
  experience: { id: number; kind: 'work' | 'education'; title: string; org: string; start: string; end: string; summary: string }[]
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

const BIO_MAX_LENGTH = 500 // keep in sync with BIO_MAX_LENGTH in backend/app/routers/users.py

const Label = ({ children }: { children: string }) => (
  <h2 className="mb-3 font-mono text-sm text-muted">{`// ${children}`}</h2>
)

export default function Profile() {
  const id = Number(useParams().id)
  const { data: me } = useMe()
  const profile = useQuery({ queryKey: ['user', id], queryFn: () => api<ProfileData>(`/users/${id}`) })
  const graph = useQuery({ queryKey: ['skills', id], queryFn: () => api<SkillGraph>(`/users/${id}/skills`) })
  const qc = useQueryClient()
  const recentPosts = useQuery({ queryKey: ['user-posts', id, 1], queryFn: () => api<FeedItem[]>(`/users/${id}/posts?limit=1`) })
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [editingBio, setEditingBio] = useState(false)
  const [bioDraft, setBioDraft] = useState('')
  const [bioSaving, setBioSaving] = useState(false)
  const [bioError, setBioError] = useState('')

  function startEditingBio(current?: string) {
    setBioDraft(current ?? '')
    setBioError('')
    setEditingBio(true)
  }

  async function saveBio() {
    setBioSaving(true)
    setBioError('')
    try {
      await put<User>('/me', { bio: bioDraft } satisfies MeUpdate)
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['user', id] }),
        qc.invalidateQueries({ queryKey: ['me'] }),
      ])
      setEditingBio(false)
    } catch (err) {
      setBioError(err instanceof ApiError ? err.message : 'Could not save your bio.')
    } finally {
      setBioSaving(false)
    }
  }

  // NEW: skills editing
  const isMe = me?.id === id
  const vocabulary = useQuery({
    queryKey: ['vocabulary'],
    queryFn: () => api<SkillVocabulary>('/skills/vocabulary'),
    enabled: isMe,
  })
  const [skillsSaving, setSkillsSaving] = useState(false)
  const [skillsError, setSkillsError] = useState('')

  // NEW: PUT /me replaces the whole expertise_tags list, so always send the full new list
  async function saveSkills(next: string[]) {
    setSkillsSaving(true)
    setSkillsError('')
    try {
      await put<User>('/me', { expertise_tags: next } satisfies MeUpdate)
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['user', id] }),
        qc.invalidateQueries({ queryKey: ['skills', id] }),
        qc.invalidateQueries({ queryKey: ['me'] }),
      ])
    } catch (err) {
      setSkillsError(err instanceof ApiError ? err.message : 'Could not save your skills.')
    } finally {
      setSkillsSaving(false)
    }
  }

  async function uploadResume(file: File) {
    setUploading(true)
    setUploadError('')
    const body = new FormData()
    body.append('file', file)
    const res = await fetch('/api/me/resume', { method: 'POST', body, credentials: 'include' })
    if (!res.ok) setUploadError((await res.json().catch(() => ({}))).detail ?? 'Upload failed.')
    await qc.invalidateQueries({ queryKey: ['user', id] })
    setUploading(false)
  }

  if (!profile.data) return <p className="text-muted">{profile.isError ? 'Profile not found.' : 'Loading…'}</p>
  const { user, projects, endorsements, experience } = profile.data
  const skills = (graph.data?.nodes ?? []).filter((n) => n.tier in KINDS)
  const evidence = skills.flatMap((n) => n.evidence.map((e) => ({ ...e, skill: n.skill })))
  const handle = user.github_username ?? user.name.toLowerCase().replace(/[^a-z]+/g, '-')

  // NEW: the skills you can still add, grouped by top-level category for the dropdown
  const parentOf = Object.fromEntries((vocabulary.data?.skills ?? []).map((v) => [v.skill, v.parent]))
  const categories = vocabulary.data?.categories ?? []
  const categoryOf = (skill: string) => {
    let at: string | null | undefined = skill
    while (at && !categories.includes(at)) at = parentOf[at]
    return at ?? 'Other'
  }
  const addable = (vocabulary.data?.skills ?? []).map((v) => v.skill).filter((sk) => !user.expertise_tags.includes(sk))
  const addableGroups = [...categories, 'Other']
    .map((cat) => ({ cat, skills: addable.filter((sk) => categoryOf(sk) === cat) }))
    .filter((g) => g.skills.length > 0)

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
        {editingBio ? (
          <div className="flex flex-col gap-2">
            <textarea
              id="bio"
              autoFocus
              rows={5}
              maxLength={BIO_MAX_LENGTH}
              value={bioDraft}
              onChange={(e) => setBioDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') setEditingBio(false)
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) saveBio()
              }}
              placeholder="Tell people what you're building and what you want to learn."
              className="w-full resize-y rounded-lg border border-edge bg-tile px-3 py-2 text-sm placeholder:text-muted focus:border-accent focus:outline-none"
            />
            <p className="text-right font-mono text-xs text-muted">
              {bioDraft.length}/{BIO_MAX_LENGTH}
            </p>
            {bioError && <p className="rounded-lg bg-warn/10 px-3 py-2 text-sm text-warn">{bioError}</p>}
            <div className="flex gap-2">
              <button
                onClick={saveBio}
                disabled={bioSaving}
                className="flex-1 rounded-lg bg-accent py-1.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
              >
                {bioSaving ? 'Saving…' : 'Save'}
              </button>
              <button
                onClick={() => setEditingBio(false)}
                disabled={bioSaving}
                className="flex-1 rounded-lg border border-edge bg-tile py-1.5 text-sm hover:border-accent disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <>
            {user.bio && <p className="whitespace-pre-wrap text-[15px] text-ink/85">{user.bio}</p>}
            {me?.id === user.id && (
              <button
                onClick={() => startEditingBio(user.bio)}
                className="flex w-fit items-center gap-1.5 rounded-lg border border-edge px-3 py-1.5 text-sm hover:border-accent"
              >
                <Pencil size={14} /> {user.bio ? 'Edit bio' : 'Add a bio'}
              </button>
            )}
          </>
        )}
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

        {/* NEW: add and remove the skills you list on your profile (your own profile only) */}
        {isMe && (
          <section>
            <Label>my skills</Label>
            {user.expertise_tags.length === 0 && (
              <p className="mb-3 text-sm text-muted">You haven't listed any skills yet. Add some below.</p>
            )}
            <ul className="mb-3 flex flex-wrap gap-2">
              {user.expertise_tags.map((sk) => (
                <li key={sk} className="flex items-center gap-1.5 rounded-full border border-edge bg-tile py-1 pr-1.5 pl-3 text-sm">
                  {sk}
                  <button
                    onClick={() => saveSkills(user.expertise_tags.filter((t) => t !== sk))}
                    disabled={skillsSaving}
                    aria-label={`Remove ${sk}`}
                    title={`Remove ${sk}`}
                    className="grid h-5 w-5 place-items-center rounded-full text-muted hover:bg-warn/20 hover:text-warn disabled:opacity-50"
                  >
                    <X size={13} />
                  </button>
                </li>
              ))}
            </ul>
            <select
              id="add-skill"
              value=""
              disabled={skillsSaving || addableGroups.length === 0}
              onChange={(e) => e.target.value && saveSkills([...user.expertise_tags, e.target.value])}
              className="rounded-lg border border-edge bg-tile px-3 py-2 text-sm focus:border-accent focus:outline-none disabled:opacity-50"
            >
              <option value="">
                {vocabulary.isLoading ? 'Loading skills…' : addableGroups.length === 0 ? 'You have every skill' : '+ Add a skill'}
              </option>
              {addableGroups.map((g) => (
                <optgroup key={g.cat} label={g.cat}>
                  {g.skills.map((sk) => (
                    <option key={sk} value={sk}>
                      {sk}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
            {skillsError && <p className="mt-3 rounded-lg bg-warn/10 px-3 py-2 text-sm text-warn">{skillsError}</p>}
            <p className="mt-3 font-mono text-xs text-muted">
              Removing a skill only removes the "claimed" entry. Skills backed by shipped code or endorsements stay on your graph.
            </p>
          </section>
        )}

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
          <Label>experience and education</Label>
          {me?.id === user.id && (
            <label className="mb-4 inline-flex cursor-pointer items-center gap-2 rounded-lg border border-edge px-4 py-2 text-sm hover:border-accent">
              <Upload size={16} /> {uploading ? 'Reading resume...' : 'Upload resume (PDF)'}
              <input type="file" accept="application/pdf,.pdf" disabled={uploading} className="sr-only" onChange={event => {
                const file = event.target.files?.[0]
                if (file) void uploadResume(file)
                event.target.value = ''
              }} />
            </label>
          )}
          {uploadError && <p role="alert" className="mb-3 text-sm text-warn">{uploadError}</p>}
          {!experience?.length && <p className="text-sm text-muted">No experience listed yet.</p>}
          <ul className="space-y-3">
            {(experience ?? []).map(entry => (
              <li key={entry.id} className="rounded-xl border border-edge p-4">
                <h3 className="font-medium">{entry.title}</h3>
                <p className="mt-1 text-sm text-muted">{entry.org}</p>
                <p className="mt-1 font-mono text-xs text-muted">{[entry.start, entry.end].filter(Boolean).join(' - ')}</p>
                {entry.summary && <p className="mt-2 text-sm text-ink/85">{entry.summary}</p>}
              </li>
            ))}
          </ul>
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
