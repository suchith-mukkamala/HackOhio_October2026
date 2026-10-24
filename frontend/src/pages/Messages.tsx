import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, FlaskConical, MessageSquare, Search, Send } from 'lucide-react'
import Avatar from '../components/Avatar'
import { useMe } from '../lib/auth'
import type { User } from '../lib/types'

type Thread = {
  id: string
  members: [string, string]
  context: string
  unreadFor: string
  messages: { from: string; text: string; time: string }[]
}

// UI fixtures only; no thread requests or message mutations until the database is ready.
const threads: Thread[] = [
  { id: 'design', members: ['Maya Chen', 'Priya Natarajan'], context: 'BuckeyeBus Live', unreadFor: 'Maya Chen', messages: [
    { from: 'Maya Chen', text: 'The live bus markers are finally on the map! Could you take a look at the arrival cards?', time: '10:24 AM' },
    { from: 'Priya Natarajan', text: 'Just tried them. The layout feels good, but I think we can make delayed arrivals easier to spot.', time: '10:26 AM' },
    { from: 'Maya Chen', text: 'Agreed. Maybe a small label instead of relying on color?', time: '10:28 AM' },
    { from: 'Priya Natarajan', text: 'Exactly! I have a new mockup ready. Want to walk through it after lunch?', time: '10:32 AM' },
  ] },
  { id: 'backend', members: ['Maya Chen', 'Sam Okafor'], context: 'Mentor feedback · FastAPI', unreadFor: 'Sam Okafor', messages: [
    { from: 'Maya Chen', text: 'Thanks for looking at our arrival estimates. Should we smooth the data in the backend?', time: '9:10 AM' },
    { from: 'Sam Okafor', text: 'Start by recording feed latency. That will help you distinguish a stale update from an actual delay.', time: '9:18 AM' },
    { from: 'Maya Chen', text: 'That makes sense. I added latency logging and will share what we find.', time: '9:22 AM' },
  ] },
  { id: 'rover', members: ['Jordan Reyes', 'Sam Okafor'], context: 'Mars Rover Arm', unreadFor: 'Jordan Reyes', messages: [
    { from: 'Jordan Reyes', text: 'Our rover dashboard is coming together. Do you have time to look at the control loop?', time: '8:40 AM' },
    { from: 'Sam Okafor', text: 'Happy to help. Bring a short recording and the timing measurements, and we can work through it together.', time: '8:55 AM' },
  ] },
  { id: 'data', members: ['Maya Chen', 'Elena Park'], context: 'BuckeyeBus Live · Data review', unreadFor: 'Elena Park', messages: [
    { from: 'Elena Park', text: 'How is the arrival history looking? A simple plot of error over time could be useful.', time: '8:15 AM' },
    { from: 'Maya Chen', text: 'We have our first batch of measurements. I’ll put together a plot for your feedback!', time: '8:30 AM' },
  ] },
  { id: 'check-in', members: ['Priya Natarajan', 'Dr. Marcus Lee'], context: 'Project check-in', unreadFor: 'Priya Natarajan', messages: [
    { from: 'Priya Natarajan', text: 'We are planning a usability session for the campus bus map this week.', time: '8:05 AM' },
    { from: 'Dr. Marcus Lee', text: 'Ask participants to find their next bus without prompting them. Note where they hesitate.', time: '8:12 AM' },
  ] },
]

const descriptions: Record<string, string> = {
  'Maya Chen': 'Student · Computer Science & Engineering',
  'Priya Natarajan': 'Student · Design',
  'Jordan Reyes': 'Student · Mechanical Engineering',
  'Sam Okafor': 'Mentor · Honda R&D',
  'Elena Park': 'Mentor · 99P Labs',
  'Dr. Marcus Lee': 'Faculty · Ohio State CSE',
}

