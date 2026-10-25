import { useMutation, useQueryClient } from '@tanstack/react-query'
import { post } from '../lib/api'
import type { FollowRequest } from '../lib/types'

export default function FollowRequestNotice({ request, viewerId }: { request: FollowRequest; viewerId: number }) {
  const qc = useQueryClient()
  const incoming = request.recipient_id === viewerId
  const decide = useMutation({
    mutationFn: (status: 'accepted' | 'denied') => post<FollowRequest>(`/connections/requests/${request.id}/respond`, { status }),
    onSuccess: async () => {
      await Promise.all(['connections', 'relationship', 'threads', 'messages'].map(key => qc.invalidateQueries({ queryKey: [key] })))
    },
  })
  return <div className="rounded-xl border border-edge bg-tile px-4 py-3 text-sm">
    <p role="status">{request.status === 'accepted' ? 'Follow accepted. You are now connected.' : request.status === 'denied' ? incoming ? 'You denied this follow request.' : 'Your follow request was denied.' : incoming ? 'Requested to follow you.' : 'Requested to follow.'}</p>
    {incoming && request.status === 'pending' && <div className="mt-3 flex flex-wrap gap-2">
      <button disabled={decide.isPending} onClick={() => decide.mutate('accepted')} className="rounded-lg bg-accent px-3 py-2 text-xs font-semibold text-white disabled:opacity-40">{decide.isPending && decide.variables === 'accepted' ? 'Accepting...' : 'Accept follow'}</button>
      <button disabled={decide.isPending} onClick={() => decide.mutate('denied')} className="rounded-lg border border-edge px-3 py-2 text-xs font-medium hover:bg-card disabled:opacity-40">{decide.isPending && decide.variables === 'denied' ? 'Denying...' : 'Deny'}</button>
    </div>}
    {decide.isError && <p role="alert" className="mt-2 text-xs text-warn">{decide.error.message}</p>}
  </div>
}
