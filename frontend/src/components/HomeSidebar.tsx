import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowUpRight, Clock3, FolderGit2, LifeBuoy, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import type { HelpRequest, Project, User } from '../lib/types'

type SidebarData = {
  my_projects: { project: Project; latest_log_title: string | null; last_activity_at: string; needs_log: boolean }[]
  active_project_count: number
  opportunities: { project: Project; matched_skills: string[] }[]
  help_requests: { request: HelpRequest; matched_skills: string[] }[]
}
const card = 'min-w-0 rounded-2xl border border-edge bg-card p-4'
const link = 'inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent'
const date = (value: string) => new Date(/Z$|[+-]\d\d:\d\d$/.test(value) ? value : value + 'Z').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

export default function HomeSidebar({ me }: { me: User }) {
  const sidebar = useQuery({ queryKey: ['home-sidebar', me.id], queryFn: () => api<SidebarData>('/home/sidebar'), staleTime: 30000 })
  const mentor = me.role === 'mentor' || me.role === 'faculty'
  if (sidebar.isPending) return <aside aria-label="Your next steps" className="home-sidebar space-y-3"><div className={card}><p role="status" className="text-sm text-muted">Finding your next steps...</p></div></aside>
  if (sidebar.isError) return <aside aria-label="Your next steps" className={card}><p role="alert" className="text-sm text-muted">Unable to load your next steps.</p><button onClick={() => void sidebar.refetch()} className={`${link} mt-3`}>Try again</button></aside>
  const { my_projects, active_project_count, opportunities, help_requests } = sidebar.data
  return <aside aria-label="Your next steps" className="min-w-0 space-y-4 lg:sticky lg:top-20">
    <div className="flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-wider text-muted"><Sparkles size={14} aria-hidden="true" /> Your next steps</div>
    <section className={card} aria-labelledby="sidebar-projects"><div className="mb-4 flex items-center justify-between gap-2"><h2 id="sidebar-projects" className="flex items-center gap-2 text-sm font-semibold"><FolderGit2 size={16} className="text-accent" /> Your projects</h2><span className="rounded-full bg-tile px-2 py-0.5 text-xs text-muted">{active_project_count}</span></div>
      <ul className="divide-y divide-edge">{my_projects.map(({ project, latest_log_title, last_activity_at, needs_log }) => <li key={project.id} className="home-sidebar-item py-3 first:pt-0 last:pb-0">
        <Link to={`/projects/${project.id}`} className="block truncate text-sm font-medium hover:text-accent">{project.title}</Link>
        <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted">{latest_log_title ? `Latest log: ${latest_log_title}` : 'Ready for your first update'}</p>
        <p className="mt-1.5 flex items-center gap-1 text-[11px] text-muted"><Clock3 size={11} />{latest_log_title ? 'Updated' : 'Created'} {date(last_activity_at)}</p>
        <Link to={mentor ? '/mentor' : `/projects/${project.id}?write=1`} className={`${link} mt-2`}>{mentor ? 'Help your team' : needs_log ? 'Write weekly log' : 'Add an update'}<ArrowUpRight size={12} /></Link>
      </li>)}</ul>
      {!my_projects.length && <div><p className="text-sm leading-relaxed text-muted">{mentor ? 'Your active team projects will appear here.' : 'Your next build starts with a project.'}</p><Link to={mentor ? '/explore?category=projects' : '/projects/new'} className={`${link} mt-3`}>{mentor ? 'Explore projects' : 'Create a project'}<ArrowUpRight size={12} /></Link></div>}
      {my_projects.length > 0 && <Link to={`/u/${me.id}`} className={`${link} mt-4 border-t border-edge pt-3`}>View your projects<ArrowUpRight size={12} /></Link>}
    </section>
    {mentor && <section className={card} aria-labelledby="sidebar-help"><h2 id="sidebar-help" className="mb-4 flex items-center gap-2 text-sm font-semibold"><LifeBuoy size={16} className="text-warn" /> Help someone move forward</h2><ul className="divide-y divide-edge">{help_requests.map(({ request, matched_skills }) => <li key={request.id} className="py-3 first:pt-0"><Link to={`/mentor?request=${request.id}`} className="line-clamp-2 text-sm font-medium hover:text-accent">{request.question}</Link><p className="mt-1 text-xs text-muted">{request.minutes} minute ask{matched_skills.length > 0 ? ` / ${matched_skills.slice(0, 2).join(', ')}` : ''}</p></li>)}</ul>{!help_requests.length && <p className="text-sm leading-relaxed text-muted">No open requests right now. Check back as teams share where they are stuck.</p>}<Link to="/mentor" className={`${link} mt-3`}>Open help inbox<ArrowUpRight size={12} /></Link></section>}
    <section className={card} aria-labelledby="sidebar-opportunities"><h2 id="sidebar-opportunities" className="mb-1 flex items-center gap-2 text-sm font-semibold"><Sparkles size={16} className="text-accent" /> Open opportunities</h2><p className="mb-4 text-xs leading-relaxed text-muted">Teams looking for another builder.</p><ul className="divide-y divide-edge">{opportunities.map(({ project, matched_skills }) => <li key={project.id} className="py-3 first:pt-0"><Link to={`/projects/${project.id}`} className="block truncate text-sm font-medium hover:text-accent">{project.title}</Link><p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted">Looking for: {project.looking_for.join(', ')}</p>{matched_skills.length ? <p className="mt-2 text-xs text-accent">Matches your {matched_skills.slice(0, 2).join(' + ')} skills</p> : <p className="mt-2 text-[11px] text-muted">Recently opened</p>}</li>)}</ul>{!opportunities.length && <p className="text-sm leading-relaxed text-muted">No other teams have open roles yet. Explore projects or start your own.</p>}<Link to="/explore?category=projects" className={`${link} mt-4 border-t border-edge pt-3`}>Explore projects<ArrowUpRight size={12} /></Link></section>
  </aside>
}
