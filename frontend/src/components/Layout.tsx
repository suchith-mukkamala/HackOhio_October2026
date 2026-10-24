import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Compass, Home, Inbox, LogOut, MessageSquare, Plus, Search, Shield } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import Avatar from './Avatar'
import { post } from '../lib/api'
import { useMe } from '../lib/auth'

// LinkedIn-style tab: icon over a small label, underlined when active
const Tab = ({ to, icon: Icon, label }: { to: string; icon: LucideIcon; label: string }) => (
  <NavLink
    to={to}
    className={({ isActive }) =>
      `flex h-full w-12 flex-col sm:w-16 lg:w-20 items-center justify-center gap-0.5 border-b-2 text-[10px] sm:text-xs ${
        isActive ? 'border-ink text-ink' : 'border-transparent text-muted hover:text-ink'
      }`
    }
  >
    <Icon size={22} strokeWidth={1.75} />
    {label}
  </NavLink>
)

export default function Layout() {
  const { data: me } = useMe()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const isMentor = me?.role === 'mentor' || me?.role === 'faculty'

  async function signOut() {
    await post('/auth/logout')
    qc.clear()
    navigate('/')
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-edge bg-panel">
        <div className="mx-auto flex h-14 w-full max-w-6xl min-w-0 items-center gap-2 px-3 sm:gap-3 sm:px-4">
          <NavLink to="/feed" className="hidden h-9 w-9 shrink-0 place-items-center sm:grid rounded-lg bg-accent font-bold text-white">
            K
          </NavLink>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              navigate(`/explore?q=${encodeURIComponent(new FormData(e.currentTarget).get('q') as string)}`)
            }}
            className="hidden h-9 min-w-0 items-center md:flex md:w-40 lg:w-64 gap-2 rounded-lg bg-tile px-3 text-muted"
          >
            <Search size={16} />
            <input id="search" name="q" aria-label="Search people and projects" placeholder="Search" className="min-w-0 w-full bg-transparent text-sm text-ink placeholder:text-muted focus:outline-none" />
          </form>

          <nav className="ml-auto flex h-full min-w-0 items-stretch">
            <Tab to="/feed" icon={Home} label="Home" />
            <Tab to="/explore" icon={Compass} label="Explore" />
            <Tab to="/messages" icon={MessageSquare} label="Messages" />
            {isMentor ? <Tab to="/mentor" icon={Inbox} label="Help inbox" /> : <Tab to="/projects/new" icon={Plus} label="Project" />}
            {me?.is_admin && <Tab to="/admin" icon={Shield} label="Admin" />}
            {me && (
              <NavLink
                to={`/u/${me.id}`}
                className={({ isActive }) =>
                  `flex w-12 flex-col sm:w-16 lg:w-20 items-center justify-center gap-0.5 border-b-2 text-xs ${
                    isActive ? 'border-ink text-ink' : 'border-transparent text-muted hover:text-ink'
                  }`
                }
              >
                <Avatar user={me} size={24} /> Me
              </NavLink>
            )}
          </nav>
          <button onClick={signOut} title="Sign out" className="shrink-0 rounded-lg p-2 text-muted hover:bg-tile hover:text-ink">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <main className="mx-auto w-full min-w-0 max-w-6xl px-3 py-4 sm:px-4 sm:py-6">
        <Outlet />
      </main>
    </div>
  )
}
