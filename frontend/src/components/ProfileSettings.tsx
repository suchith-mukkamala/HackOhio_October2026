import { useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, put } from '../lib/api'
import type { ExperienceEntry, SettingsData, SkillGraph, SkillVocabulary } from '../lib/types'

const field = 'mt-1 w-full rounded-lg border border-edge bg-tile px-3 py-2 text-sm text-ink outline-none focus:border-accent'
const button = 'rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-40'
function Group({ title, children }: { title: string; children: ReactNode }) { return <fieldset className="space-y-4 rounded-xl border border-edge p-4"><legend className="px-2 font-semibold">{title}</legend>{children}</fieldset> }
function Text({ label, name, value, type = 'text', maxLength }: { label: string; name: string; value?: string | number | null; type?: string; maxLength?: number }) { return <label className="block text-sm text-muted">{label}<input name={name} type={type} defaultValue={value ?? ''} maxLength={maxLength} className={field} /></label> }
function Toggle({ label, name, checked }: { label: string; name: string; checked: boolean }) { return <label className="flex items-center gap-3 text-sm"><input name={name} type="checkbox" defaultChecked={checked} />{label}</label> }
const csv = (value: FormDataEntryValue | null) => String(value ?? '').split(',').map(value => value.trim()).filter(Boolean)

function ExperienceEditor({ entry, refresh }: { entry: ExperienceEntry; refresh: () => Promise<void> }) {
  const [editing, setEditing] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget); setBusy(true); setError('')
    try { await put(`/me/experience/${entry.id}`, { ...Object.fromEntries(data), skills: csv(data.get('skills')) }); await refresh(); setEditing(false) }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not save experience.') }
    finally { setBusy(false) }
  }
  async function remove() {
    setBusy(true); setError('')
    try { await api(`/me/experience/${entry.id}`, { method: 'DELETE' }); await refresh() }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not remove experience.') }
    finally { setBusy(false) }
  }
  return <div className="rounded-lg border border-edge p-3">{editing ? <form onSubmit={save} className="space-y-3">
    <label className="text-sm">Type<select name="kind" defaultValue={entry.kind} className={field}><option value="work">Work</option><option value="education">Education</option></select></label>
    <Text label="Title" name="title" value={entry.title} maxLength={200} /><Text label="Organization" name="org" value={entry.org} maxLength={200} />
    <div className="grid grid-cols-2 gap-3"><Text label="Start" name="start" value={entry.start} /><Text label="End" name="end" value={entry.end} /></div>
    <label className="block text-sm">Summary<textarea name="summary" defaultValue={entry.summary} maxLength={2000} className={field} /></label>
    <Text label="Skills (comma separated, from the skill vocabulary)" name="skills" value={entry.skills.join(', ')} />
    <button disabled={busy} className={button}>Save entry</button><button type="button" disabled={busy} onClick={() => setEditing(false)} className="ml-3 text-sm">Cancel</button>
  </form> : <><p className="text-sm font-medium">{entry.title} at {entry.org}</p><div className="mt-2 flex gap-4 text-sm"><button onClick={() => setEditing(true)} className="text-accent">Edit</button><button onClick={() => setConfirm(true)} className="text-muted">Remove</button></div>{confirm && <div className="mt-3 text-sm"><p>Remove this entry and its resume skill evidence?</p><button disabled={busy} onClick={() => void remove()} className="mt-2 text-warn">Confirm remove</button><button onClick={() => setConfirm(false)} className="ml-3">Cancel</button></div>}</>}{error && <p role="alert" className="mt-2 text-sm text-warn">{error}</p>}</div>
}

