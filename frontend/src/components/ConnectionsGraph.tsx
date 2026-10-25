import type { User } from '../lib/types'
import { useGraphGestures } from '../lib/useGraphGestures'

const roles = { student: { label: 'Student', color: '#60a5fa' }, mentor: { label: 'Mentor', color: '#c4a0ff' }, faculty: { label: 'Faculty', color: '#fbbf24' } }

function Marker({ role, x, y }: { role: string; x: number; y: number }) {
  const color = roles[role as keyof typeof roles]?.color ?? roles.student.color
  if (role === 'mentor') return <path d={`M${x} ${y - 14}l14 14 -14 14 -14 -14Z`} fill="var(--color-card)" stroke={color} strokeWidth={2.5} />
  if (role === 'faculty') return <rect x={x - 11} y={y - 11} width={22} height={22} rx={3} fill="var(--color-card)" stroke={color} strokeWidth={2.5} />
  return <circle cx={x} cy={y} r={12} fill="var(--color-card)" stroke={color} strokeWidth={2.5} />
}

export default function ConnectionsGraph({ users }: { users: User[] }) {
  const { ref, camera } = useGraphGestures(true)
  // Concentric rings allocate a fixed arc per node, keeping every connection distinct.
  let offset = 0
  let ring = 1
  const placed: { user: User; x: number; y: number }[] = []
  while (offset < users.length) {
    const radius = ring * 120
    const count = Math.min(users.length - offset, Math.floor(2 * Math.PI * radius / 65))
    for (let index = 0; index < count; index++) {
      const angle = index / count * 2 * Math.PI - Math.PI / 2 + (ring % 2 ? 0 : .15)
      placed.push({ user: users[offset + index], x: Math.cos(angle) * radius, y: Math.sin(angle) * radius })
    }
    offset += count
    ring++
  }
  const extent = Math.max(180, (ring - 1) * 120 + 40)
  const size = extent * 2
  return <div className="min-w-0 rounded-2xl border border-edge bg-card p-4">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold">Your connections graph</h2><span className="text-xs text-muted">Accepted connections only</span></div>
    <svg ref={ref} viewBox={`${-extent} ${-extent} ${size} ${size}`} className="mx-auto h-[320px] w-full touch-none sm:h-[380px]" aria-label={`Connections graph with ${users.length} connections. Circles are students, diamonds are mentors, squares are faculty.`}>
      <g transform={`translate(${camera.x * size} ${camera.y * size}) translate(${-extent} ${-extent}) scale(${camera.scale}) translate(${extent} ${extent})`}>
        {Array.from({ length: ring - 1 }, (_, index) => <circle key={index} r={(index + 1) * 120} fill="none" stroke="var(--color-edge)" strokeDasharray="2 8" />)}
        {placed.map(({ user, x, y }) => <line key={user.id} x1={0} y1={0} x2={x} y2={y} stroke="var(--color-muted)" strokeOpacity={.25} />)}
        <circle r={32} fill="var(--color-accent-soft)" stroke="var(--color-accent)" strokeWidth={2} /><text textAnchor="middle" y={5} fill="var(--color-ink)" fontSize={14}>You</text>
        {placed.map(({ user, x, y }, index) => <a key={user.id} data-role={user.role} href={`/u/${user.id}`} aria-label={`Open ${roles[user.role as keyof typeof roles]?.label ?? 'student'} connection ${index + 1} profile`} className="outline-none focus-visible:[&>circle]:stroke-white focus-visible:[&>rect]:stroke-white focus-visible:[&>path]:stroke-white"><title>{roles[user.role as keyof typeof roles]?.label ?? 'Student'} connection</title><circle cx={x} cy={y} r={23} fill="transparent" /><Marker role={user.role} x={x} y={y} /></a>)}
      </g>
    </svg>
    <div className="flex flex-wrap justify-center gap-5 text-xs text-muted">{Object.entries(roles).map(([role, { label }]) => <span key={role} className="inline-flex items-center gap-2"><svg width={22} height={22} viewBox="-17 -17 34 34" aria-hidden="true"><Marker role={role} x={0} y={0} /></svg>{label}</span>)}</div>
    <p className="mt-3 text-center text-xs text-muted">Select a node to open a profile. Scroll or pinch to zoom; double-click to reset.</p>
  </div>
}
