import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { api } from '../lib/api'
import type { SidebarData } from './HomeSidebar'
import type { User } from '../lib/types'

export default function ProjectFocus({ me }: { me: User }) {
  const focus = useQuery({ queryKey: ['home-sidebar', me.id], queryFn: () => api<SidebarData>('/home/sidebar'), staleTime: 30_000 })
  const supporting = me.role === 'mentor' || me.role === 'faculty'
  return <section aria-labelledby="project-focus-heading" className="min-w-0 rounded-2xl border border-accent/30 bg-card p-3 sm:p-4">
    <div className="flex items-center justify-between gap-3">
      <h1 id="project-focus-heading" className="min-w-0 text-base font-semibold text-white">{supporting ? 'Help a team finish' : 'Move your project forward'}</h1>
      <Link to={supporting ? '/mentor' : '/projects/new'} className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-white">{supporting ? 'Mentor inbox' : 'Start a project'}<ArrowRight size={13} /></Link>
    </div>
    {focus.isPending && <p role="status" className="mt-3 text-xs text-muted">Loading your active projects...</p>}
    {focus.isError && <p role="alert" className="mt-3 text-xs text-muted">Unable to load your projects. <button onClick={() => void focus.refetch()} className="text-accent">Try again</button></p>}
    {focus.data && (focus.data.active_project_count ? <>
      <ul className="mt-3 grid gap-2 sm:grid-cols-3">{focus.data.my_projects.map(({ project, needs_log }, index) => <li key={project.id} className={`${index ? 'hidden sm:flex' : 'flex'} min-w-0 flex-col rounded-lg border border-edge bg-base/40 px-3 py-2`}>
        <Link to={`/projects/${project.id}`} title={project.title} className="truncate text-sm font-semibold hover:text-accent">{project.title}</Link>
        <p className="mt-1 text-xs text-muted">{project.end_date ? `Target finish: ${new Date(project.end_date + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}` : 'Set a target finish date'}</p>
        <Link to={supporting ? `/projects/${project.id}` : `/projects/${project.id}?write=1`} className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline">{supporting ? 'Review progress' : needs_log ? 'Share progress' : 'Add an update'}<ArrowRight size={12} /></Link>
      </li>)}</ul>
      <Link to={`/u/${me.id}`} className="mt-2 inline-block text-xs text-accent hover:underline">View all {focus.data.active_project_count} active {focus.data.active_project_count === 1 ? 'project' : 'projects'}</Link>
    </> : <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs"><p className="text-muted">{supporting ? 'Find a team to support.' : 'Join a team or start a small project.'}</p><Link to="/explore?category=projects" className="font-medium text-accent hover:underline">{supporting ? 'Explore teams' : 'Find a project to join'}</Link><Link to="/showcase" className="text-muted hover:text-ink">See finished projects</Link></div>)}
  </section>
}
