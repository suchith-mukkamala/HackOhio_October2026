import { useState } from 'react'
import type { FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { Github } from 'lucide-react'
import { ApiError, post } from '../lib/api'

// Sign-in page; with `register` it becomes the create-account page at /register
export default function Landing({ register = false }: { register?: boolean }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [error, setError] = useState('')
  const [role, setRole] = useState<'student' | 'faculty' | 'mentor'>('student')

  async function signIn(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    // Leave out empty optional fields (major, title...) instead of saving blanks
    const f = Object.fromEntries([...new FormData(e.currentTarget)].filter(([, v]) => v !== ''))
    try {
      await post(register ? '/auth/register' : '/auth/login', f)
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
          <h1 className="text-5xl leading-[1.05] font-semibold tracking-tight">
            {register ? 'Join Keystone' : 'Welcome to Keystone'}
          </h1>
          <p className="mt-4 text-lg text-slate">A portfolio AI can't fake.</p>

          <form key={String(register)} onSubmit={signIn} className="mt-8 flex flex-col gap-4">
            {register && (
              <>
                <fieldset>
                  <legend className="mb-1.5 text-sm font-medium">I am a…</legend>
                  <div className="grid grid-cols-3 gap-2">
                    {([['student', 'Student'], ['faculty', 'Faculty'], ['mentor', 'Industry pro']] as const).map(([value, label]) => (
                      <label key={value} className={`cursor-pointer rounded-xl border px-3 py-2.5 text-center text-sm font-medium ${role === value ? 'border-brand bg-brand/10 text-brand' : 'border-line bg-white text-slate hover:border-brand/60'}`}>
                        <input type="radio" name="role" value={value} checked={role === value} onChange={() => setRole(value)} className="sr-only" />
                        {label}
                      </label>
                    ))}
                  </div>
                </fieldset>
                {role === 'student' ? (
                  <div className="grid grid-cols-[1fr_8rem] gap-3">
                    <input id="major" name="major" placeholder="Major" className={field} />
                    <input id="year" name="year" placeholder="Year" className={field} />
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-3">
                    <input id="title" name="title" placeholder={role === 'faculty' ? 'Title (e.g. Professor)' : 'Job title'} className={field} />
                    <input id="company" name="company" placeholder={role === 'faculty' ? 'Department' : 'Company'} className={field} />
                  </div>
                )}
                <label>
                  <span className="mb-1.5 block text-sm font-medium">Full name</span>
                  <input id="name" name="name" required autoComplete="name" className={field} />
                </label>
                <label>
                  <span className="mb-1.5 block text-sm font-medium">Email</span>
                  <input id="email" name="email" type="email" required autoComplete="email" className={field} />
                </label>
              </>
            )}
            <label>
              <span className="mb-1.5 block text-sm font-medium">Username</span>
              <input id="username" name="username" required minLength={3} autoComplete="username" className={field} />
            </label>
            <label>
              <span className="mb-1.5 block text-sm font-medium">Password</span>
              <input
                id="password"
                name="password"
                type="password"
                required
                minLength={register ? 12 : undefined}
                autoComplete={register ? 'new-password' : 'current-password'}
                placeholder={register ? 'At least 12 characters' : 'Enter your password'}
                className={field}
              />
            </label>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button className="h-12 rounded-xl bg-brand font-medium text-white shadow-lg shadow-brand/25 hover:bg-brand-hover">
              {register ? 'Create account' : 'Sign in'}
            </button>
            <p className="text-center text-sm text-slate">
              {register ? 'Already have an account? ' : 'New to Keystone? '}
              <Link to={register ? '/' : '/register'} onClick={() => setError('')} className="font-medium text-brand underline underline-offset-2">
                {register ? 'Sign in' : 'Create an account'}
              </Link>
            </p>
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
