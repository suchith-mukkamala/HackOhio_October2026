import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Avatar from '../components/Avatar'
import { ApiError, api, post, put } from '../lib/api'
import { useMe } from '../lib/auth'
import type { Role, User } from '../lib/types'

const ROLES: Role[] = ['student', 'mentor', 'faculty']

// Anyone signed in can open this page. Only the secret code unlocks the admin tools.
function RedeemCode() {
  const qc = useQueryClient()
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [unlocking, setUnlocking] = useState(false)

  async function redeem(e: FormEvent) {
    e.preventDefault()
    if (unlocking) return
    setUnlocking(true)
    setError('')
    try {
      await post('/admin/redeem', { code })
      setCode('')
      await qc.invalidateQueries({ queryKey: ['me'] })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not check that code.')
    } finally {
      setUnlocking(false)
    }
  }

  return (
    <form onSubmit={redeem} className="max-w-md rounded-2xl border border-edge bg-card p-5">
      <h1 className="text-lg font-semibold">Admin access</h1>
      <p className="mt-1 text-sm text-muted">Enter the shared admin code to grant admin privileges to your signed-in account.</p>
      <input
        id="admin-code"
        aria-label="Shared admin code"
        type="password"
        autoComplete="off"
        value={code}
        onChange={(e) => {
          setCode(e.target.value)
          setError('')
        }}
        placeholder="Admin code"
        className="mt-3 w-full rounded-lg bg-tile px-3 py-2 text-sm placeholder:text-muted focus:ring-1 focus:ring-accent focus:outline-none"
      />
      {error && <p className="mt-1 text-sm text-warn">{error}</p>}
      <button
        type="submit"
        disabled={unlocking || !code.trim()}
        className="mt-3 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
      >
        {unlocking ? 'Unlocking...' : 'Unlock'}
      </button>
    </form>
  )
}

// Everyone on the platform, with a role switch (handy for demoing both the student and mentor sides).
function UserList({ meId }: { meId: number }) {
  const qc = useQueryClient()
  const [error, setError] = useState('')
  const { data: users, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => api<User[]>('/admin/users'),
  })

  async function changeRole(id: number, role: Role) {
    try {
      await put(`/admin/users/${id}/role`, { role })
      setError('')
      await qc.invalidateQueries({ queryKey: ['admin-users'] })
      if (id === meId) await qc.invalidateQueries({ queryKey: ['me'] })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not change that role.')
    }
  }

  return (
    <section>
      <h1 className="text-lg font-semibold">Admin</h1>
      <p className="mt-1 text-sm text-muted">Switch anyone between student, mentor and faculty.</p>
      {error && <p className="mt-2 text-sm text-warn">{error}</p>}
      {isLoading && <p className="mt-4 text-muted">Loading users...</p>}
      <ul className="mt-4 divide-y divide-edge rounded-2xl border border-edge bg-card">
        {(users ?? []).map((u) => (
          <li key={u.id} className="flex items-center gap-3 px-4 py-3">
            <Avatar user={u} size={32} />
            <Link to={`/u/${u.id}`} className="min-w-0 flex-1 truncate text-sm hover:text-accent">
              {u.name}
              {u.is_admin && (
                <span className="ml-2 rounded-full bg-accent-soft px-2 py-0.5 font-mono text-xs text-accent">admin</span>
              )}
            </Link>
            <select
              id={`role-${u.id}`}
              aria-label={`Role for ${u.name}`}
              value={u.role}
              onChange={(e) => changeRole(u.id, e.target.value as Role)}
              className="rounded-lg bg-tile px-2 py-2 text-sm"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function Admin() {
  const { data: me, isLoading } = useMe()
  if (!me) return <p className="text-muted">{isLoading ? 'Loading...' : 'Sign in to continue.'}</p>
  return me.is_admin ? <UserList meId={me.id} /> : <RedeemCode />
}
