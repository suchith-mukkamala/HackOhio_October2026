import { createSearchIndex } from './exploreSearch'
import type { Role } from './types'

export type ExploreCategory = 'students' | 'projects' | 'mentors'
export type ExploreEntry = {
  id: string
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

// Standalone example records; these identifiers intentionally do not imply database IDs.
export const exploreEntries: ExploreEntry[] = [
  { id: 'maya', category: 'students', name: 'Maya Chen', subtitle: '3rd year · Computer Science & Engineering', description: 'Backend-curious, learning FastAPI by breaking it. Building live campus bus arrivals with BuckeyeBus Live.', skills: ['Python', 'SQL', 'FastAPI', 'React'], roles: ['student'], majors: ['Computer Science & Engineering'] },
  { id: 'jordan', category: 'students', name: 'Jordan Reyes', subtitle: '2nd year · Mechanical Engineering', description: 'Builds robots and wants to learn the software side. Working on a web-controlled rover arm.', skills: ['CAD', 'Arduino', 'C++'], roles: ['student'], majors: ['Mechanical Engineering'] },
  { id: 'priya', category: 'students', name: 'Priya Natarajan', subtitle: '4th year · Design', description: 'UX researcher who prototypes in Figma. Making campus transit easier to navigate, one usability session at a time.', skills: ['UI Design', 'UX Research', 'Figma'], roles: ['student'], majors: ['Design'] },
  { id: 'sam', category: 'mentors', name: 'Sam Okafor', subtitle: 'Software Engineer · Honda R&D', description: 'Happy to give 15 minutes on backend and cloud. Bring a question, a code snippet, or something you are stuck on.', skills: ['Python', 'FastAPI', 'AWS', 'Docker', 'System Design'], roles: ['mentor'], majors: [] },
  { id: 'elena', category: 'mentors', name: 'Elena Park', subtitle: 'Data Scientist · 99P Labs', description: 'ML, data pipelines, and making charts honest. Here to help turn your measurements into useful insights.', skills: ['Machine Learning', 'Data Analysis', 'Python', 'SQL'], roles: ['mentor'], majors: [] },
  { id: 'marcus', category: 'mentors', name: 'Dr. Marcus Lee', subtitle: 'Senior Lecturer · Ohio State CSE', description: 'Advises capstone teams. Happy to discuss project scope, testing, and how to show the work behind your progress.', skills: ['System Design', 'Testing', 'Project Management'], roles: ['faculty'], majors: [] },
  { id: 'bus', category: 'projects', name: 'BuckeyeBus Live', subtitle: 'Campus transit · In progress', description: 'Real-time campus bus arrivals with crowding estimates. Help build a clearer picture of the next bus.', skills: ['Python', 'FastAPI', 'React', 'SQL'], roles: ['student'], majors: ['Computer Science & Engineering', 'Design'], lookingFor: ['Frontend dev', 'Data person'], team: ['Maya Chen', 'Priya Natarajan'] },
  { id: 'rover', category: 'projects', name: 'Mars Rover Arm', subtitle: 'Robotics · In progress', description: 'A 4-DOF arm for the rover club, controlled from a web dashboard. Help connect the hardware to the interface.', skills: ['Arduino', 'C++', 'CAD', 'React'], roles: ['student'], majors: ['Mechanical Engineering'], lookingFor: ['Embedded dev'], team: ['Jordan Reyes'] },
]

export const exploreById = new Map(exploreEntries.map(entry => [entry.id, entry]))
export const exploreIndex = createSearchIndex(exploreEntries.map(entry => ({
  id: entry.id,
  fields: [
    { text: entry.name, weight: 5 },
    { text: entry.skills.join(' '), weight: 4 },
    { text: [entry.subtitle, ...entry.majors, ...entry.roles, ...(entry.team ?? []), ...(entry.lookingFor ?? [])].join(' '), weight: 2 },
    { text: entry.description, weight: 1 },
  ],
})))
