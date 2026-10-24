import { useState } from 'react'
import type { FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Github } from 'lucide-react'
import { ApiError, post } from '../lib/api'

export default function Landing() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [error, setError] = useState('')

  async function signIn(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    try {
      await post('/auth/login', { username: f.get('username'), password: f.get('password') })
      await qc.invalidateQueries({ queryKey: ['me'] })
      navigate('/feed')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not sign in.')
    }
  }

  const field = 'h-12 w-full rounded-xl border border-line bg-white px-4 text-navy placeholder:text-slate/70 focus:border-brand focus:outline-none'
  const oauth = 'flex h-12 items-center justify-center gap-2 rounded-xl border border-line bg-white font-medium hover:border-brand'

  return (
    <main className="relative min-h-screen overflow-hidden bg-paper text-navy">
      {/* Soft background shapes, as on the Flash sign-in page */}
      <div className="pointer-events-none absolute -top-40 right-[-10%] h-[42rem] w-[42rem] rounded-full bg-blob/70" />
      <div className="pointer-events-none absolute -bottom-56 right-[-18%] h-[48rem] w-[56rem] rounded-full bg-blob-2/70" />

      <div className="relative mx-auto flex min-h-screen max-w-6xl items-center px-6 py-16">
        <div className="w-full max-w-md">
          <h1 className="text-5xl leading-[1.05] font-semibold tracking-tight">Welcome to Keystone</h1>
          <p className="mt-4 text-lg text-slate">A portfolio AI can't fake.</p>

          <form onSubmit={signIn} className="mt-8 flex flex-col gap-4">
            <label>
              <span className="mb-1.5 block text-sm font-medium">Username</span>
              <input id="username" name="username" required autoComplete="username" className={field} />
            </label>
            <label>
              <span className="mb-1.5 block text-sm font-medium">Password</span>
              <input id="password" name="password" type="password" required autoComplete="current-password" placeholder="Enter your password" className={field} />
            </label>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button className="h-12 rounded-xl bg-brand font-medium text-white shadow-lg shadow-brand/25 hover:bg-brand-hover">Sign in</button>
          </form>

          <div className="my-6 flex items-center gap-4 text-sm text-slate">
            <span className="h-px flex-1 bg-line" /> or <span className="h-px flex-1 bg-line" />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <a href="/api/auth/google/login" className={oauth}>
              <span className="text-lg font-bold text-brand">G</span> Google
            </a>
            <a href="/api/auth/github/login" className={oauth}>
              <Github size={18} /> GitHub
            </a>
          </div>
        </div>
      </div>
    </main>
  )
}
