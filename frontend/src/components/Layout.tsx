import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Compass, Home, Inbox, LogOut, MessageSquare, Plus, Search, Shield } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import Avatar from './Avatar'
import { post } from '../lib/api'
import { usePageNavigation } from '../lib/usePageNavigation'
import { useMe } from '../lib/auth'

// A round icon button. The tab you are on opens up into a pill with its name.
const Tab = ({ to, icon: Icon, label }: { to: string; icon: LucideIcon; label: string }) => {
  const { onLinkClick } = usePageNavigation()

  return (
    <NavLink
      to={to}
      onClick={event => onLinkClick(event, to)}
      title={label}
      aria-label={label}
      className={({ isActive }) =>
        `flex h-10 items-center gap-2 rounded-full px-3 text-sm transition-colors ${
          isActive ? 'bg-accent text-white' : 'text-muted hover:bg-tile hover:text-ink'
        }`
      }
    >
      {({ isActive }) => (
        <>
          <Icon size={20} strokeWidth={1.75} />
          {isActive && <span className="font-medium">{label}</span>}
        </>
      )}
    </NavLink>
  )
}

export default function Layout() {
  const { data: me } = useMe()
  const qc = useQueryClient()
  const { go: navigate, onLinkClick } = usePageNavigation()
  const location = useLocation()
  const isMentor = me?.role === 'mentor' || me?.role === 'faculty'

  async function signOut() {
    await post('/auth/logout')
    qc.clear()
    navigate('/')
  }

  return (
    <div className="min-h-screen">
      {/* A floating pill instead of a full-width bar */}
      <header className="sticky top-0 z-10 px-3 pt-3">
        <div className="mx-auto flex h-14 max-w-4xl items-center gap-2 rounded-full border border-edge bg-panel/80 px-2 shadow-lg shadow-black/20 backdrop-blur">
          <NavLink
            to="/feed"
            onClick={event => onLinkClick(event, '/feed')}
            title="Home"
            aria-label="Home"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-accent font-bold text-white"
          >
            K
          </NavLink>

          <form
            onSubmit={(e) => {
              e.preventDefault()
              navigate(`/explore?q=${encodeURIComponent(new FormData(e.currentTarget).get('q') as string)}`)
            }}
            className="hidden h-10 w-48 items-center gap-2 rounded-full bg-tile px-4 text-muted sm:flex lg:w-64"
          >
            <Search size={16} />
            <input
              id="search"
              name="q"
              aria-label="Search people and projects"
              placeholder="Search"
              className="w-full bg-transparent text-sm text-ink placeholder:text-muted focus:outline-none"
            />
          </form>

          <nav className="ml-auto flex items-center gap-1">
            <Tab to="/feed" icon={Home} label="Home" />
            <Tab to="/explore" icon={Compass} label="Explore" />
            <Tab to="/messages" icon={MessageSquare} label="Messages" />
            {isMentor ? <Tab to="/mentor" icon={Inbox} label="Help inbox" /> : <Tab to="/projects/new" icon={Plus} label="Project" />}
            {me?.is_admin && <Tab to="/admin" icon={Shield} label="Admin" />}
            {me && (
              <NavLink
                to={`/u/${me.id}`}
                onClick={event => onLinkClick(event, `/u/${me.id}`)}
                title="Your profile"
                aria-label="Your profile"
                className={({ isActive }) =>
                  `ml-1 grid h-10 w-10 place-items-center rounded-full ${isActive ? 'ring-2 ring-accent' : 'hover:ring-2 hover:ring-edge'}`
                }
              >
                <Avatar user={me} size={32} />
              </NavLink>
            )}
          </nav>

          <button
            onClick={signOut}
            title="Sign out"
            aria-label="Sign out"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-full text-muted hover:bg-tile hover:text-ink"
          >
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
