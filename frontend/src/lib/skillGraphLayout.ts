// Place each node near its radial position, moving only nodes that collide.
export type GraphPoint = { x: number; y: number; r: number; node: { skill: string } }
export const labelWidth = (skill: string) => Array.from(skill).length * 9
export function graphBounds(point: GraphPoint, center: number) {
  const halo = point.r * 1.9 + 3
  const right = point.x >= center
  const label = Math.max(halo, point.r + 8 + labelWidth(point.node.skill))
  return { left: point.x - (right ? halo : label), right: point.x + (right ? label : halo), top: point.y - halo, bottom: point.y + halo }
}

export function spaceGraph<T extends GraphPoint>(points: T[], center: number) {
  const gap = 6
  const occupied = [{ left: center - 48, right: center + 48, top: center - 48, bottom: center + 48 }]
  const placedByIndex = new Map<number, T>()
  // Settle the inner branches first; leaves pack around them without enlarging every ring.
  const ordered = points.map((point, index) => ({ point, index }))
    .sort((a, b) => Math.hypot(a.point.x - center, a.point.y - center) - Math.hypot(b.point.x - center, b.point.y - center) || a.index - b.index)
  for (const { point, index } of ordered) {
    const initial = graphBounds(point, center)
    const left = point.x - initial.left, right = initial.right - point.x
    const top = point.y - initial.top, bottom = initial.bottom - point.y
    const candidates = [{ x: point.x, y: point.y }]
    for (const box of occupied) {
      const xs = [box.left - right - gap, box.right + left + gap]
      const ys = [box.top - bottom - gap, box.bottom + top + gap]
      for (const x of xs) {
        candidates.push({ x, y: point.y })
        for (const y of ys) candidates.push({ x, y })
      }
      for (const y of ys) candidates.push({ x: point.x, y })
    }
    candidates.sort((a, b) => (a.x - point.x) ** 2 + (a.y - point.y) ** 2 - ((b.x - point.x) ** 2 + (b.y - point.y) ** 2))
    const position = candidates.find(candidate => {
      // Keep labels facing the same direction as in the radial tree.
      if ((candidate.x >= center) !== (point.x >= center)) return false
      const box = graphBounds({ ...point, ...candidate }, center)
      return occupied.every(other => box.right + gap <= other.left || other.right + gap <= box.left || box.bottom + gap <= other.top || other.bottom + gap <= box.top)
    })!
    const placed = { ...point, ...position }
    placedByIndex.set(index, placed)
    occupied.push(graphBounds(placed, center))
  }
  const placed = points.map((_, index) => placedByIndex.get(index)!)
  const x = Math.min(...occupied.map(box => box.left)) - 16
  const y = Math.min(...occupied.map(box => box.top)) - 16
  return { placed, bounds: { x, y, width: Math.max(...occupied.map(box => box.right)) + 16 - x, height: Math.max(...occupied.map(box => box.bottom)) + 16 - y } }
}
