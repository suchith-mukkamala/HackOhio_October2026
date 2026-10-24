import { NavLink, Outlet } from 'react-router-dom'
import { useMe } from '../lib/auth'

const link = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-md text-sm ${isActive ? 'bg-scarlet text-white' : 'hover:bg-black/5'}`

export default function Layout() {
  const { data: me } = useMe()
  const isMentor = me?.role === 'mentor' || me?.role === 'faculty'

  return (
    <div className="min-h-screen">
      <header className="border-b border-black/10 bg-white">
        <nav className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
          <span className="mr-4 font-bold text-scarlet">Keystone</span>
          <NavLink to="/feed" className={link}>Feed</NavLink>
          <NavLink to="/explore" className={link}>Explore</NavLink>
          {isMentor && <NavLink to="/mentor" className={link}>Help inbox</NavLink>}
          <NavLink to="/messages" className={link}>Messages</NavLink>
          <span className="ml-auto text-sm text-black/60">
            {me ? <NavLink to={`/u/${me.id}`}>{me.name}</NavLink> : <NavLink to="/">Sign in</NavLink>}
          </span>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
