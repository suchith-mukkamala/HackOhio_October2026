import { useEffect, useRef, useState } from 'react'

const initial = { scale: 1, x: 0, y: 0 }
export function useGraphGestures(enabled: boolean) {
  const ref = useRef<SVGSVGElement>(null)
  const [camera, setCamera] = useState(initial)

  useEffect(() => {
    const svg = ref.current
    if (!svg || !enabled) return
    const pointers = new Map<number, { x: number; y: number }>()
    let moved = false
    let distanceTravelled = 0
    const point = (x: number, y: number) => {
      const rect = svg.getBoundingClientRect()
      return { x: (x - rect.left) / rect.width, y: (y - rect.top) / rect.height }
    }
    const zoom = (factor: number, anchor: { x: number; y: number }, dx = 0, dy = 0) => {
      setCamera(previous => {
        const scale = Math.max(1, Math.min(8, previous.scale * factor))
        if (scale === 1) return initial
        const ratio = scale / previous.scale
        return { scale, x: anchor.x - (anchor.x - previous.x) * ratio + dx, y: anchor.y - (anchor.y - previous.y) * ratio + dy }
      })
    }
    const wheel = (event: WheelEvent) => {
      event.preventDefault()
      const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? svg.clientHeight : 1)
      zoom(Math.exp(-Math.max(-100, Math.min(100, delta)) * (event.ctrlKey ? 0.015 : 0.003)), point(event.clientX, event.clientY))
    }
    const down = (event: PointerEvent) => {
      if (event.button !== 0) return
      if (!pointers.size) { moved = false; distanceTravelled = 0 }
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY })
    }
    const move = (event: PointerEvent) => {
      const old = pointers.get(event.pointerId)
      if (!old) return
      const before = [...pointers.values()]
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY })
      const after = [...pointers.values()]
      distanceTravelled += Math.hypot(event.clientX - old.x, event.clientY - old.y)
      if (distanceTravelled < 4 && pointers.size === 1) return
      moved = true
      svg.setPointerCapture(event.pointerId)
      const rect = svg.getBoundingClientRect()
      if (after.length >= 2) {
        const oldDistance = Math.hypot(before[0].x - before[1].x, before[0].y - before[1].y)
        const newDistance = Math.hypot(after[0].x - after[1].x, after[0].y - after[1].y)
        const anchor = point((before[0].x + before[1].x) / 2, (before[0].y + before[1].y) / 2)
        zoom(oldDistance > 0 ? newDistance / oldDistance : 1, anchor,
          ((after[0].x + after[1].x) - (before[0].x + before[1].x)) / 2 / rect.width,
          ((after[0].y + after[1].y) - (before[0].y + before[1].y)) / 2 / rect.height)
      } else {
        setCamera(previous => previous.scale === 1 ? previous : { ...previous, x: previous.x + (event.clientX - old.x) / rect.width, y: previous.y + (event.clientY - old.y) / rect.height })
      }
    }
    const up = (event: PointerEvent) => {
      pointers.delete(event.pointerId)
      if (svg.hasPointerCapture(event.pointerId)) svg.releasePointerCapture(event.pointerId)
    }
    const click = (event: MouseEvent) => {
      if (moved && event.detail !== 0) { event.preventDefault(); event.stopPropagation(); moved = false }
    }
    const reset = (event: MouseEvent) => { event.preventDefault(); setCamera(initial) }
    svg.addEventListener('wheel', wheel, { passive: false })
    svg.addEventListener('pointerdown', down)
    svg.addEventListener('pointermove', move)
    svg.addEventListener('pointerup', up)
    svg.addEventListener('pointercancel', up)
    svg.addEventListener('lostpointercapture', up)
    svg.addEventListener('click', click, true)
    svg.addEventListener('dblclick', reset)
    return () => {
      svg.removeEventListener('wheel', wheel)
      svg.removeEventListener('pointerdown', down)
      svg.removeEventListener('pointermove', move)
      svg.removeEventListener('pointerup', up)
      svg.removeEventListener('pointercancel', up)
      svg.removeEventListener('lostpointercapture', up)
      svg.removeEventListener('click', click, true)
      svg.removeEventListener('dblclick', reset)
    }
  }, [enabled])

  return { ref, camera }
}
