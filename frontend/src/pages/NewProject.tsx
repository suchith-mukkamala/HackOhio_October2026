import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, api, post } from '../lib/api'
import type { Project } from '../lib/types'

const csv = (v: FormDataEntryValue | null) => String(v ?? '').split(',').map((s) => s.trim()).filter(Boolean)

export default function NewProject({ project, onDone }: { project?: Project; onDone?: () => void } = {}) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  // Only works after "Sign in with GitHub"; other accounts type the repo instead
  const repos = useQuery({ queryKey: ['repos'], queryFn: () => api<{ full_name: string }[]>('/github/repos'), retry: false })

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    setSaving(true)
    setError('')
    try {
      const body = {
        title: f.get('title'),
        description: f.get('description'),
        repo_full_name: f.get('repo') || null,
        tags: csv(f.get('tags')),
        looking_for: csv(f.get('looking_for')),
        start_date: f.get('start_date') || null,
        end_date: f.get('end_date') || null,
      }
      const p = project
        ? await api<Project>(`/projects/${project.id}`, { method: 'PUT', body: JSON.stringify(body) })
        : await post<Project>('/projects', body)
      await qc.invalidateQueries()
      if (onDone) onDone()
      else navigate(`/projects/${p.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save the project.')
    } finally { setSaving(false) }
  }

  const field = 'w-full rounded-lg border border-edge bg-tile px-3 py-2.5 text-sm placeholder:text-muted focus:border-accent focus:outline-none'
  const label = 'mb-1.5 block font-mono text-xs text-muted'

  return (
    <form onSubmit={submit} className="mx-auto flex max-w-xl flex-col gap-5 rounded-2xl border border-edge bg-card p-6">
      <div>
        <h1 className="text-2xl font-semibold">{project ? 'Edit project' : 'Start a project you can finish'}</h1>
        <p className="mt-1 text-sm text-muted">Choose one deliverable, a target finish date, and the teammates who can help.</p>
      </div>

      <label>
        <span className={label}>title</span>
        <input id="title" name="title" defaultValue={project?.title} required placeholder="BuckeyeBus Live" className={field} />
      </label>
      <label>
        <span className={label}>description</span>
        <textarea id="description" name="description" defaultValue={project?.description} rows={4} placeholder="Who is this for? What will you deliver? What must work for your team to call it finished?" aria-describedby="project-scope-help" className={field} />
        <span id="project-scope-help" className="mt-2 block text-xs leading-relaxed text-muted">Define a small, concrete result: a working demo, a tested prototype, or a published release. Save extra ideas for a later version.</span>
      </label>
      <label>
        <span className={label}>github repo</span>
        <input id="repo" name="repo" defaultValue={project?.repo_full_name ?? ''} list="repo-options" placeholder="owner/repo" className={`${field} font-mono`} />
        <datalist id="repo-options">
          {repos.data?.map((r) => <option key={r.full_name} value={r.full_name} />)}
        </datalist>
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label>
          <span className={label}>tags</span>
          <input id="tags" name="tags" defaultValue={project?.tags.join(', ')} placeholder="Python, React, SQL" className={field} />
        </label>
        <label>
          <span className={label}>looking for</span>
          <input id="looking_for" name="looking_for" defaultValue={project?.looking_for.join(', ')} placeholder="Frontend dev, Designer" className={field} />
        </label>
        <label>
          <span className={label}>starts</span>
          <input id="start_date" name="start_date" defaultValue={project?.start_date ?? ''} type="date" className={`${field} [color-scheme:dark]`} />
        </label>
        <label>
          <span className={label}>target finish date</span>
          <input id="end_date" name="end_date" defaultValue={project?.end_date ?? ''} type="date" className={`${field} [color-scheme:dark]`} />
        </label>
      </div>

      {error && <p className="rounded-lg bg-warn/10 px-3 py-2 text-sm text-warn">{error}</p>}
      <div className="flex justify-end gap-3">{onDone && <button type="button" disabled={saving} onClick={onDone} className="px-4 py-2 text-sm">Cancel</button>}<button disabled={saving} className="rounded-lg bg-accent px-4 py-2.5 font-semibold text-white disabled:opacity-40">{saving ? 'Saving...' : project ? 'Save changes' : 'Publish project'}</button></div>
    </form>
  )
}
