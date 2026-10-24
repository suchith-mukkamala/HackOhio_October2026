import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import type { User } from './types'

// "CSE · 3rd year" for students, "Software Engineer at Honda R&D" for mentors
export const headline = (u: User) =>
  u.role === 'student' ? [u.major, u.year].filter(Boolean).join(' · ') : [u.title, u.company].filter(Boolean).join(' at ')

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: () => api<User>('/me'), retry: false })
}
