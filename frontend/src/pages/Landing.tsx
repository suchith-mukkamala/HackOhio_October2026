import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
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
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-8 px-4 py-12">
      <div>
        <h1 className="text-4xl font-bold text-scarlet">Keystone</h1>
        <p className="mt-3 text-lg">
          A portfolio AI can't fake. Build in public, get help from mentors in minutes, and earn skills
          backed by real code and real people.
        </p>
      </div>

      <a href="/api/auth/github/login" className="w-fit rounded-md bg-ink px-4 py-2 font-medium text-white">
        Sign in with GitHub
      </a>

      <section>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-black/50">Demo personas</h2>
        {personas.isError && <p className="mt-2 text-sm text-black/60">Start the backend to load personas.</p>}
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {personas.data?.map((p) => (
            <button
              key={p.id}
              onClick={() => signInAs(p.id)}
              className="rounded-md border border-black/10 bg-white px-3 py-2 text-left hover:border-scarlet"
            >
              <span className="font-medium">{p.name}</span>
              <span className="block text-xs text-black/60">
                {p.role} · {p.company ?? p.major}
              </span>
            </button>
          ))}
        </div>
      </section>
    </main>
  )
}
