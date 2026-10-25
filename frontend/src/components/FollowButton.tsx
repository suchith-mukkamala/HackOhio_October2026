import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { UserPlus } from 'lucide-react'
import { api, post } from '../lib/api'
import type { FollowRequest } from '../lib/types'

export default function FollowButton({ userId, viewerId }: { userId: number; viewerId: number }) {
  const qc = useQueryClient()
  const relationship = useQuery({ queryKey: ['relationship', viewerId, userId], queryFn: () => api<FollowRequest | null>(`/connections/users/${userId}`), refetchInterval: 5000 })
  const follow = useMutation({
    mutationFn: () => post<FollowRequest>(`/connections/users/${userId}`),
    onSuccess: async result => {
      qc.setQueryData(['relationship', viewerId, userId], result)
      await Promise.all(['connections', 'threads'].map(key => qc.invalidateQueries({ queryKey: [key] })))
    },
  })
  const request = relationship.data
  return <div className="space-y-2">
    <button disabled={relationship.isPending || relationship.isError || follow.isPending || Boolean(request)} onClick={() => follow.mutate()} className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"><UserPlus size={16} />{relationship.isPending ? 'Loading connection...' : follow.isPending ? 'Requesting...' : request?.status === 'accepted' ? 'Connected' : request?.status === 'denied' ? 'Follow denied' : request ? request.sender_id === viewerId ? 'Requested to follow' : 'Follow request received' : 'Request to follow'}</button>
    {request && <Link to={`/messages?thread=${request.thread_id}`} className="block text-center text-xs text-accent hover:underline">{request.status === 'pending' && request.recipient_id === viewerId ? 'Accept or deny in messages' : 'View request in messages'}</Link>}
    {(follow.isError || relationship.isError) && <p role="alert" className="text-xs text-warn">{follow.error?.message ?? 'Unable to load connection status.'}{relationship.isError && <button onClick={() => void relationship.refetch()} className="ml-2 text-accent">Retry</button>}</p>}
  </div>
}
