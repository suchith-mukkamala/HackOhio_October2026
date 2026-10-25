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
  is_admin?: boolean
  expertise_tags: string[]
}

// Body of PUT /me. Only these fields can be edited; send the full expertise_tags list each time.
export type MeUpdate = Partial<
  Pick<User, 'bio' | 'major' | 'year' | 'company' | 'title' | 'expertise_tags'>
>

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

export type MediaKind = 'image' | 'video' | 'youtube'

export interface FollowRequest {
  id: number
  sender_id: number
  recipient_id: number
  thread_id: number
  message_id: number
  status: 'pending' | 'accepted' | 'denied'
  created_at: string
  responded_at: string | null
}

export interface ConnectionsData {
  interconnections: { source: number; target: number }[]
  connections: User[]
  requests: (FollowRequest & { user: User })[]
}

export interface Comment {
  id: number
  author_id: number
  author_name?: string | null
  body: string
  created_at: string
}

// One row of GET /feed
export interface FeedItem {
  post: { id: number; author_id: number; body: string; type: 'update' | 'log' | 'question'; created_at: string; media_url?: string | null; media_kind?: MediaKind | null }
  author: User | null
  project: Project | null
  log: LogEntry | null
  comments: Comment[]
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

// Strongest kind of evidence behind a skill the user actually has.
export type SkillTier = 'claimed' | 'code' | 'peer' | 'mentor'

// 'category' = top-level branch (Programming, Hardware...). 'derived' = a parent skill that
// only appears because one of its children is strong (e.g. Python above FastAPI).
export type NodeTier = SkillTier | 'category' | 'derived'

export interface SkillNode {
  skill: string
  parent: string | null // name of another node, or null for a top-level category
  score: number
  pulse: number // 0..1: strongest score at or below this node / user's strongest score
  tier: NodeTier
  evidence: { kind: 'claimed' | 'code' | 'peer' | 'mentor' | 'help_given'; label: string }[]
}

export interface SkillGraph {
  nodes: SkillNode[]
  edges: { a: string; b: string; weight: number }[] // skills used together on a project
}

// GET /skills/vocabulary: the fixed tree, for the onboarding picker.
export interface SkillVocabulary {
  categories: string[]
  skills: { skill: string; parent: string | null }[]
}
export interface ProfilePreferences {
  availability: 'not_looking' | 'teammates' | 'projects' | 'mentorship' | 'available_to_mentor'
  preferred_roles: string[]
  interests: string[]
  hours_per_week: number
  website: string
  linkedin: string
  contact_email: string
  show_experience: boolean
  show_activity: boolean
  show_contact: boolean
  direct_messages: 'everyone' | 'teammates' | 'nobody'
  group_invites: 'everyone' | 'teammates' | 'nobody'
  particles: boolean
  reduce_motion: boolean
  highlighted_skills: string[]
  pinned_project_ids: number[]
  pinned_post_id: number | null
}
export interface ExperienceEntry {
  id: number
  kind: 'work' | 'education'
  title: string
  org: string
  start: string
  end: string
  summary: string
  skills: string[]
}
export interface SettingsData {
  user: User
  preferences: ProfilePreferences
  account: { username: string | null; email: string | null; has_password: boolean; github_connected: boolean; google_connected: boolean; google_email: string | null; github_available: boolean; google_available: boolean }
  projects: Project[]
  posts: FeedItem['post'][]
  experience: ExperienceEntry[]
}
