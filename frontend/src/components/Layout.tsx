import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Compass, Home, Inbox, LogOut, MessageSquare, Plus } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import Avatar from './Avatar'
import { post } from '../lib/api'
import { useMe } from '../lib/auth'

const item = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 rounded-xl px-4 py-2.5 text-[15px] ${
    isActive ? 'bg-accent-soft font-semibold text-accent' : 'text-ink/90 hover:bg-tile'
  }`

const Section = ({ children }: { children: string }) => (
  <p className="mt-6 mb-2 px-4 text-xs font-semibold tracking-widest text-muted uppercase">{children}</p>
)

const Link = ({ to, icon: Icon, label }: { to: string; icon: LucideIcon; label: string }) => (
  <NavLink to={to} className={item}>
    <Icon size={20} strokeWidth={1.75} /> {label}
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
    <div className="flex min-h-screen">
      <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col border-r border-edge bg-panel p-4">
        <p className="px-4 py-2 text-lg font-semibold tracking-tight">Keystone</p>

        <Section>Navigation</Section>
        <nav className="flex flex-col gap-1">
          <Link to="/feed" icon={Home} label="Feed" />
          <Link to="/explore" icon={Compass} label="Explore" />
          <Link to="/messages" icon={MessageSquare} label="Messages" />
          {isMentor && <Link to="/mentor" icon={Inbox} label="Help inbox" />}
        </nav>

        {!isMentor && (
          <>
            <Section>Build</Section>
            <Link to="/projects/new" icon={Plus} label="Push a project" />
          </>
        )}

        {me && (
          <div className="mt-auto flex items-center gap-3 border-t border-edge px-2 pt-4">
            <NavLink to={`/u/${me.id}`} className="flex min-w-0 flex-1 items-center gap-3">
              <Avatar user={me} />
              <span className="min-w-0">
                <span className="block truncate font-semibold">{me.name}</span>
                <span className="block truncate text-xs text-muted capitalize">{me.company ?? me.role}</span>
              </span>
            </NavLink>
            <button onClick={signOut} title="Sign out" className="rounded-lg p-2 text-muted hover:bg-tile hover:text-ink">
              <LogOut size={18} />
            </button>
          </div>
        )}
      </aside>

      <main className="min-w-0 flex-1 px-10 py-8">
        <Outlet />
      </main>
    </div>
  )
}
