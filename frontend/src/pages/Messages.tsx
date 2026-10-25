import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, MessageSquare, Plus, Send } from 'lucide-react'
import Avatar from '../components/Avatar'
import ProjectInvitationInbox from '../components/ProjectInvitationInbox'
import FollowRequestNotice from '../components/FollowRequestNotice'
import { api, post } from '../lib/api'
import { headline, useMe } from '../lib/auth'
import type { FollowRequest, User } from '../lib/types'

type Message = { id: number; sender_id: number; body: string; created_at: string; follow_request?: FollowRequest | null }
type Thread = { id: number; with: User[]; last: Message | null }
const inputClass = 'w-full rounded-xl border border-edge bg-tile px-4 py-3 text-sm outline-none focus:border-accent'
const buttonClass = 'inline-flex items-center justify-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-40'
const errorText = (error: Error | null) => error?.message ?? 'Something went wrong. Please try again.'
const threadName = (thread: Thread) => thread.with.map(user => user.name).join(', ')
const time = (value: string) => new Date(/Z$|[+-]\d\d:\d\d$/.test(value) ? value : value + 'Z').toLocaleString()

function Inbox({ me }: { me: User }) {
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const selectedId = Number(params.get('thread')) || null
  const recipientId = Number(params.get('to')) || null
  const [creating, setCreating] = useState(Boolean(recipientId))
  const [recipients, setRecipients] = useState<number[]>(recipientId ? [recipientId] : [])
  const [peopleQuery, setPeopleQuery] = useState('')
  const [query, setQuery] = useState('')
  const [drafts, setDrafts] = useState<Record<number, string>>({})
  const bottom = useRef<HTMLDivElement>(null)
  const threads = useQuery({ queryKey: ['threads', me.id], queryFn: () => api<Thread[]>('/threads'), refetchInterval: 3000 })
  const people = useQuery({
    queryKey: ['message-people'], enabled: creating,
    queryFn: async () => {
      const [students, mentors] = await Promise.all([api<User[]>('/search?type=students'), api<User[]>('/search?type=mentors')])
      return [...students, ...mentors].filter(user => user.id !== me.id)
    },
  })
  const selected = threads.data?.find(thread => thread.id === selectedId)
  const messages = useQuery({ queryKey: ['messages', me.id, selectedId], queryFn: () => api<Message[]>(`/threads/${selectedId}/messages`), enabled: Boolean(selected), refetchInterval: 2000 })
  const lastId = messages.data?.[messages.data.length - 1]?.id
  useEffect(() => { bottom.current?.scrollIntoView({ block: 'nearest' }) }, [selectedId, lastId])
  function openThread(id: number) { setParams({ thread: String(id) }); setCreating(false); setQuery('') }
  const create = useMutation({
    mutationFn: () => post<{ id: number }>('/threads', { user_ids: recipients }),
    onSuccess: async result => {
      await qc.invalidateQueries({ queryKey: ['threads', me.id] })
      openThread(result.id); setRecipients([]); setPeopleQuery('')
    },
  })
  const send = useMutation({
    mutationFn: ({ id, body }: { id: number; body: string }) => post<Message>(`/threads/${id}/messages`, { body }),
    onSuccess: (message, sent) => {
      setDrafts(previous => previous[sent.id]?.trim() === sent.body ? { ...previous, [sent.id]: '' } : previous)
      qc.setQueryData<Message[]>(['messages', me.id, sent.id], previous => [...(previous ?? []).filter(item => item.id !== message.id), message].sort((a, b) => a.id - b.id))
      void qc.invalidateQueries({ queryKey: ['messages', me.id, sent.id] })
      void qc.invalidateQueries({ queryKey: ['threads', me.id] })
    },
  })
  const filtered = (threads.data ?? []).filter(thread => `${threadName(thread)} ${thread.last?.body ?? ''}`.toLowerCase().includes(query.trim().toLowerCase()))
  const visiblePeople = (people.data ?? []).filter(user => `${user.name} ${headline(user)}`.toLowerCase().includes(peopleQuery.trim().toLowerCase()))
  const draft = selectedId ? drafts[selectedId] ?? '' : ''

  return <div className="mx-auto max-w-6xl">
    <ProjectInvitationInbox userId={me.id} />
    <header className="mb-6 flex items-center justify-between gap-3"><div><h1 className="text-2xl font-semibold">Messages</h1><p className="mt-2 text-sm text-muted">Talk with teammates and mentors, individually or as a group.</p></div><button className={buttonClass} onClick={() => { setCreating(true); create.reset(); setRecipients([]) }}><Plus size={17} /> New conversation</button></header>
    {creating && <section aria-label="New conversation" className="mb-5 rounded-2xl border border-edge bg-card p-5">
      <h2 className="mb-2 font-semibold">New conversation</h2><p className="mb-4 text-sm text-muted">Select one person for a direct conversation, or several for a group.</p>
      <label className="block"><span className="sr-only">Find people</span><input autoFocus value={peopleQuery} onChange={event => setPeopleQuery(event.target.value)} placeholder="Find people by name" className={inputClass} /></label>
      <div className="my-3 flex flex-wrap gap-2">{(people.data ?? []).filter(user => recipients.includes(user.id)).map(user => <button key={user.id} onClick={() => setRecipients(previous => previous.filter(id => id !== user.id))} className="rounded-full bg-accent-soft px-3 py-1 text-sm text-accent" aria-label={`Remove ${user.name}`}>{user.name} &times;</button>)}</div>
      <div className="max-h-60 overflow-y-auto">{people.isPending ? <p role="status">Loading people...</p> : people.isError ? <p role="alert">Unable to load people. <button onClick={() => void people.refetch()} className="text-accent">Retry</button></p> : visiblePeople.length ? visiblePeople.map(user => <label key={user.id} className="flex cursor-pointer items-center gap-3 rounded-lg p-3 hover:bg-tile"><input type="checkbox" checked={recipients.includes(user.id)} onChange={event => setRecipients(previous => event.target.checked ? [...previous, user.id] : previous.filter(id => id !== user.id))} /><Avatar user={user} size={32} /><span><span className="block text-sm font-medium">{user.name}</span><span className="text-xs text-muted">{headline(user)}</span></span></label>) : <p className="py-4 text-sm text-muted">No people found.</p>}</div>
      {create.isError && <p role="alert" className="mt-3 text-sm text-red-500">{errorText(create.error)}</p>}
      <div className="mt-4 flex gap-3"><button disabled={!recipients.length || recipients.length > 99 || create.isPending || people.isError || people.isPending} onClick={() => create.mutate()} className={buttonClass}>{create.isPending ? 'Creating...' : recipients.length > 1 ? `Start group (${recipients.length + 1})` : 'Start conversation'}</button><button onClick={() => setCreating(false)} className="px-3 text-sm">Cancel</button></div>
    </section>}
    {threads.isError && <p role="alert" className="mb-4">Unable to refresh conversations. <button className="text-accent" onClick={() => void threads.refetch()}>Retry</button></p>}
    <div className="grid min-h-[600px] overflow-hidden rounded-2xl border border-edge bg-card md:h-[min(720px,calc(100dvh-210px))] md:grid-cols-[300px_minmax(0,1fr)]">
      <aside aria-label="Conversations" className={`min-h-0 flex-col border-edge md:border-r ${selectedId ? 'hidden md:flex' : 'flex'}`}>
        <div className="border-b border-edge p-4"><h2 className="mb-3 font-semibold">Inbox</h2><input aria-label="Search conversations" type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Search conversations" className={inputClass} /></div>
        <div className="min-h-0 flex-1 overflow-y-auto">{threads.isPending ? <p role="status" className="p-5">Loading conversations...</p> : filtered.map(thread => <button key={thread.id} onClick={() => { openThread(thread.id); send.reset() }} aria-pressed={selectedId === thread.id} className={`flex w-full gap-3 border-b border-edge p-4 text-left ${selectedId === thread.id ? 'bg-accent-soft' : 'hover:bg-tile'}`}><Avatar user={{ name: threadName(thread) || 'Conversation' }} /><span className="min-w-0"><span className="block truncate text-sm font-semibold">{threadName(thread)}</span><span className="block text-xs text-accent">{thread.with.length > 1 ? `Group - ${thread.with.length + 1} people` : 'Direct conversation'}</span><span className="mt-1 block truncate text-xs text-muted">{thread.last?.body ?? 'Send the first message'}</span></span></button>)}{!threads.isPending && !filtered.length && <p className="p-6 text-sm text-muted">{query ? 'No matching conversations.' : 'No conversations yet. Start one with the button above.'}</p>}</div>
      </aside>
      <section aria-label="Conversation" className={`min-h-0 flex-col ${selectedId ? 'flex' : 'hidden md:flex'}`}>
        {selected ? <>
          <header className="flex items-start gap-3 border-b border-edge p-4"><button aria-label="Back to conversations" onClick={() => setParams({})} className="p-1 md:hidden"><ArrowLeft size={20} /></button><div className="min-w-0"><h2 className="font-semibold">{threadName(selected)}</h2><div className="mt-1 flex flex-wrap gap-2 text-xs text-accent">{selected.with.map(user => <Link key={user.id} to={`/u/${user.id}`} className="hover:underline">{user.name}</Link>)}</div></div></header>
          <div aria-label="Messages" className="min-h-[250px] flex-1 space-y-4 overflow-y-auto p-5">
            {messages.isPending && <p role="status">Loading messages...</p>}{messages.isError && <p role="alert">Unable to refresh messages. <button onClick={() => void messages.refetch()} className="text-accent">Retry</button></p>}
            {messages.data?.map(message => <div key={message.id} className={`flex ${message.sender_id === me.id ? 'justify-end' : 'justify-start'}`}><div className="max-w-[85%]"><p className="mb-1 text-xs text-muted">{message.sender_id === me.id ? 'You' : selected.with.find(user => user.id === message.sender_id)?.name ?? 'Member'}</p>{message.follow_request ? <FollowRequestNotice request={message.follow_request} viewerId={me.id} /> : <p className={`whitespace-pre-wrap break-words rounded-2xl px-4 py-3 text-sm ${message.sender_id === me.id ? 'bg-accent text-white' : 'bg-tile'}`}>{message.body}</p>}<time className="mt-1 block text-[10px] text-muted">{time(message.created_at)}</time></div></div>)}
            {!messages.isPending && !messages.isError && !messages.data?.length && <p className="py-10 text-center text-sm text-muted">Say hello to start the conversation.</p>}<div ref={bottom} />
          </div>
          <form className="border-t border-edge p-4" onSubmit={event => { event.preventDefault(); if (draft.trim() && !send.isPending) send.mutate({ id: selected.id, body: draft.trim() }) }}>
            <label htmlFor="message-draft" className="sr-only">Message</label><textarea id="message-draft" rows={2} maxLength={10000} value={draft} onChange={event => setDrafts(previous => ({ ...previous, [selected.id]: event.target.value }))} placeholder="Write a message..." className={`${inputClass} resize-none`} />
            {send.isError && send.variables?.id === selected.id && <p role="alert" className="my-2 text-sm text-red-500">{errorText(send.error)} Your draft is saved here; try sending again.</p>}
            <div className="mt-2 flex justify-end"><button type="submit" disabled={!draft.trim() || send.isPending} className={buttonClass}><Send size={16} /> {send.isPending ? 'Sending...' : 'Send'}</button></div>
          </form>
        </> : <div className="m-auto p-8 text-center"><MessageSquare size={32} className="mx-auto mb-4 text-accent" /><p>{selectedId && !threads.isPending ? 'Conversation unavailable.' : 'Choose a conversation or start a new one.'}</p><button className="mt-4 text-accent" onClick={() => setParams({})}>View inbox</button></div>}
      </section>
    </div>
  </div>
}

export default function Messages() {
  const { data: me, isPending } = useMe()
  if (isPending) return <p role="status">Loading your inbox...</p>
  if (!me) return <div className="p-10 text-center"><h1 className="text-2xl font-semibold">Sign in to message people</h1><Link to="/" className="mt-4 inline-block text-accent">Go to sign in</Link></div>
  return <Inbox key={me.id} me={me} />
}
