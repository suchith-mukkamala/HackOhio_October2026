import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ApiError, api, post } from '../lib/api'
import type { Project } from '../lib/types'

const csv = (v: FormDataEntryValue | null) => String(v ?? '').split(',').map((s) => s.trim()).filter(Boolean)

export default function NewProject() {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  // Only works after "Sign in with GitHub"; other accounts type the repo instead
  const repos = useQuery({ queryKey: ['repos'], queryFn: () => api<{ full_name: string }[]>('/github/repos'), retry: false })

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    try {
      const p = await post<Project>('/projects', {
        title: f.get('title'),
        description: f.get('description'),
        repo_full_name: f.get('repo') || null,
        tags: csv(f.get('tags')),
        looking_for: csv(f.get('looking_for')),
        start_date: f.get('start_date') || null,
        end_date: f.get('end_date') || null,
      })
      navigate(`/projects/${p.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create the project.')
    }
  }

  const field = 'w-full rounded-lg border border-edge bg-tile px-3 py-2.5 text-sm placeholder:text-muted focus:border-accent focus:outline-none'
  const label = 'mb-1.5 block font-mono text-xs text-muted'

  return (
    <form onSubmit={submit} className="mx-auto flex max-w-xl flex-col gap-5 rounded-2xl border border-edge bg-card p-6">
      <div>
        <h1 className="text-2xl font-semibold">Push a project</h1>
        <p className="mt-1 text-sm text-muted">4–6 weeks, real work, with mentors one click away.</p>
      </div>

      <label>
        <span className={label}>title</span>
        <input id="title" name="title" required placeholder="BuckeyeBus Live" className={field} />
      </label>
      <label>
        <span className={label}>description</span>
        <textarea id="description" name="description" rows={3} placeholder="What are you building, and for whom?" className={field} />
      </label>
      <label>
        <span className={label}>github repo</span>
        <input id="repo" name="repo" list="repo-options" placeholder="owner/repo" className={`${field} font-mono`} />
        <datalist id="repo-options">
          {repos.data?.map((r) => <option key={r.full_name} value={r.full_name} />)}
        </datalist>
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label>
          <span className={label}>tags</span>
          <input id="tags" name="tags" placeholder="Python, React, SQL" className={field} />
        </label>
        <label>
          <span className={label}>looking for</span>
          <input id="looking_for" name="looking_for" placeholder="Frontend dev, Designer" className={field} />
        </label>
        <label>
          <span className={label}>starts</span>
          <input id="start_date" name="start_date" type="date" className={`${field} [color-scheme:dark]`} />
        </label>
        <label>
          <span className={label}>ends</span>
          <input id="end_date" name="end_date" type="date" className={`${field} [color-scheme:dark]`} />
        </label>
      </div>

      {error && <p className="rounded-lg bg-warn/10 px-3 py-2 text-sm text-warn">{error}</p>}
      <button className="rounded-lg bg-accent py-2.5 font-semibold text-white hover:opacity-90">Publish project</button>
    </form>
  )
}
