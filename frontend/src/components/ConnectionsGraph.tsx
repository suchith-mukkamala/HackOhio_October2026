import { useEffect, useId, useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import type { User } from '../lib/types'

const roles = { student: { label: 'Student', color: '#60a5fa' }, mentor: { label: 'Mentor', color: '#c4a0ff' }, faculty: { label: 'Faculty', color: '#fbbf24' } }
const initialRotation = { yaw: .25, pitch: -.15 }
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5))

function Marker({ role, x, y }: { role: string; x: number; y: number }) {
  const color = roles[role as keyof typeof roles]?.color ?? roles.student.color
  if (role === 'mentor') return <path d={`M${x} ${y - 14}l14 14 -14 14 -14 -14Z`} fill="var(--color-card)" stroke={color} strokeWidth={2.5} />
  if (role === 'faculty') return <rect x={x - 11} y={y - 11} width={22} height={22} rx={3} fill="var(--color-card)" stroke={color} strokeWidth={2.5} />
  return <circle cx={x} cy={y} r={12} fill="var(--color-card)" stroke={color} strokeWidth={2.5} />
}

export default function ConnectionsGraph({ users, interconnections = [] }: { users: User[]; interconnections?: { source: number; target: number }[] }) {
  const [rotation, setRotation] = useState(initialRotation)
  const drag = useRef<{ id: number; x: number; y: number; distance: number } | null>(null)
  const dragged = useRef(false)
  const svgRef = useRef<SVGSVGElement>(null)
  const hovered = useRef(false)
  const focused = useRef(false)
  const glowId = useId()
  useEffect(() => {
    if (!users.length) return
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
    let frame = 0
    let previous = 0
    let visible = true
    const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting })
    if (svgRef.current) observer.observe(svgRef.current)
    const tick = (time: number) => {
      frame = requestAnimationFrame(tick)
      if (previous && time - previous < 32) return
      const elapsed = previous ? Math.min(time - previous, 64) : 0
      previous = time
      if (document.hidden || !visible || hovered.current || focused.current || drag.current) return
      // About one revolution every two minutes, independent of display refresh rate.
      setRotation(value => ({ ...value, yaw: (value.yaw + elapsed * 0.0003) % (Math.PI * 2) }))
    }
    const syncMotion = () => {
      cancelAnimationFrame(frame)
      previous = 0
      if (!motion.matches) frame = requestAnimationFrame(tick)
    }
    motion.addEventListener('change', syncMotion)
    syncMotion()
    return () => {
      cancelAnimationFrame(frame)
      observer.disconnect()
      motion.removeEventListener('change', syncMotion)
    }
  }, [users.length])
  function startDrag(event: PointerEvent<SVGSVGElement>) {
    if (event.button !== 0 || drag.current) return
    dragged.current = false
    drag.current = { id: event.pointerId, x: event.clientX, y: event.clientY, distance: 0 }
  }
  function rotate(event: PointerEvent<SVGSVGElement>) {
    const previous = drag.current
    if (!previous || previous.id !== event.pointerId) return
    const dx = event.clientX - previous.x
    const dy = event.clientY - previous.y
    previous.distance += Math.hypot(dx, dy)
    previous.x = event.clientX
    previous.y = event.clientY
    if (previous.distance < 5) return
    dragged.current = true
    event.currentTarget.setPointerCapture(event.pointerId)
    setRotation(value => ({ yaw: value.yaw + dx * .008, pitch: value.pitch - dy * .008 }))
  }
  function stopDrag(event: PointerEvent<SVGSVGElement>) {
    if (drag.current?.id !== event.pointerId) return
    drag.current = null
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
  }
  function project(x: number, y: number, z: number) {
    const rx = x * Math.cos(rotation.yaw) + z * Math.sin(rotation.yaw)
    const rz = -x * Math.sin(rotation.yaw) + z * Math.cos(rotation.yaw)
    const ry = y * Math.cos(rotation.pitch) - rz * Math.sin(rotation.pitch)
    const depth = y * Math.sin(rotation.pitch) + rz * Math.cos(rotation.pitch)
    const scale = 600 / (600 - depth)
    return { x: rx * scale, y: ry * scale, depth, scale }
  }
  // A Fibonacci sphere gives each connection a real 3D position around the origin.
  const placed = users.map((user, index) => {
    const y = users.length === 1 ? 0 : 1 - 2 * (index + .5) / users.length
    const radius = Math.sqrt(1 - y * y)
    const angle = index * GOLDEN_ANGLE
    return { user, index, ...project(145 * Math.cos(angle) * radius, 145 * y, 145 * Math.sin(angle) * radius) }
  }).sort((a, b) => a.depth - b.depth)
  const byId = new Map(placed.map(node => [node.user.id, node]))
  const orbit = (axis: number) => Array.from({ length: 65 }, (_, index) => {
    const angle = index / 64 * 2 * Math.PI
    const a = 145 * Math.cos(angle), b = 145 * Math.sin(angle)
    const point = axis === 0 ? project(a, b, 0) : axis === 1 ? project(a, 0, b) : project(0, a, b)
    return `${index ? 'L' : 'M'}${point.x},${point.y}`
  }).join(' ') + ' Z'
  const node = ({ user, x, y, depth, scale }: typeof placed[number]) => <a key={user.id} data-role={user.role} data-depth={depth.toFixed(2)} href={`/u/${user.id}`} aria-label={`Open ${user.name} profile`} className="outline-none focus-visible:[&_circle]:stroke-white focus-visible:[&_rect]:stroke-white focus-visible:[&_path]:stroke-white"><title>{user.name}</title><g transform={`translate(${x} ${y}) scale(${scale})`}><circle r={23} fill="transparent" /><Marker role={user.role} x={0} y={0} /></g></a>
  return <div className="min-w-0 rounded-2xl border border-edge bg-card p-4">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold">Your connections graph</h2><span className="text-xs text-muted">Accepted connections only</span></div>
    <svg ref={svgRef} onPointerEnter={() => { hovered.current = true }} onPointerLeave={() => { hovered.current = false }} onFocusCapture={() => { focused.current = true }} onBlurCapture={event => { if (!event.currentTarget.contains(event.relatedTarget)) focused.current = false }} viewBox="-210 -210 420 420" className="mx-auto h-[320px] w-full touch-pan-y select-none cursor-grab active:cursor-grabbing sm:h-[380px] focus-visible:outline-2 focus-visible:outline-accent" tabIndex={0} aria-label={`Connections graph with ${users.length} connections. Circles are students, diamonds are mentors, squares are faculty.`} aria-describedby="connections-rotate-help" onPointerDown={startDrag} onPointerMove={rotate} onPointerUp={stopDrag} onPointerCancel={stopDrag} onLostPointerCapture={() => { drag.current = null }} onClickCapture={event => { if (dragged.current && event.detail !== 0) { event.preventDefault(); event.stopPropagation(); dragged.current = false } }} onDoubleClick={() => setRotation(initialRotation)} onKeyDown={event => {
      if (event.target !== event.currentTarget) return
      if (event.key === 'Home') { event.preventDefault(); setRotation(initialRotation); return }
      if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return
      event.preventDefault()
      setRotation(value => ({ yaw: value.yaw + (event.key === 'ArrowLeft' ? -.12 : event.key === 'ArrowRight' ? .12 : 0), pitch: value.pitch + (event.key === 'ArrowUp' ? .12 : event.key === 'ArrowDown' ? -.12 : 0) }))
    }}>
      <defs><radialGradient id={glowId}><stop stopColor="var(--color-accent)" stopOpacity=".09" /><stop offset="1" stopColor="var(--color-accent)" stopOpacity="0" /></radialGradient></defs>
      <circle r={195} fill={`url(#${glowId})`} pointerEvents="none" />
      <g fill="none" stroke="var(--color-muted)" strokeOpacity={.1} pointerEvents="none">{[0, 1, 2].map(axis => <path key={axis} d={orbit(axis)} />)}</g>
      <g aria-hidden="true" data-interconnections="true" stroke="var(--color-accent)" strokeOpacity={.13} strokeWidth={1} pointerEvents="none">
        {interconnections.map(({ source, target }) => {
          const from = byId.get(source), to = byId.get(target)
          return from && to ? <line key={`${source}-${target}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} /> : null
        })}
      </g>
      {placed.map(({ user, x, y }) => <line key={user.id} x1={0} y1={0} x2={x} y2={y} stroke="var(--color-muted)" strokeOpacity={.25} pointerEvents="none" />)}
      {placed.filter(point => point.depth < 0).map(node)}
      <g data-graph-center="true" pointerEvents="none"><circle r={32} fill="var(--color-accent-soft)" stroke="var(--color-accent)" strokeWidth={2} /><text textAnchor="middle" y={5} fill="var(--color-ink)" fontSize={14}>You</text></g>
      {placed.filter(point => point.depth >= 0).map(node)}
    </svg>
    <div className="flex flex-wrap justify-center gap-5 text-xs text-muted">{Object.entries(roles).map(([role, { label }]) => <span key={role} className="inline-flex items-center gap-2"><svg width={22} height={22} viewBox="-17 -17 34 34" aria-hidden="true"><Marker role={role} x={0} y={0} /></svg>{label}</span>)}</div>
    <p className="mt-3 text-center text-xs text-muted">Gray lines connect to you; faint blue lines connect people in your network.</p>
    <p id="connections-rotate-help" className="mt-1 text-center text-xs text-muted">Drag to spin around You. Use arrow keys when focused; double-click or press Home to reset. Select a node to open its profile.</p>
  </div>
}