function Inbox({ me }: { me: User }) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const mine = threads.filter(thread => thread.members.includes(me.name))
  const unreadCount = mine.filter(thread => thread.unreadFor === me.name).length
  const filtered = mine.filter(thread => (!unreadOnly || thread.unreadFor === me.name) && `${thread.members.find(name => name !== me.name)} ${thread.context}`.toLowerCase().includes(query.toLowerCase().trim()))
  const selected = filtered.find(thread => thread.id === selectedId) ?? filtered[0]
  const partner = selected?.members.find(name => name !== me.name)

  return <div className="mx-auto max-w-6xl">
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div><h1 className="text-2xl font-semibold">Messages</h1><p className="mt-2 text-sm text-muted">Keep building the conversation with teammates and mentors.</p></div>
      <span className="inline-flex items-center gap-2 rounded-full border border-edge bg-card px-3 py-1.5 text-xs text-muted"><FlaskConical size={14} /> Preview</span>
    </div>
    <p className="mb-4 rounded-xl border border-edge bg-panel px-4 py-3 text-sm text-muted">Previewing <span className="font-medium text-ink">{me.name}’s inbox</span>. These are sample messages. Sending will be available soon.</p>
    <div className="grid min-h-[600px] overflow-hidden rounded-2xl border border-edge bg-card shadow-sm xl:h-[min(720px,calc(100dvh-210px))] xl:grid-cols-[320px_minmax(0,1fr)]">
      <aside aria-label="Conversations" className={`min-h-0 flex-col border-edge xl:border-r ${selectedId && selected ? 'hidden xl:flex' : 'flex'}`}>
        <div className="border-b border-edge p-5">
          <div className="mb-4 flex items-center justify-between"><h2 className="font-semibold">Inbox</h2><span className="text-xs text-muted">{mine.length} conversations</span></div>
          <label className="relative block"><span className="sr-only">Search conversations</span><Search size={16} aria-hidden="true" className="pointer-events-none absolute top-3 left-3 text-muted" /><input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Search people or projects" className="w-full rounded-xl border border-edge bg-tile py-2.5 pr-3 pl-9 text-sm text-ink placeholder:text-muted outline-none focus:border-accent focus:ring-2 focus:ring-accent/20" /></label>
          <div className="mt-4 flex gap-2" aria-label="Filter conversations">{[false, true].map(unread => <button key={String(unread)} onClick={() => setUnreadOnly(unread)} aria-pressed={unreadOnly === unread} className={`rounded-full px-3 py-1.5 text-xs font-medium ${unreadOnly === unread ? 'bg-accent-soft text-accent' : 'bg-tile text-muted hover:bg-tile'}`}>{unread ? `Unread (${unreadCount})` : 'All messages'}</button>)}</div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">{filtered.map(thread => {
          const name = thread.members.find(person => person !== me.name)!
          const last = thread.messages[thread.messages.length - 1]
          return <button key={thread.id} onClick={() => setSelectedId(thread.id)} aria-pressed={selected?.id === thread.id} className={`flex w-full gap-3 border-b border-edge border-l-2 p-4 text-left transition-colors ${selected?.id === thread.id ? 'border-l-accent bg-accent-soft' : 'border-l-transparent hover:bg-tile'}`}>
            <Avatar user={{ name }} /><span className="min-w-0 flex-1"><span className="flex items-center justify-between gap-2"><span className="truncate text-sm font-semibold">{name}</span><span className="shrink-0 text-[10px] text-muted">{last.time}</span></span><span className="mt-0.5 block truncate text-xs text-accent">{thread.context}</span><span className="mt-1.5 flex items-center gap-2"><span className="truncate text-xs leading-5 text-muted">{last.from === me.name ? 'You: ' : ''}{last.text}</span>{thread.unreadFor === me.name && <span className="h-2 w-2 shrink-0 rounded-full bg-accent"><span className="sr-only">Unread sample message</span></span>}</span></span>
          </button>
        })}{!filtered.length && <div className="px-6 py-12 text-center"><p className="font-medium">{query ? 'No conversations found' : unreadOnly ? 'No unread messages' : 'Your inbox starts here'}</p><p className="mt-2 text-sm text-muted">{query ? 'Try another name or project.' : unreadOnly ? 'Switch to all messages to see your conversations.' : 'Conversations with your connections will appear here.'}</p></div>}</div>
        <div className="flex items-center gap-3 border-t border-edge px-5 py-4"><Avatar user={me} /><div><p className="text-sm font-medium">{me.name}</p><p className="text-xs capitalize text-muted">Your inbox · {me.role}</p></div></div>
      </aside>
      <section aria-label={partner ? `Conversation with ${partner}` : 'Conversation'} className={`min-h-0 flex-col ${selectedId && selected ? 'flex' : 'hidden xl:flex'}`}>
        {selected && partner ? <>
          <div className="flex items-center gap-3 border-b border-edge px-5 py-4"><button onClick={() => setSelectedId(null)} className="rounded-md px-2 py-2 text-sm hover:bg-tile xl:hidden" aria-label="Back to conversations"><ArrowLeft size={18} /></button><Avatar user={{ name: partner }} /><div className="min-w-0"><h2 className="truncate font-semibold">{partner}</h2><p className="mt-0.5 text-xs text-muted">{descriptions[partner]}</p></div></div>
          <div className="border-b border-edge bg-panel px-6 py-2.5 text-xs text-muted">Discussing <span className="font-medium text-ink">{selected.context}</span></div>
          <div className="min-h-[300px] flex-1 space-y-5 overflow-y-auto px-5 py-6 sm:px-8"><p className="text-center text-[11px] font-medium uppercase tracking-wider text-muted">Sample conversation</p>{selected.messages.map((message, index) => {
            const own = message.from === me.name
            return <div key={`${selected.id}-${index}`} className={`flex ${own ? 'justify-end' : 'justify-start'}`}><div className="max-w-[85%] sm:max-w-[78%]"><p className={`mb-1.5 text-xs font-medium text-muted ${own ? 'text-right' : ''}`}>{own ? 'You' : message.from}</p><p className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${own ? 'rounded-br-sm bg-accent text-white' : 'rounded-bl-sm border border-edge bg-tile text-ink'}`}>{message.text}</p><p className={`mt-1.5 text-[10px] text-muted ${own ? 'text-right' : ''}`}>{message.time}</p></div></div>
          })}</div>
          <div className="border-t border-edge p-4 sm:px-6"><label htmlFor="message-draft" className="sr-only">Draft a message to {partner}</label><textarea id="message-draft" rows={2} placeholder={`Draft a message to ${partner.split(' ')[0]}…`} value={drafts[selected.id] ?? ''} onChange={event => setDrafts(previous => ({ ...previous, [selected.id]: event.target.value }))} className="w-full resize-none rounded-xl border border-edge bg-tile px-4 py-3 text-sm text-ink placeholder:text-muted outline-none focus:border-accent focus:ring-2 focus:ring-accent/20" /><div className="mt-2 flex items-center justify-between gap-3"><p className="text-xs text-muted">Preview only. Drafts stay here until you leave.</p><button disabled className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"><Send size={15} /> Send · Soon</button></div></div>
        </> : <div className="m-auto p-8 text-center"><MessageSquare size={32} className="mx-auto mb-4 text-accent" aria-hidden="true" /><p className="text-lg font-semibold">Room for a conversation</p><p className="mt-2 max-w-xs text-sm text-muted">Choose a conversation from your inbox to see it here.</p></div>}
      </section>
    </div>
  </div>
}

export default function Messages() {
  const { data: me, isPending } = useMe()
  if (isPending) return <div role="status" className="rounded-xl border border-edge bg-card p-10 text-center text-muted">Loading your inbox…</div>
  if (!me) return <div className="rounded-xl border border-edge bg-card p-12 text-center"><h1 className="text-2xl font-bold">Your conversations, together</h1><p className="mt-3 text-muted">Sign in to see your Messages preview.</p><Link to="/" className="mt-6 inline-block rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-white">Go to sign in</Link></div>
  return <Inbox key={me.id} me={me} />
}
