import { useMemo, useState } from 'react'
import { Briefcase, FolderGit2, GraduationCap, Search, SlidersHorizontal, Users, X } from 'lucide-react'
import Avatar from '../components/Avatar'
import { indexEntries, projectEntry, userEntry } from '../lib/exploreData'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import type { Project, User } from '../lib/types'
import type { ExploreCategory, ExploreEntry } from '../lib/exploreData'

const categories = [
  { id: 'projects', label: 'Projects', icon: FolderGit2 },
  { id: 'students', label: 'Teammates', icon: Users },
  { id: 'mentors', label: 'Mentors', icon: GraduationCap },
] as const

const roleNames: Record<string, string> = { student: 'Student', mentor: 'Industry mentor', faculty: 'Faculty' }
const unique = (values: string[]) => [...new Set(values)].sort((a, b) => a.localeCompare(b))
const selectClass = 'w-full rounded-xl border border-edge bg-tile px-3 py-2.5 text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 disabled:opacity-50'

function ResultCard({ entry, fuzzy, onSkill }: { entry: ExploreEntry; fuzzy: boolean; onSkill: (skill: string) => void }) {
  const project = entry.category === 'projects'
  return <article className="flex flex-col rounded-2xl border border-edge bg-card p-5 transition-colors hover:border-accent/50">
    <div className="flex items-start gap-3">
      {project ? <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-accent-soft text-accent"><FolderGit2 size={24} /></span> : <Avatar user={entry} size={48} />}
      <div className="min-w-0 flex-1"><p className="mb-1 text-xs font-medium text-accent">{project ? 'Project' : roleNames[entry.roles[0]]}</p><h2 className="text-lg font-semibold leading-tight"><Link to={entry.href} className="hover:text-accent hover:underline">{entry.name}</Link></h2><p className="mt-1 text-sm text-muted">{entry.subtitle}</p></div>
    </div>
    <p className="mt-4 text-sm leading-relaxed text-ink/85">{entry.description}</p>
    <div className="mt-4 flex flex-wrap gap-1.5" aria-label={`${entry.name} skills`}>{entry.skills.map(skill => <button key={skill} onClick={() => onSkill(skill)} title={`Filter by ${skill}`} className="rounded-full bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent transition-colors hover:bg-accent/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">{skill}</button>)}</div>
    <div className="mt-auto pt-5">
      {project ? <div className="border-t border-edge pt-3"><p className="mt-2 text-xs text-ink/85"><span className="text-muted">Looking for: </span>{entry.lookingFor?.join(' · ')}</p></div> : <div className="flex items-center gap-2 border-t border-edge pt-3 text-xs text-muted">{entry.category === 'students' ? <GraduationCap size={15} /> : <Briefcase size={15} />} {entry.category === 'students' ? 'Building and learning with others' : 'Sharing experience with builders'}</div>}
      {fuzzy && <p className="mt-3 text-xs text-accent">Similar spelling match</p>}
    </div>
  </article>
}

export default function Explore() {
  const [params, setParams] = useSearchParams()
  const requestedCategory = params.get('category')
  const category: ExploreCategory = requestedCategory === 'students' || requestedCategory === 'mentors' ? requestedCategory : 'projects'
  const query = params.get('q') ?? ''
  function setQuery(value: string) {
    setParams(previous => {
      const next = new URLSearchParams(previous)
      if (value) next.set('q', value)
      else next.delete('q')
      return next
    }, { replace: true })
  }
  const directory = useQuery({
    queryKey: ['explore-directory'],
    queryFn: async () => {
      const [students, mentors, projects] = await Promise.all([
        api<User[]>('/search?type=students'), api<User[]>('/search?type=mentors'), api<Project[]>('/search?type=projects'),
      ])
      return [...students.map(userEntry), ...mentors.map(userEntry), ...projects.map(projectEntry)]
    },
  })
  const exploreEntries = useMemo(() => directory.data ?? [], [directory.data])
  const exploreById = useMemo(() => new Map(exploreEntries.map(entry => [entry.id, entry])), [exploreEntries])
  const exploreIndex = useMemo(() => indexEntries(exploreEntries), [exploreEntries])
  const [role, setRole] = useState('')
  const [skill, setSkill] = useState('')
  const [major, setMajor] = useState('')
  const categoryEntries = exploreEntries.filter(entry => entry.category === category)
  const roles = unique(categoryEntries.flatMap(entry => entry.roles))
  const skills = unique(categoryEntries.flatMap(entry => entry.skills))
  const majors = unique(categoryEntries.flatMap(entry => entry.majors))
  const hits = useMemo(() => exploreIndex.search(query), [exploreIndex, query])
  const results = hits.flatMap(hit => {
    const entry = exploreById.get(hit.id)!
    return entry.category === category && (!role || entry.roles.some(value => value === role)) && (!skill || entry.skills.includes(skill)) && (!major || entry.majors.includes(major)) ? [{ entry, fuzzy: hit.fuzzy }] : []
  })
  const hasFilters = Boolean(role || skill || major || query)

  function clearFilters() { setRole(''); setSkill(''); setMajor('') }
  function switchCategory(next: ExploreCategory) {
    setParams(previous => { const updated = new URLSearchParams(previous); updated.set('category', next); return updated })
    clearFilters()
  }
  function reset() { clearFilters(); setQuery('') }

  return <div className="mx-auto max-w-6xl">
    <header className="mb-6 flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-2xl font-semibold">Explore</h1><p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">Join a project you can help finish. Find teammates and mentors to get it over the line.</p></div><span className="inline-flex items-center gap-2 rounded-full border border-edge bg-card px-3 py-1.5 text-xs text-muted">Live directory</span></header>
    <div className="mb-6 grid gap-3 sm:grid-cols-3" role="group" aria-label="Search category">{categories.map(({ id, label, icon: Icon }) => <button key={id} onClick={() => switchCategory(id)} aria-pressed={category === id} className={`flex items-center gap-3 rounded-2xl border p-4 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${category === id ? 'border-accent/60 bg-accent-soft' : 'border-edge bg-card hover:bg-tile'}`}><span className={`grid h-10 w-10 place-items-center rounded-xl ${category === id ? 'bg-accent/15 text-accent' : 'bg-tile text-muted'}`}><Icon size={21} /></span><span className="flex-1 font-semibold">{label}</span><span className={`text-sm ${category === id ? 'text-accent' : 'text-muted'}`}>{exploreEntries.filter(entry => entry.category === id).length}</span></button>)}</div>
    {category === 'projects' && <div className="mb-5 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-edge bg-card px-4 py-3"><p className="text-sm text-muted">See what teams have finished building.</p><Link to="/showcase" className="text-sm font-medium text-accent hover:underline">View completed project showcase</Link></div>}
    <section aria-label="Search and filters" className="rounded-2xl border border-edge bg-card p-5">
      <label htmlFor="explore-search" className="mb-2 block text-sm font-medium">Search {category}</label>
      <div className="relative"><Search size={19} aria-hidden="true" className="pointer-events-none absolute top-3.5 left-4 text-muted" /><input id="explore-search" type="search" maxLength={160} value={query} onChange={event => setQuery(event.target.value)} placeholder={category === 'projects' ? 'Search projects, skills, or open roles...' : 'Search names, skills, or interests...'} aria-describedby="explore-search-help" className="w-full rounded-xl border border-edge bg-tile py-3 pr-4 pl-11 text-sm text-ink placeholder:text-muted outline-none focus:border-accent focus:ring-2 focus:ring-accent/20" /></div>
      <p id="explore-search-help" className="mt-2 text-xs text-muted">Search names, skills, and interests. Partial words and small spelling mistakes work, too.</p>
      <div className="mt-5 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted"><SlidersHorizontal size={14} /> Refine your search</div>
      <div className="mt-3 grid gap-4 sm:grid-cols-3">
        <label className="space-y-2 text-xs font-medium text-muted"><span className="block">{category === 'projects' ? 'Team role' : 'Role'}</span><select value={role} disabled={!roles.length} onChange={event => setRole(event.target.value)} className={selectClass}><option value="">All roles</option>{roles.map(value => <option key={value} value={value}>{roleNames[value]}</option>)}</select></label>
        <label className="space-y-2 text-xs font-medium text-muted"><span className="block">Skill</span><select value={skill} onChange={event => setSkill(event.target.value)} className={selectClass}><option value="">All skills</option>{skills.map(value => <option key={value}>{value}</option>)}</select></label>
        <label className="space-y-2 text-xs font-medium text-muted"><span className="block">{category === 'projects' ? 'Team major' : 'Major'}</span><select value={major} onChange={event => setMajor(event.target.value)} disabled={!majors.length} className={selectClass}><option value="">{majors.length ? 'All majors' : 'No majors listed'}</option>{majors.map(value => <option key={value}>{value}</option>)}</select></label>
      </div>
      {category === 'projects' && <p className="mt-3 text-xs text-muted">Skills and open roles describe the project. Team roles and majors are unavailable.</p>}
      {category === 'mentors' && <p className="mt-3 text-xs text-muted">Mentors include industry professionals and faculty. Filter by the majors listed on their profiles.</p>}
      {(role || skill || major) && <div className="mt-4 flex flex-wrap gap-2">{[{ value: role, label: roleNames[role], clear: () => setRole('') }, { value: skill, label: skill, clear: () => setSkill('') }, { value: major, label: major, clear: () => setMajor('') }].filter(filter => filter.value).map(filter => <button key={filter.value} onClick={filter.clear} aria-label={`Remove ${filter.label} filter`} className="inline-flex items-center gap-2 rounded-full bg-accent-soft px-3 py-1.5 text-xs text-accent">{filter.label}<X size={12} /></button>)}</div>}
    </section>
    <div className="my-5 flex flex-wrap items-center justify-between gap-3"><p role="status" aria-live="polite" className="text-sm text-muted"><span className="font-semibold text-ink">{results.length}</span> {results.length === 1 ? 'result' : 'results'}{query.trim() && <> for <span className="text-ink">“{query.trim()}”</span></>}</p><div className="flex items-center gap-4">{hasFilters && <button onClick={reset} className="text-xs font-medium text-accent hover:underline">Clear search & filters</button>}<span className="text-xs text-muted">{query.trim() ? 'Best matches first' : 'All results'}</span></div></div>
    {directory.isPending ? <p role="status" className="py-10 text-center text-muted">Loading directory...</p> : directory.isError ? <div role="alert" className="py-10 text-center"><p>Unable to load the directory.</p><button onClick={() => void directory.refetch()} className="mt-3 text-accent hover:underline">Try again</button></div> : results.length ? <div className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">{results.map(({ entry, fuzzy }) => <ResultCard key={entry.id} entry={entry} fuzzy={fuzzy} onSkill={setSkill} />)}</div> : <div className="rounded-2xl border border-dashed border-edge bg-panel px-6 py-14 text-center"><Search size={30} className="mx-auto mb-4 text-muted" /><h2 className="text-lg font-semibold">No matches yet</h2><p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-muted">Try a shorter search, a different skill, or fewer filters.</p><button onClick={reset} className="mt-5 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-brand-hover">Reset search</button></div>}
  </div>
}
