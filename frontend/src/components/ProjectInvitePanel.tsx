import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import Avatar from './Avatar'
import { api, post } from '../lib/api'
import { headline } from '../lib/auth'
import type { ProjectInvite, User } from '../lib/types'

export default function ProjectInvitePanel({ projectId, memberIds, viewerId, onClose }: { projectId: number; memberIds: number[]; viewerId: number; onClose: () => void }) {
  const [search, setSearch] = useState('')
  const qc = useQueryClient()
  const invitations = useQuery({ queryKey: ['project-invitations', projectId], queryFn: () => api<(ProjectInvite & { recipient: User })[]>(`/projects/${projectId}/invites`), refetchInterval: 5000 })
  const people = useQuery({ queryKey: ['invite-people'], queryFn: async () => {
    const [students, mentors] = await Promise.all([api<User[]>('/search?type=students'), api<User[]>('/search?type=mentors')])
    return [...students, ...mentors]
  } })
  const send = useMutation({ mutationFn: (userId: number) => post<ProjectInvite>(`/projects/${projectId}/invite?to_id=${userId}`), onSuccess: async () => { await qc.invalidateQueries({ queryKey: ['project-invitations', projectId] }) } })
  const visible = people.data?.filter(person => person.id !== viewerId && !memberIds.includes(person.id) && `${person.name} ${person.role} ${headline(person)} ${person.expertise_tags.join(' ')}`.toLowerCase().includes(search.toLowerCase())) ?? []
  const latest = new Map<number, ProjectInvite>()
  for (const invitation of invitations.data ?? []) if (!latest.has(invitation.to_id)) latest.set(invitation.to_id, invitation)
  return <section aria-label="Invite people to project" className="rounded-2xl border border-edge bg-card p-4 sm:p-5">
    <div className="mb-3 flex items-center justify-between gap-3"><h2 className="font-semibold">Invite people</h2><button onClick={onClose} className="text-sm text-muted hover:text-ink">Close</button></div>
    <p className="mb-4 text-sm text-muted">Invite students, faculty, or mentors. They can accept or decline in Messages or on this project page.</p>
    <input aria-label="Find people to invite" type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search names, roles, or skills" className="w-full rounded-lg border border-edge bg-tile px-3 py-2 text-sm" />
    {(people.isPending || invitations.isPending) && <p role="status" className="mt-3 text-sm text-muted">Loading people and invitations...</p>}
    {(people.isError || invitations.isError) && <p role="alert" className="mt-3 text-sm text-warn">Unable to load invitations. <button onClick={() => { void people.refetch(); void invitations.refetch() }} className="text-accent">Retry</button></p>}
    {send.isError && <p role="alert" className="mt-3 text-sm text-warn">{send.error.message}</p>}
    {send.isSuccess && <p role="status" className="mt-3 text-sm text-good">Invitation sent.</p>}
    {people.data && invitations.data && <ul className="mt-3 max-h-72 space-y-2 overflow-y-auto">{visible.map(person => {
      const status = latest.get(person.id)?.status
      return <li key={person.id} className="flex min-w-0 items-center gap-3 rounded-lg bg-tile/50 p-3"><Avatar user={person} size={32} /><div className="min-w-0 flex-1"><Link to={`/u/${person.id}`} className="block truncate text-sm font-medium hover:text-accent">{person.name}</Link><p className="truncate text-xs text-muted">{person.role} · {headline(person)}</p></div><button aria-label={`Invite ${person.name}`} disabled={send.isPending || status === 'pending'} onClick={() => send.mutate(person.id)} className="shrink-0 rounded-lg border border-edge px-3 py-2 text-xs font-semibold hover:border-accent disabled:opacity-50">{send.isPending && send.variables === person.id ? 'Sending...' : status === 'pending' ? 'Invited' : status === 'accepted' || status === 'declined' ? 'Invite again' : 'Invite'}</button></li>
    })}{!visible.length && <li className="py-4 text-sm text-muted">No matching people outside your project team.</li>}</ul>}
    {Boolean(invitations.data?.length) && <details className="mt-4 border-t border-edge pt-3"><summary className="cursor-pointer text-sm text-muted">Invitation history</summary><ul className="mt-3 space-y-2 text-sm">{invitations.data?.map(invitation => <li key={invitation.id} className="flex flex-wrap justify-between gap-2"><span>{invitation.recipient.name}</span><span className="capitalize text-muted">{invitation.status}</span></li>)}</ul></details>}
  </section>
}
