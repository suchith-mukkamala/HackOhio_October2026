import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Avatar from '../components/Avatar'
import ConnectionsGraph from '../components/ConnectionsGraph'
import FollowRequestNotice from '../components/FollowRequestNotice'
import { api } from '../lib/api'
import { headline, useMe } from '../lib/auth'
import type { ConnectionsData, User } from '../lib/types'

function ConnectionsView({ me }: { me: User }) {
  const [search, setSearch] = useState('')
  const data = useQuery({ queryKey: ['connections', me.id], queryFn: () => api<ConnectionsData>('/connections'), refetchInterval: 5000 })
  const people = data.data?.connections.filter(user => `${user.name} ${headline(user)}`.toLowerCase().includes(search.toLowerCase())) ?? []
  return <div className="mx-auto max-w-5xl min-w-0">
    <header className="mb-6"><h1 className="text-2xl font-semibold">Connections</h1><p className="mt-2 text-sm text-muted">Request to follow someone. When they accept, you are connected to each other.</p></header>
    {data.isPending && <p role="status">Loading connections...</p>}
    {data.isError && <p role="alert" className="mb-4">Unable to refresh connections. <button onClick={() => void data.refetch()} className="text-accent">Retry</button></p>}
    {data.data && <>
      <ConnectionsGraph users={data.data.connections} />
      <section className="mt-6" aria-labelledby="connections-list"><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><h2 id="connections-list" className="font-semibold">Your connections ({data.data.connections.length})</h2><input aria-label="Search connections" value={search} onChange={event => setSearch(event.target.value)} placeholder="Find a connection" type="search" className="w-full rounded-lg border border-edge bg-tile px-3 py-2 text-sm sm:w-64" /></div>
        {!data.data.connections.length ? <p className="rounded-xl border border-dashed border-edge p-5 text-sm text-muted">No connections yet. <Link to="/explore?category=students" className="text-accent hover:underline">Find people to follow</Link>. Accepted requests will appear here.</p> : !people.length ? <p className="text-sm text-muted">No matching connections.</p> : <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{people.map(user => <li key={user.id}><Link to={`/u/${user.id}`} className="flex min-w-0 items-center gap-3 rounded-xl border border-edge bg-card p-4 hover:border-accent"><Avatar user={user} size={36} /><span className="min-w-0"><span className="block truncate font-medium">{user.name}</span><span className="block truncate text-xs text-muted">{headline(user)}</span></span></Link></li>)}</ul>}
      </section>
      {data.data.requests.length > 0 && <section className="mt-8" aria-labelledby="follow-requests"><h2 id="follow-requests" className="mb-4 font-semibold">Follow requests</h2><ul className="grid gap-4 sm:grid-cols-2">{data.data.requests.map(request => <li key={request.id} className="min-w-0 rounded-xl border border-edge bg-card p-4"><div className="mb-3 flex items-center justify-between gap-2"><Link to={`/u/${request.user.id}`} className="truncate text-sm font-medium hover:text-accent">{request.user.name}</Link><Link to={`/messages?thread=${request.thread_id}`} className="shrink-0 text-xs text-accent hover:underline">View message</Link></div><FollowRequestNotice request={request} viewerId={me.id} /></li>)}</ul></section>}
    </>}
  </div>
}

export default function Connections() {
  const { data: me, isPending } = useMe()
  if (isPending) return <p role="status">Loading connections...</p>
  if (!me) return <p>Sign in to view your connections. <Link to="/" className="text-accent">Sign in</Link></p>
  return <ConnectionsView key={me.id} me={me} />
}
