import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Github } from 'lucide-react'
import Avatar from '../components/Avatar'
import { api, post } from '../lib/api'
import type { User } from '../lib/types'

export default function Landing() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const personas = useQuery({
    queryKey: ['personas'],
    queryFn: () => api<User[]>('/auth/demo/personas'),
    retry: 10, // the API starts a moment after Vite under npm run dev
    retryDelay: 1000,
  })

  async function signInAs(id: number) {
    await post(`/auth/demo/${id}`)
    await qc.invalidateQueries({ queryKey: ['me'] })
    navigate('/feed')
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-paper text-navy">
      {/* Soft background shapes, as on the Flash sign-in page */}
      <div className="pointer-events-none absolute -top-40 right-[-10%] h-[42rem] w-[42rem] rounded-full bg-blob/70" />
      <div className="pointer-events-none absolute -bottom-56 right-[-18%] h-[48rem] w-[56rem] rounded-full bg-blob-2/70" />

      <div className="relative mx-auto flex min-h-screen max-w-6xl items-center px-6 py-16">
        <div className="w-full max-w-md">
          <h1 className="text-5xl leading-[1.05] font-semibold tracking-tight">Welcome to Keystone</h1>
          <p className="mt-4 text-lg text-slate">
            A portfolio AI can't fake. Build in public, get help from mentors in minutes, and earn skills backed by
            real code and real people.
          </p>

          <a
            href="/api/auth/github/login"
            className="mt-8 flex h-12 items-center justify-center gap-2 rounded-xl bg-brand font-medium text-white shadow-lg shadow-brand/25 hover:bg-brand-hover"
          >
            <Github size={18} /> Sign in with GitHub
          </a>

          <div className="my-6 flex items-center gap-4 text-sm text-slate">
            <span className="h-px flex-1 bg-line" /> or try a demo persona <span className="h-px flex-1 bg-line" />
          </div>

          {personas.isError && <p className="text-sm text-slate">Start the backend to load personas.</p>}
          <div className="grid gap-2 sm:grid-cols-2">
            {personas.data?.map((p) => (
              <button
                key={p.id}
                onClick={() => signInAs(p.id)}
                className="flex items-center gap-3 rounded-xl border border-line bg-white/80 p-3 text-left hover:border-brand"
              >
                <Avatar user={p} size={34} />
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium">{p.name}</span>
                  <span className="block truncate text-xs text-slate capitalize">
                    {p.role} · {p.company ?? p.major}
                  </span>
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </main>
  )
}
