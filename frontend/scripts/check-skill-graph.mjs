import assert from 'node:assert/strict'
import { spaceGraph, graphBounds } from '../src/lib/skillGraphLayout.ts'
const points = []
for (let ring = 1; ring <= 4; ring++) {
  for (let i = 0; i < 40; i++) {
    const angle = i * 2 * Math.PI / 40
    points.push({ x: 400 + ring * 90 * Math.cos(angle), y: 400 + ring * 90 * Math.sin(angle), r: 22, node: { skill: `Long skill label ${ring}-${i}` } })
  }
}
const { placed, bounds } = spaceGraph(points, 400)
assert.equal(placed.length, points.length)
const boxes = placed.map(point => graphBounds(point, 400))
for (let i = 0; i < boxes.length; i++) {
  const a = boxes[i]
  assert.ok(a.left >= bounds.x && a.right <= bounds.x + bounds.width)
  assert.ok(a.top >= bounds.y && a.bottom <= bounds.y + bounds.height)
  for (let j = i + 1; j < boxes.length; j++) {
    const b = boxes[j]
    assert.ok(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top, `Overlap: ${i}, ${j}`)
  }
}
for (const count of [1, 2, 12, 48]) {
  const result = spaceGraph(points.slice(0, count), 400)
  assert.ok(Number.isFinite(result.bounds.width) && Number.isFinite(result.bounds.height))
}
console.log('Graph layout checks passed: 160 nodes, long labels, no overlapping bounds, no clipping.')

// A local collision must not push an unrelated node farther from the center.
const local = [
  { x: 540, y: 400, r: 18, node: { skill: 'Python' } },
  { x: 542, y: 402, r: 18, node: { skill: 'FastAPI' } },
  { x: 100, y: 100, r: 18, node: { skill: 'CAD' } },
]
const compact = spaceGraph(local, 400)
assert.equal(compact.placed[2].x, local[2].x)
assert.equal(compact.placed[2].y, local[2].y)
assert.ok(compact.bounds.width < 800 && compact.bounds.height < 800)
assert.deepEqual(spaceGraph(local, 400), compact)