function SettingsForm({ data, onClose }: { data: SettingsData; onClose: () => void }) {
  const qc = useQueryClient()
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [removeResume, setRemoveResume] = useState(false)
  const vocabulary = useQuery({ queryKey: ['vocabulary'], queryFn: () => api<SkillVocabulary>('/skills/vocabulary') })
  const graph = useQuery({ queryKey: ['skills', data.user.id], queryFn: () => api<SkillGraph>(`/users/${data.user.id}/skills`) })
  const graphSkills = new Set(graph.data?.nodes.map(node => node.skill) ?? [])
  const pref = data.preferences
  const refresh = async () => { await qc.invalidateQueries() }
  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true); setMessage(''); setError('')
    try { await action(); await refresh(); setMessage(success) }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not save changes.') }
    finally { setBusy(false) }
  }
  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const f = new FormData(event.currentTarget)
    const preferences = { ...pref }
    for (const key of ['availability', 'website', 'linkedin', 'contact_email', 'direct_messages', 'group_invites'] as const) Object.assign(preferences, { [key]: String(f.get(key) ?? '') })
    for (const key of ['show_experience', 'show_activity', 'show_contact', 'particles', 'reduce_motion'] as const) preferences[key] = f.has(key)
    preferences.preferred_roles = csv(f.get('preferred_roles')); preferences.interests = csv(f.get('interests'))
    preferences.hours_per_week = Number(f.get('hours_per_week'))
    preferences.pinned_project_ids = f.getAll('pinned_project_ids').map(Number)
    preferences.pinned_post_id = f.get('pinned_post_id') ? Number(f.get('pinned_post_id')) : null
    preferences.highlighted_skills = f.getAll('highlighted_skills').map(String)
    const profile = Object.fromEntries(['name', 'bio', 'major', 'year', 'company', 'title', 'avatar_url'].map(key => [key, String(f.get(key) ?? '')]))
    void run(() => put('/me/settings', { profile, preferences }), 'Profile settings saved.')
  }
  function password(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const f = new FormData(form)
    if (f.get('new_password') !== f.get('confirm_password')) { setError('The new passwords do not match.'); return }
    void run(async () => { await put('/me/password', Object.fromEntries(f)); form.reset() }, 'Password updated.')
  }
  const rule = (name: 'direct_messages' | 'group_invites', label: string) => <label className="block text-sm text-muted">{label}<select name={name} defaultValue={pref[name]} className={field}><option value="everyone">Everyone</option><option value="teammates">Project teammates only</option><option value="nobody">Nobody</option></select></label>
  return <section aria-label="Profile settings" className="mb-6 rounded-2xl border border-edge bg-card p-5 sm:p-6">
    <div className="mb-5 flex items-center justify-between"><h2 className="text-xl font-semibold">Profile settings</h2><button onClick={onClose} className="text-sm text-muted">Close</button></div>
    {error && <p role="alert" className="mb-4 rounded-lg bg-warn/10 p-3 text-sm text-warn">{error}</p>}{message && <p role="status" className="mb-4 rounded-lg bg-good-soft p-3 text-sm text-good">{message}</p>}
    <form onSubmit={save} className="space-y-5">
      <Group title="Profile details"><div className="grid gap-4 sm:grid-cols-2"><Text label="Full name" name="name" value={data.user.name} maxLength={100} /><Text label="Avatar image URL (https)" name="avatar_url" value={data.user.avatar_url} type="url" />
        <Text label="Major" name="major" value={data.user.major} maxLength={100} /><Text label="Year" name="year" value={data.user.year} maxLength={30} /><Text label="Job title" name="title" value={data.user.title} /><Text label="Company / department" name="company" value={data.user.company} />
        <Text label="Website (https)" name="website" value={pref.website} type="url" /><Text label="LinkedIn (https)" name="linkedin" value={pref.linkedin} type="url" /><Text label="Public contact email" name="contact_email" value={pref.contact_email} type="email" /></div><label className="block text-sm text-muted">Bio<textarea name="bio" defaultValue={data.user.bio} maxLength={500} rows={3} className={field} /></label></Group>
      <Group title="Availability and collaboration"><label className="block text-sm text-muted">Open to<select name="availability" defaultValue={pref.availability} className={field}><option value="not_looking">Not currently looking</option><option value="teammates">Finding teammates</option><option value="projects">Joining projects</option><option value="mentorship">Finding a mentor</option><option value="available_to_mentor">Mentoring others</option></select></label><div className="grid gap-4 sm:grid-cols-2"><Text label="Preferred roles (comma separated)" name="preferred_roles" value={pref.preferred_roles.join(', ')} /><Text label="Interests (comma separated)" name="interests" value={pref.interests.join(', ')} /></div><label className="block text-sm text-muted">Hours available per week<input type="number" name="hours_per_week" min={0} max={80} defaultValue={pref.hours_per_week} className={field} /></label></Group>
      <Group title="Pinned content"><p className="text-xs text-muted">Choose up to six projects. With none selected, your projects appear automatically.</p><div className="max-h-44 space-y-2 overflow-y-auto">{data.projects.map(project => <label key={project.id} className="flex items-center gap-3 text-sm"><input type="checkbox" name="pinned_project_ids" value={project.id} defaultChecked={pref.pinned_project_ids.includes(project.id)} />{project.title}</label>)}{!data.projects.length && <p className="text-sm text-muted">Join or create a project to pin it.</p>}</div><label className="block text-sm text-muted">Featured post<select name="pinned_post_id" defaultValue={pref.pinned_post_id ?? ''} className={field}><option value="">Most recent post automatically</option>{data.posts.map(post => <option key={post.id} value={post.id}>{post.body.slice(0, 100) || 'Weekly log'}</option>)}</select></label></Group>
      <Group title="Privacy"><Toggle label="Show experience and education to others" name="show_experience" checked={pref.show_experience} /><Toggle label="Show posts on profiles and the feed" name="show_activity" checked={pref.show_activity} /><Toggle label="Show contact details and social links" name="show_contact" checked={pref.show_contact} /><p className="text-xs text-muted">You can always see your own information. Project timelines remain visible to collaborators and visitors.</p></Group>
      <Group title="Messaging permissions">{rule('direct_messages', 'Who can start a direct conversation?')}{rule('group_invites', 'Who can add you to a new group?')}<p className="text-xs text-muted">Existing conversations remain available.</p></Group>
      <Group title="Skill graph"><Toggle label="Show flowing particles" name="particles" checked={pref.particles} /><Toggle label="Reduce graph motion" name="reduce_motion" checked={pref.reduce_motion} /><p className="text-xs text-muted">Your display preferences apply while you browse. Highlight up to ten skills on your own graph.</p><div className="grid max-h-48 grid-cols-2 gap-2 overflow-y-auto">{vocabulary.data?.skills.filter(({ skill }) => graphSkills.has(skill)).map(({ skill }) => <label key={skill} className="flex items-center gap-2 text-sm"><input type="checkbox" name="highlighted_skills" value={skill} defaultChecked={pref.highlighted_skills.includes(skill)} />{skill}</label>)}</div>{vocabulary.isError && <p role="alert" className="text-sm text-warn">Skills could not load. Close settings and try again before saving.</p>}</Group>
      <div className="flex items-center justify-end gap-3"><button type="button" onClick={onClose} disabled={busy} className="px-3 text-sm">Cancel</button><button disabled={busy || vocabulary.isPending || vocabulary.isError || graph.isPending || graph.isError} className={button}>{busy ? 'Saving...' : 'Save profile settings'}</button></div>
    </form>
    <div className="mt-6 space-y-5">
      <Group title="Resume and experience"><p className="text-sm text-muted">Use Upload resume on your profile to replace your history. The PDF itself is not stored.</p>{data.experience.map(entry => <ExperienceEditor key={entry.id} entry={entry} refresh={refresh} />)}{!data.experience.length && <p className="text-sm text-muted">No experience entries yet.</p>}{data.experience.length > 0 && (removeResume ? <div className="text-sm"><p>Remove all resume-derived history and its skill evidence? Your bio and manually listed skills stay.</p><button disabled={busy} onClick={() => void run(() => api('/me/resume', { method: 'DELETE' }), 'Resume history removed.')} className="mt-2 text-warn">Confirm removal</button><button onClick={() => setRemoveResume(false)} className="ml-4">Cancel</button></div> : <button onClick={() => setRemoveResume(true)} className="text-sm text-warn">Remove resume history</button>)}</Group>
      <Group title="Account"><p className="text-sm text-muted">Signed in as {data.account.username ?? data.user.name}{data.account.email ? ` (${data.account.email})` : ''}</p><form onSubmit={password} className="space-y-3"><Text label="Username for password sign-in" name="username" value={data.account.username} maxLength={50} />{data.account.has_password && <Text label="Current password" name="current_password" type="password" />}<label className="block text-sm text-muted">New password<input name="new_password" type="password" required minLength={12} maxLength={128} autoComplete="new-password" className={field} /></label><label className="block text-sm text-muted">Confirm new password<input name="confirm_password" type="password" required minLength={12} autoComplete="new-password" className={field} /></label><button disabled={busy} className={button}>{data.account.has_password ? 'Change password' : 'Set password'}</button></form><div className="space-y-3 border-t border-edge pt-4">{(['github', 'google'] as const).map(provider => <div key={provider} className="flex items-center justify-between gap-3 text-sm"><span className="capitalize">{provider} {data.account[`${provider}_connected`] ? 'connected' : 'not connected'}</span>{data.account[`${provider}_connected`] ? <button disabled={busy} onClick={() => void run(() => api(`/me/connections/${provider}`, { method: 'DELETE' }), `${provider} disconnected.`)} className="text-warn">Disconnect</button> : data.account[`${provider}_available`] ? <a href={`/api/auth/${provider}/login`} className="text-accent hover:underline">Connect {provider}</a> : <span className="text-xs text-muted">Not configured on this server</span>}</div>)}</div></Group>
    </div>
  </section>
}

export default function ProfileSettings({ onClose }: { onClose: () => void }) {
  const settings = useQuery({ queryKey: ['profile-settings'], queryFn: () => api<SettingsData>('/me/settings') })
  if (settings.isPending) return <p role="status" className="p-5">Loading settings...</p>
  if (settings.isError) return <div role="alert" className="p-5">Could not load settings. <button onClick={() => void settings.refetch()} className="text-accent">Retry</button><button onClick={onClose} className="ml-4">Close</button></div>
  return <SettingsForm data={settings.data} onClose={onClose} />
}
