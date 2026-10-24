import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Compass, Home, Inbox, LogOut, MessageSquare, Plus, Search } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import Avatar from './Avatar'
import { post } from '../lib/api'
import { useMe } from '../lib/auth'

// LinkedIn-style tab: icon over a small label, underlined when active
const Tab = ({ to, icon: Icon, label }: { to: string; icon: LucideIcon; label: string }) => (
  <NavLink
    to={to}
    className={({ isActive }) =>
      `flex h-full w-20 flex-col items-center justify-center gap-0.5 border-b-2 text-xs ${
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
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4">
          <NavLink to="/feed" className="grid h-9 w-9 place-items-center rounded-lg bg-accent font-bold text-white">
            K
          </NavLink>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              navigate(`/explore?q=${encodeURIComponent(new FormData(e.currentTarget).get('q') as string)}`)
            }}
            className="flex h-9 w-64 items-center gap-2 rounded-lg bg-tile px-3 text-muted"
          >
            <Search size={16} />
            <input id="search" name="q" placeholder="Search" className="w-full bg-transparent text-sm text-ink placeholder:text-muted focus:outline-none" />
          </form>

          <nav className="ml-auto flex h-full items-stretch">
            <Tab to="/feed" icon={Home} label="Home" />
            <Tab to="/explore" icon={Compass} label="Explore" />
            <Tab to="/messages" icon={MessageSquare} label="Messages" />
            {isMentor ? <Tab to="/mentor" icon={Inbox} label="Help inbox" /> : <Tab to="/projects/new" icon={Plus} label="Project" />}
            {me && (
              <NavLink
                to={`/u/${me.id}`}
                className={({ isActive }) =>
                  `flex w-20 flex-col items-center justify-center gap-0.5 border-b-2 text-xs ${
                    isActive ? 'border-ink text-ink' : 'border-transparent text-muted hover:text-ink'
                  }`
                }
              >
                <Avatar user={me} size={24} /> Me
              </NavLink>
            )}
          </nav>
          <button onClick={signOut} title="Sign out" className="rounded-lg p-2 text-muted hover:bg-tile hover:text-ink">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
