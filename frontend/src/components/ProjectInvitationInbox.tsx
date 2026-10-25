import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, post } from '../lib/api'
import type { ProjectInvite, ReceivedProjectInvite } from '../lib/types'

export default function ProjectInvitationInbox({ userId, projectId }: { userId: number; projectId?: number }) {
  const qc = useQueryClient()
  const [notice, setNotice] = useState<{ text: string; projectId: number } | null>(null)
  const invitations = useQuery({ queryKey: ['project-invites', userId], queryFn: () => api<ReceivedProjectInvite[]>('/project-invites'), refetchInterval: 5000 })
  const respond = useMutation({ mutationFn: ({ invite, status }: { invite: ReceivedProjectInvite; status: 'accepted' | 'declined' }) => post<ProjectInvite>(`/project-invites/${invite.id}/respond`, { status }), onSuccess: async (_, { invite, status }) => {
    setNotice({ text: status === 'accepted' ? `You joined ${invite.project.title}.` : `Invitation to ${invite.project.title} declined.`, projectId: invite.project_id })
    await Promise.all(['project-invites', 'project-invitations', 'project', 'user', 'home-sidebar', 'projects', 'ladder'].map(key => qc.invalidateQueries({ queryKey: [key] })))
  } })
  const pending = invitations.data?.filter(invite => invite.status === 'pending' && (!projectId || invite.project_id === projectId)) ?? []
  if (!pending.length && !notice && !invitations.isError) return null
  return <section aria-label="Project invitations" className="mb-5 rounded-2xl border border-accent/30 bg-card p-4 sm:p-5">
    <h2 className="mb-3 font-semibold">Project invitations</h2>
    {notice && <p role="status" className="mb-3 text-sm text-good">{notice.text} <Link to={`/projects/${notice.projectId}`} className="text-accent hover:underline">View project</Link></p>}
    {invitations.isError && <p role="alert" className="text-sm text-warn">Unable to load project invitations. <button onClick={() => void invitations.refetch()} className="text-accent">Retry</button></p>}
    {respond.isError && <p role="alert" className="mb-3 text-sm text-warn">{respond.error.message}</p>}
    <ul className="space-y-3">{pending.map(invite => <li key={invite.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-edge p-3"><div className="min-w-0"><Link to={`/projects/${invite.project_id}`} className="break-words font-medium hover:text-accent">{invite.project.title}</Link><p className="mt-1 text-xs text-muted">Invited by {invite.sender.name}{invite.project.status === 'archived' ? ' · Project archived' : ''}</p></div><div className="flex gap-2"><button onClick={() => respond.mutate({ invite, status: 'accepted' })} disabled={respond.isPending || invite.project.status !== 'active'} className="rounded-lg bg-accent px-3 py-2 text-xs font-semibold text-white disabled:opacity-40">Accept invitation</button><button onClick={() => respond.mutate({ invite, status: 'declined' })} disabled={respond.isPending} className="rounded-lg border border-edge px-3 py-2 text-xs disabled:opacity-40">Decline</button></div></li>)}</ul>
  </section>
}
