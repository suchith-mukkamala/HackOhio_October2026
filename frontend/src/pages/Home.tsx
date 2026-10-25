import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Feed from './Feed'
import { api } from '../lib/api'
import { useMe } from '../lib/auth'
import type { Project } from '../lib/types'

// Faculty: every active project at a glance, so they can follow and advise
function ProjectsOverview() {
  const projects = useQuery({ queryKey: ['projects'], queryFn: () => api<Project[]>('/projects') })
  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-mono text-sm text-muted">{'// active projects'}</h2>
      {projects.data?.length === 0 && <p className="text-sm text-muted">No active projects yet.</p>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {projects.data?.map((p) => (
          <Link key={p.id} to={`/projects/${p.id}`} className="flex flex-col rounded-2xl border border-edge bg-card p-4 hover:border-accent">
            <p className="font-semibold">{p.title}</p>
            <p className="mt-1 line-clamp-2 flex-1 text-sm text-muted">{p.description}</p>
            <p className="mt-3 font-mono text-xs text-muted">
              {[p.start_date, p.end_date].filter(Boolean).join(' → ') || 'no dates'} · {p.tags.slice(0, 3).join(' · ')}
            </p>
          </Link>
        ))}
      </div>
    </section>
  )
}

// Faculty keep their project overview; mentor requests live exclusively in the Mentor tab.
export default function Home() {
  const { data: me } = useMe()
  if (!me) return null
  if (me.role === 'student') return <Feed />
  return (
    <div className="flex flex-col gap-10">
      {me.role === 'faculty' && <ProjectsOverview />}
      <section className="flex flex-col gap-3">
        <h2 className="font-mono text-sm text-muted">{'// what students are building'}</h2>
        <Feed />
      </section>
    </div>
  )
}
