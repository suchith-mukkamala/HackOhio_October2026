import { createSearchIndex } from './exploreSearch'
import type { Project, Role, User } from './types'
import { headline } from './auth'

export type ExploreCategory = 'students' | 'projects' | 'mentors'
export type ExploreEntry = {
  id: string
  href: string
  avatar_url?: string
  category: ExploreCategory
  name: string
  subtitle: string
  description: string
  skills: string[]
  roles: Role[]
  majors: string[]
  lookingFor?: string[]
  team?: string[]
}

export function userEntry(user: User): ExploreEntry {
  return { id: 'user-' + user.id, href: '/u/' + user.id, avatar_url: user.avatar_url,
    category: user.role === 'student' ? 'students' : 'mentors', name: user.name,
    subtitle: headline(user), description: user.bio ?? '', skills: user.expertise_tags,
    roles: [user.role], majors: user.major ? [user.major] : [] }
}
export function projectEntry(project: Project): ExploreEntry {
  return { id: 'project-' + project.id, href: '/projects/' + project.id, category: 'projects',
    name: project.title, subtitle: 'In progress', description: project.description,
    skills: project.tags, roles: [], majors: [], lookingFor: project.looking_for }
}
export const indexEntries = (entries: ExploreEntry[]) => createSearchIndex(entries.map(entry => ({
  id: entry.id,
  fields: [
    { text: entry.name, weight: 5 },
    { text: entry.skills.join(' '), weight: 4 },
    { text: [entry.subtitle, ...entry.majors, ...entry.roles, ...(entry.lookingFor ?? [])].join(' '), weight: 2 },
    { text: entry.description, weight: 1 },
  ],
})))
