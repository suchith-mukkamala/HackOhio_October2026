import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { User } from '../lib/types'

export type AdminUser = User & { username?: string | null }
type Preview = { user: AdminUser; owned_projects: { id: number; title: string }[]; deleted: Record<string, number>; updated: Record<string, number> }
const labels: Record<string, string> = { user: 'Account', project: 'Owned projects', projectmember: 'Project memberships', post: 'Posts', logentry: 'Weekly logs', comment: 'Comments', helprequest: 'Help requests', endorsement: 'Endorsements', invite: 'Project invitations', challenge: 'Challenge entries', connectionrequest: 'Connections and follow requests', message: 'Messages', threadmember: 'Conversation memberships', thread: 'Conversations with no remaining participants', experience: 'Experience entries', profilesettingsrecord: 'Profile settings', clubmember: 'Organization memberships' }

export default function DeleteUserDialog({ user, onClose, onDeleted }: { user: AdminUser; onClose: () => void; onDeleted: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [confirmation, setConfirmation] = useState('')
  const preview = useQuery({ queryKey: ['admin-deletion-preview', user.id], queryFn: () => api<Preview>(`/admin/users/${user.id}/deletion-preview`), retry: false, staleTime: 0 })
  const remove = useMutation({ mutationFn: () => api(`/admin/users/${user.id}`, { method: 'DELETE', body: JSON.stringify({ confirmation }) }), onSuccess: onDeleted })
  const phrase = `DELETE ${user.id}`
  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => element?.close()
  }, [])
  return <dialog ref={dialog} aria-labelledby="delete-user-title" onCancel={event => { event.preventDefault(); if (!remove.isPending) onClose() }} className="m-auto max-h-[85dvh] w-[calc(100%-2rem)] max-w-xl overflow-y-auto rounded-2xl border border-edge bg-card p-5 text-ink shadow-2xl backdrop:bg-black/70 sm:p-6">
    <h2 id="delete-user-title" className="text-lg font-semibold">Delete {user.name}?</h2>
    <p className="mt-1 text-sm text-muted">{user.username ? `@${user.username} · ` : ''}User ID {user.id}</p>
    <p className="mt-4 text-sm leading-relaxed">This permanently removes this account, its owned projects and their contents, and its contributions and references elsewhere. Other users and projects they own are preserved.</p>
    {preview.isPending && <p role="status" className="mt-4 text-sm text-muted">Checking associated data...</p>}
    {preview.isError && <p role="alert" className="mt-4 text-sm text-warn">{preview.error.message} <button onClick={() => void preview.refetch()} className="underline">Retry preview</button></p>}
    {preview.data && <>
      <h3 className="mt-5 text-sm font-semibold">Records to remove</h3>
      <dl className="mt-2 grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 text-sm">{Object.entries(preview.data.deleted).filter(([, count]) => count > 0).map(([key, count]) => <div key={key} className="contents"><dt className="text-muted">{labels[key] ?? key}</dt><dd>{count}</dd></div>)}</dl>
      {preview.data.owned_projects.length > 0 && <div className="mt-4"><h3 className="text-sm font-semibold">Owned projects being deleted</h3><ul className="mt-2 list-inside list-disc space-y-1 break-words text-sm text-muted">{preview.data.owned_projects.map(project => <li key={project.id}>{project.title}</li>)}</ul></div>}
      {Object.values(preview.data.updated).some(Boolean) && <p className="mt-4 text-xs leading-relaxed text-muted">References in surviving content will be cleared, including affected profile pins, mentor answers, and challenge reviews.</p>}
    </>}
    <form className="mt-5" onSubmit={event => { event.preventDefault(); if (preview.data && !preview.isError && confirmation === phrase && !remove.isPending) remove.mutate() }}>
      <label className="block text-sm">Type <strong>{phrase}</strong> to confirm<input aria-label={`Type ${phrase} to confirm`} autoComplete="off" spellCheck={false} value={confirmation} onChange={event => setConfirmation(event.target.value)} disabled={remove.isPending} className="mt-2 block w-full rounded-lg border border-edge bg-tile px-3 py-2 font-mono text-sm outline-none focus:border-warn" /></label>
      {remove.isError && <p role="alert" className="mt-3 text-sm text-warn">{remove.error.message}</p>}
      <div className="mt-5 flex flex-wrap justify-end gap-3"><button type="button" autoFocus disabled={remove.isPending} onClick={onClose} className="rounded-lg border border-edge px-4 py-2 text-sm disabled:opacity-40">Cancel</button><button type="submit" disabled={!preview.data || preview.isError || confirmation !== phrase || remove.isPending} className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">{remove.isPending ? 'Deleting...' : 'Permanently delete user'}</button></div>
    </form>
  </dialog>
}
