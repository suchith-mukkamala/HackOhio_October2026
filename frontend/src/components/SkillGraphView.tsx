import { useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties, KeyboardEvent } from 'react'
import type { SkillGraph, SkillNode } from '../lib/types'
import './SkillGraphView.css'
import { useGraphGestures } from '../lib/useGraphGestures'
import { spaceGraph } from '../lib/skillGraphLayout'

const SIZE = 800
const C = SIZE / 2
const RING = [0, 110, 200, 280, 350] // radius by depth; depth 1 = top-level categories
const PULSE_AT = 0.6 // nodes at or above this pulse value animate

function growthProgress(time: number): number {
  const acceleration = .04
  const deceleration = .15
  const distance = 1 - (acceleration + deceleration) / 2
  // Reach cruising speed quickly; retain the longer, gentle slowdown at the end.
  if (time < acceleration) return (time - acceleration / Math.PI * Math.sin(Math.PI * time / acceleration)) / (2 * distance)
  if (time > 1 - deceleration) {
    const remaining = 1 - time
    return 1 - (remaining - deceleration / Math.PI * Math.sin(Math.PI * remaining / deceleration)) / (2 * distance)
  }
  return (time - acceleration / 2) / distance
}

interface Placed {
  node: SkillNode
  x: number
  y: number
  r: number
}

interface Layout {
  bounds: { x: number; y: number; width: number; height: number }
  placed: Placed[]
  treeLinks: [string, string | null][] // [child, parent]; parent null = joins the center
}

function layout(nodes: SkillNode[]): Layout {
  const byName = new Map(nodes.map((n) => [n.skill, n]))
  const kids = new Map<string, SkillNode[]>()
  const roots: SkillNode[] = []
  for (const n of nodes) {
    if (n.parent && byName.has(n.parent)) {
      const list = kids.get(n.parent) ?? []
      list.push(n)
      kids.set(n.parent, list)
    } else {
      roots.push(n)
    }
  }

  const visibleKids = (n: SkillNode) => kids.get(n.skill) ?? []
  const leaves = (n: SkillNode): number => {
    const k = visibleKids(n)
    return k.length ? k.reduce((s, c) => s + leaves(c), 0) : 1
  }

  const placed: Placed[] = []
  const treeLinks: [string, string | null][] = []

  const place = (n: SkillNode, a0: number, a1: number, depth: number, parent: string | null) => {
    const angle = (a0 + a1) / 2 - Math.PI / 2 // start at the top
    const ring = RING[Math.min(depth, RING.length - 1)]
    const isCategory = n.tier === 'category'
    const r = isCategory ? 14 + n.pulse * 8 : 7 + n.pulse * 13
    placed.push({
      node: n,
      x: C + ring * Math.cos(angle),
      y: C + ring * Math.sin(angle),
      r,
    })
    treeLinks.push([n.skill, parent])

    const k = visibleKids(n)
    const total = k.reduce((s, c) => s + leaves(c), 0)
    let cur = a0
    for (const c of k) {
      const span = ((a1 - a0) * leaves(c)) / total
      place(c, cur, cur + span, depth + 1, n.skill)
      cur += span
    }
  }

  const total = roots.reduce((s, r) => s + leaves(r), 0) || 1
  let cur = 0
  for (const root of roots) {
    const span = (2 * Math.PI * leaves(root)) / total
    place(root, cur, cur + span, 1, null)
    cur += span
  }
  return { ...spaceGraph(placed, C), treeLinks }
}

function FlowParticle({ path, color, duration, delay, scale }: { path: string; color: 'blue' | 'yellow'; duration: number; delay: number; scale: number }) {
  return <g className={`sg-flow sg-flow-${color}`} aria-hidden="true">
    <circle r={5 / scale} className="sg-flow-glow" />
    <circle r={2 / scale} />
    <animateMotion path={path} dur={`${duration}s`} begin={`-${delay}s`} repeatCount="indefinite" calcMode="paced" />
    <animate attributeName="opacity" values={color === 'yellow' ? '0;0.9;0.9;0' : '0;0.22;0.22;0'} keyTimes="0;0.12;0.88;1" dur={`${duration}s`} begin={`-${delay}s`} repeatCount="indefinite" />
  </g>
}

