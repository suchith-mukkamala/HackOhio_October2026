// Mirrors backend/app/models.py. Keep the two in sync when the contract changes.
export type Role = 'student' | 'mentor' | 'faculty'

export interface User {
  id: number
  role: Role
  name: string
  major?: string
  year?: string
  company?: string
  title?: string
  bio?: string
  avatar_url?: string
  github_username?: string
  expertise_tags: string[]
}

export interface Project {
  id: number
  owner_id: number
  title: string
  description: string
  repo_full_name?: string
  tags: string[]
  looking_for: string[]
  status: 'active' | 'archived'
  start_date?: string
  end_date?: string
}

export interface LogEntry {
  id: number
  project_id: number
  author_id: number
  week_label: string
  title: string
  built: string[]
  learned: string[]
  stuck: string[]
  skills: string[]
  source: 'ai' | 'manual'
  published: boolean
  created_at: string
}

export interface HelpRequest {
  id: number
  project_id: number
  requester_id: number
  question: string
  tags: string[]
  minutes: 5 | 15 | 30
  status: 'open' | 'answered' | 'resolved'
  mentor_id?: number
  answer?: string
  helpful?: boolean
  created_at: string
  match_score?: number
}

export type SkillTier = 'claimed' | 'code' | 'peer' | 'mentor'

export interface SkillNode {
  skill: string
  score: number
  tier: SkillTier
  evidence: { kind: 'code' | 'peer' | 'mentor' | 'help_given'; label: string }[]
}

export interface SkillGraph {
  nodes: SkillNode[]
  edges: { a: string; b: string; weight: number }[]
}
