import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Award, Compass, Home, Inbox, LogOut, MessageSquare, Plus, Search, Shield, Trophy, UsersRound } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import Avatar from './Avatar'
import { api, post } from '../lib/api'
import { usePageNavigation } from '../lib/usePageNavigation'
import { useMe } from '../lib/auth'
import type { ConnectionsData, HelpRequest, ReceivedProjectInvite } from '../lib/types'

// Icon-only navigation, underlined when active.
const tabClass = ({ isActive }: { isActive: boolean }) =>
  `flex h-full w-12 shrink-0 flex-col items-center justify-center gap-0.5 border-b-2 text-[10px] sm:w-16 sm:text-xs lg:w-20 ${
    isActive ? 'border-ink text-ink' : 'border-transparent text-muted hover:text-ink'
  }`

// `badge` shows a small count on the icon (hidden when 0)
const Tab = ({ to, icon: Icon, label, badge = 0 }: { to: string; icon: LucideIcon; label: string; badge?: number }) => {
  const { onLinkClick } = usePageNavigation()
  return (
    <NavLink to={to} aria-label={badge > 0 ? `${label}, ${badge} open` : label} onClick={event => onLinkClick(event, to)} className={tabClass}>
      <span className="relative">
        <Icon size={22} strokeWidth={1.75} aria-hidden="true" />
        {badge > 0 && (
          <span aria-hidden="true" className="absolute -top-1.5 -right-2.5 grid h-4 min-w-4 place-items-center rounded-full bg-accent px-1 text-[10px] leading-none font-semibold text-white">
            {badge > 99 ? '99+' : badge}
          </span>
        )}
      </span>
    </NavLink>
  )
}

export default function Layout() {
  const { data: me } = useMe()
  const qc = useQueryClient()
  const { go: navigate, onLinkClick } = usePageNavigation()
  const location = useLocation()
  const isMentor = me?.role === 'mentor' || me?.role === 'faculty'
  // Same query as the Help inbox page, so the badge and the page share one request and update together
  const inbox = useQuery({ queryKey: ['inbox'], queryFn: () => api<HelpRequest[]>('/help/inbox'), enabled: isMentor, refetchInterval: 60_000 })
  const openRequests = inbox.data?.length ?? 0
  const projectInvites = useQuery({ queryKey: ['project-invites', me?.id], queryFn: () => api<ReceivedProjectInvite[]>('/project-invites'), enabled: Boolean(me), refetchInterval: 5000 })
  const pendingProjectInvites = projectInvites.data?.filter(invite => invite.status === 'pending').length ?? 0
  const connections = useQuery({ queryKey: ['connections', me?.id], queryFn: () => api<ConnectionsData>('/connections'), enabled: Boolean(me), refetchInterval: 5000 })
  const followRequests = connections.data?.requests.filter(request => request.recipient_id === me?.id && request.status === 'pending').length ?? 0

  async function signOut() {
    if (!window.confirm('Are you sure you want to log out?')) return
    await post('/auth/logout')
    qc.clear()
    navigate('/')
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-edge bg-panel">
        <div className="mx-auto flex h-14 w-full max-w-6xl min-w-0 items-center gap-2 px-3 sm:gap-3 sm:px-4">
          <NavLink
            to="/feed"
            onClick={event => onLinkClick(event, '/feed')}
            aria-label="Home"
            className="hidden h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-xl transition-opacity hover:opacity-85 sm:grid"
          >
            <img src="/keystone-icon.svg" alt="Keystone" width={40} height={40} className="block h-10 w-10" />
          </NavLink>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              navigate(`/explore?q=${encodeURIComponent(new FormData(e.currentTarget).get('q') as string)}`)
            }}
            className="hidden h-9 min-w-0 items-center gap-2 rounded-lg bg-tile px-3 text-muted md:flex md:w-40 lg:w-64"
          >
            <Search size={16} />
            <input id="search" name="q" aria-label="Search people and projects" placeholder="Search" className="w-full min-w-0 bg-transparent text-sm text-ink placeholder:text-muted focus:outline-none" />
          </form>

          <nav aria-label="Main navigation" className="ml-auto flex h-full min-w-0 items-stretch overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <Tab to="/feed" icon={Home} label="Home" />
            <Tab to="/explore" icon={Compass} label="Explore" />
            <Tab to="/showcase" icon={Award} label="Showcase" />
            <Tab to="/challenges" icon={Trophy} label="Challenges" />
            <Tab to="/messages" icon={MessageSquare} label="Messages" badge={pendingProjectInvites} />
            <Tab to="/connections" icon={UsersRound} label="Connections" badge={followRequests} />
            {isMentor ? <Tab to="/mentor" icon={Inbox} label="Help inbox" badge={openRequests} /> : <Tab to="/projects/new" icon={Plus} label="Project" />}
            {me?.is_admin && <Tab to="/admin" icon={Shield} label="Admin" />}
            {me && (
              <NavLink to={`/u/${me.id}`} aria-label="Your profile" onClick={event => onLinkClick(event, `/u/${me.id}`)} className={tabClass}>
                <Avatar user={me} size={24} />
              </NavLink>
            )}
          </nav>
          <button onClick={signOut} title="Sign out" aria-label="Sign out" className="shrink-0 rounded-lg p-2 text-muted hover:bg-tile hover:text-ink">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <main key={location.pathname} className="page-content mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