interface Props {
  graph: SkillGraph
  name?: string // shown in the center
  particles?: boolean
  reduceMotion?: boolean
  highlightedSkills?: string[]
}

export default function SkillGraphView({ graph, name, particles = true, reduceMotion = false, highlightedSkills = [] }: Props) {
  const [growth, setGrowth] = useState(() => reduceMotion || window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 1 : 0)
  const growthFinished = useRef(growth === 1)
  useEffect(() => {
    if (growthFinished.current) return
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
    let frame = 0
    let previous = 0
    const start = performance.now()
    const finish = () => {
      cancelAnimationFrame(frame)
      growthFinished.current = true
      setGrowth(1)
    }
    const tick = (time: number) => {
      const progress = Math.min(1, (time - start) / 6000)
      if (time - previous >= 32 || progress === 1) {
        setGrowth(growthProgress(progress))
        previous = time
      }
      if (progress < 1) frame = requestAnimationFrame(tick)
      else growthFinished.current = true
    }
    const onMotionChange = () => { if (motion.matches) finish() }
    if (reduceMotion || motion.matches) finish()
    else frame = requestAnimationFrame(tick)
    motion.addEventListener('change', onMotionChange)
    return () => { cancelAnimationFrame(frame); motion.removeEventListener('change', onMotionChange) }
  }, [reduceMotion])
  // Keep every branch fully extended; selecting a node opens its evidence.
  const { ref: gestureRef, camera } = useGraphGestures(graph.nodes.length > 0)
  const [selected, setSelected] = useState<string | null>(null)

  const nodeByName = useMemo(() => new Map(graph.nodes.map((n) => [n.skill, n])), [graph.nodes])

  const { placed: finalPlaced, treeLinks, bounds } = useMemo(() => layout(graph.nodes), [graph.nodes])
  // Every anchor moves together. Lines and particle routes use these same live positions.
  const placed = finalPlaced.map(point => ({ ...point, x: C + (point.x - C) * growth, y: C + (point.y - C) * growth }))

  // Keep the original 1020:800 display proportions while fitting every label.
  const displayWidth = Math.max(bounds.width, bounds.height * 1020 / 800)
  const displayHeight = displayWidth * 800 / 1020
  const viewX = bounds.x - (displayWidth - bounds.width) / 2
  const viewY = bounds.y - (displayHeight - bounds.height) / 2

  // Counteract camera zoom around each anchor so only the spacing changes.
  const fixedSizeAt = (x: number, y: number) => `translate(${x} ${y}) scale(${1 / camera.scale}) translate(${-x} ${-y})`

  const pos = new Map(placed.map((p) => [p.node.skill, p]))
  const sel = selected ? nodeByName.get(selected) : undefined
  const onNodeClick = (skill: string) => setSelected(skill)

  if (graph.nodes.length === 0) {
    return <p className="sg-empty">No skills yet. Pick a few or push a project to grow your graph.</p>
  }

  return (
    <div data-growth={growth.toFixed(4)} className={`skillgraph ${!particles ? 'sg-no-particles' : ''} ${reduceMotion ? 'sg-reduce-motion' : ''}`}>
      <svg
        ref={gestureRef}
        viewBox={`${viewX - camera.x * displayWidth / camera.scale} ${viewY - camera.y * displayHeight / camera.scale} ${displayWidth / camera.scale} ${displayHeight / camera.scale}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label={`Skill graph${name ? ` for ${name}` : ''}`}
      >
        {/* tree lines */}
        {treeLinks.map(([child, parent]) => {
          const a = pos.get(child)
          if (!a) return null
          const bx = parent ? (pos.get(parent)?.x ?? C) : C
          const by = parent ? (pos.get(parent)?.y ?? C) : C
          return <line key={`t-${child}`} className="sg-tree" x1={bx} y1={by} x2={a.x} y2={a.y} />
        })}

        {/* Subtle pathways between skills used together, with sparse blue flow. */}
        {graph.edges.map((edge, index) => {
          const a = pos.get(edge.a), b = pos.get(edge.b)
          if (!a || !b) return null
          const path = `M ${a.x} ${a.y} L ${b.x} ${b.y}`
          return <g key={`e-${edge.a}-${edge.b}`} className="sg-pathway" aria-hidden="true">
            <path d={path} className="sg-co" />
            {index % Math.max(1, Math.ceil(graph.edges.length / 60)) === 0 && <FlowParticle path={path} color="blue" duration={26 + index % 9} delay={(index * 7.31) % 29} scale={camera.scale} />}
          </g>
        })}

        {/* Each yellow particle follows a full route from the user to a leaf. */}
        {placed.filter(point => !treeLinks.some(([, parent]) => parent === point.node.skill)).map((leaf, index) => {
          const route = [leaf]
          const visited = new Set([leaf.node.skill])
          let parent = leaf.node.parent
          while (parent && pos.has(parent) && !visited.has(parent)) {
            visited.add(parent)
            const point = pos.get(parent)!
            route.unshift(point)
            parent = point.node.parent
          }
          const path = `M ${C} ${C} ${route.map(point => `L ${point.x} ${point.y}`).join(' ')}`
          return <FlowParticle key={`flow-${leaf.node.skill}`} path={path} color="yellow" duration={30 + index % 11} delay={(index * 9.17) % 37} scale={camera.scale} />
        })}

        {/* nodes */}
        {placed.map(({ node, x, y, r }) => {
          const pulsing = node.pulse >= PULSE_AT
          const cls = [
            'sg-node',
            `sg-${node.tier}`,
            pulsing ? 'sg-pulse' : '',
            selected === node.skill ? 'sg-selected' : '',
            highlightedSkills.includes(node.skill) ? 'sg-highlighted' : '',
          ]
            .filter(Boolean)
            .join(' ')
          // stronger pulse = shorter beat (about 3s down to 1.2s)
          const style = {
            '--dur': `${(3 - node.pulse * 1.8).toFixed(2)}s`,
            opacity: Math.min(1, growth * 5),
          } as CSSProperties
          const onKey = (e: KeyboardEvent<SVGGElement>) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              onNodeClick(node.skill)
            }
          }
          const right = x >= C
          return (
            <g key={node.skill} className="sg-sprout" style={style}>
            <g
              transform={fixedSizeAt(x, y)}
              className={cls}
              tabIndex={0}
              role="button"
              aria-label={`${node.skill}, ${node.tier}`}
              onClick={() => onNodeClick(node.skill)}
              onKeyDown={onKey}
            >
              <circle className="sg-node-background" cx={x} cy={y} r={r + 1} />
              <circle className="sg-halo" cx={x} cy={y} r={r * 1.3} />
              <circle className="sg-dot" cx={x} cy={y} r={r} />
              <text
                className="sg-label"
                style={{ opacity: Math.max(0, Math.min(1, (growth - .35) / .35)) }}
                x={x + (right ? r + 8 : -(r + 8))}
                y={y}
                dy="0.35em"
                textAnchor={right ? 'start' : 'end'}
              >
                {node.skill}
              </text>
            </g>
            </g>
          )
        })}
        <g className="sg-center" transform={fixedSizeAt(C, C)}>
          <circle cx={C} cy={C} r={34} />
          <text x={C} y={C} dy="0.35em" textAnchor="middle">
            {(name ?? 'You').split(' ')[0]}
          </text>
        </g>
      </svg>

      {sel && (
        <div className="sg-panel">
          <h4>{sel.skill}</h4>
          <p>
            <span className="sg-tier">{sel.tier}</span>
            {sel.tier !== 'category' && ` · strength ${Math.round(sel.pulse * 100)}%`}
          </p>
          {sel.evidence.length > 0 ? (
            <ul>
              {sel.evidence.map((ev, i) => (
                <li key={i}>
                  <span className="sg-tier">{ev.kind.replace('_', ' ')}</span>: {ev.label}
                </li>
              ))}
            </ul>
          ) : (
            <p>
              {sel.tier === 'derived'
                ? 'Shown because a skill under it is strong.'
                : 'Part of your fully expanded skill tree. No evidence of its own yet.'}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
