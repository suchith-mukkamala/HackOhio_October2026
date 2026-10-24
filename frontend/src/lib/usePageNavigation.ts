import type { MouseEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

let pendingExit: Animation | null = null

// Animate the actual page so the effect works consistently across browsers.
export function usePageNavigation() {
  const navigate = useNavigate()
  const location = useLocation()
  function go(to: string) {
    pendingExit?.cancel()
    pendingExit = null
    const next = new URL(to, window.location.href)
    const changePage = next.pathname !== location.pathname
    const update = () => {
      navigate(to)
      if (changePage) window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
    }
    const content = document.querySelector<HTMLElement>('main.page-content')
    if (!changePage || window.matchMedia('(prefers-reduced-motion: reduce)').matches || !content?.animate) {
      update()
      return
    }
    const exit = content.animate([
      { opacity: 1, transform: 'translateY(0)' },
      { opacity: 0, transform: 'translateY(-12px)' },
    ], { duration: 130, easing: 'ease-in', fill: 'forwards' })
    pendingExit = exit
    void exit.finished.then(() => {
      if (pendingExit !== exit) return
      pendingExit = null
      update()
    }, () => { /* A newer tab click superseded this navigation. */ })
  }
  function onLinkClick(event: MouseEvent<HTMLAnchorElement>, to: string) {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.currentTarget.target === '_blank') return
    event.preventDefault()
    go(to)
  }
  return { go, onLinkClick }
}
