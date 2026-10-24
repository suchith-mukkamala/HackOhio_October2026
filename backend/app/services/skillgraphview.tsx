import { useMemo, useState } from 'react'
import type { CSSProperties, KeyboardEvent } from 'react'
import type { SkillGraph, SkillNode } from '../lib/types'
import './SkillGraphView.css'

const SIZE = 800
const C = SIZE / 2
const RING = [0, 110, 200, 280, 350] // radius by depth; depth 1 = top-level categories
const PULSE_AT = 0.6 // nodes at or above this pulse value animate

interface Placed {
  node: SkillNode
  x: number
  y: number
  r: number
  hasHidden: boolean
}

interface Layout {
  placed: Placed[]
  treeLinks: [string, string | null][] // [child, parent]; parent null = joins the center
}

function layout(nodes: SkillNode[], isOpen: (skill: string) => boolean): Layout {
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

  const visibleKids = (n: SkillNode) => (isOpen(n.skill) ? (kids.get(n.skill) ?? []) : [])
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
      hasHidden: (kids.get(n.skill)?.length ?? 0) > 0 && !isOpen(n.skill),
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
  return { placed, treeLinks }
}

interface Props {
  graph: SkillGraph
  name?: string // shown in the center
}

export default function SkillGraphView({ graph, name }: Props) {
  // Categories start open; clicking a node flips it from its default.
  const [flipped, setFlipped] = useState<Set<string>>(new Set())
  const [selected, setSelected] = useState<string | null>(null)

  const isOpen = (skill: string) => {
    const node = graph.nodes.find((n) => n.skill === skill)
    const byDefault = node?.tier === 'category'
    return flipped.has(skill) ? !byDefault : byDefault
  }

  const { placed, treeLinks } = useMemo(
    () => layout(graph.nodes, isOpen),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [graph.nodes, flipped],
  )

  const pos = new Map(placed.map((p) => [p.node.skill, p]))
  const sel = selected ? graph.nodes.find((n) => n.skill === selected) : undefined
  const hasChildren = (skill: string) => graph.nodes.some((n) => n.parent === skill)

  const onNodeClick = (skill: string) => {
    setSelected(skill)
    if (hasChildren(skill)) {
      setFlipped((prev) => {
        const next = new Set(prev)
        if (next.has(skill)) next.delete(skill)
        else next.add(skill)
        return next
      })
    }
  }

  if (graph.nodes.length === 0) {
    return <p className="sg-empty">No skills yet. Pick a few or push a project to grow your graph.</p>
  }

  return (
    <div className="skillgraph">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label={`Skill graph${name ? ` for ${name}` : ''}`}>
        {/* tree lines */}
        {treeLinks.map(([child, parent]) => {
          const a = pos.get(child)
          if (!a) return null
          const bx = parent ? (pos.get(parent)?.x ?? C) : C
          const by = parent ? (pos.get(parent)?.y ?? C) : C
          return <line key={`t-${child}`} className="sg-tree" x1={bx} y1={by} x2={a.x} y2={a.y} />
        })}

        {/* skills used together on a project */}
        {graph.edges.map((e) => {
          const a = pos.get(e.a)
          const b = pos.get(e.b)
          if (!a || !b) return null
          return (
            <line
              key={`e-${e.a}-${e.b}`}
              className="sg-co"
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              strokeWidth={1 + Math.min(e.weight, 4)}
            />
          )
        })}

        <g className="sg-center">
          <circle cx={C} cy={C} r={34} />
          <text x={C} y={C} dy="0.35em" textAnchor="middle">
            {(name ?? 'You').split(' ')[0]}
