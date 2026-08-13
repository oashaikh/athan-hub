import { gsap } from 'gsap'

const reducedMotionQuery = '(prefers-reduced-motion: reduce)'

export const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia(reducedMotionQuery).matches

const completeImmediately = (element: Element, done?: () => void) => {
  gsap.set(element, { clearProps: 'all' })
  done?.()
}

export const enterRoute = (element: Element, done: () => void) => {
  if (prefersReducedMotion()) return completeImmediately(element, done)
  gsap.fromTo(
    element,
    { autoAlpha: 0, y: 10 },
    {
      autoAlpha: 1,
      y: 0,
      duration: 0.34,
      ease: 'power3.out',
      clearProps: 'opacity,transform,visibility',
      onComplete: done
    }
  )
}

export const leaveRoute = (element: Element, done: () => void) => {
  if (prefersReducedMotion()) return completeImmediately(element, done)
  gsap.to(element, {
    autoAlpha: 0,
    y: -5,
    duration: 0.16,
    ease: 'power2.in',
    onComplete: done
  })
}

export const enterMenu = (element: Element, done: () => void) => {
  if (prefersReducedMotion()) return completeImmediately(element, done)
  const panel = element.querySelector('.menu-panel')
  const scrim = element.querySelector('.menu-scrim')
  gsap.timeline({ onComplete: done })
    .fromTo(scrim, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.16, ease: 'power1.out' }, 0)
    .fromTo(
      panel,
      { autoAlpha: 0, y: -10, scale: 0.97, transformOrigin: 'top right' },
      { autoAlpha: 1, y: 0, scale: 1, duration: 0.28, ease: 'power3.out' },
      0.02
    )
    .fromTo(
      element.querySelectorAll('.menu-link'),
      { autoAlpha: 0, x: 8 },
      { autoAlpha: 1, x: 0, duration: 0.2, stagger: 0.025, ease: 'power2.out' },
      0.08
    )
}

export const leaveMenu = (element: Element, done: () => void) => {
  if (prefersReducedMotion()) return completeImmediately(element, done)
  gsap.timeline({ onComplete: done })
    .to(element.querySelector('.menu-panel'), { autoAlpha: 0, y: -6, scale: 0.98, duration: 0.14, ease: 'power2.in' }, 0)
    .to(element.querySelector('.menu-scrim'), { autoAlpha: 0, duration: 0.13, ease: 'power1.in' }, 0)
}

export const animateDashboardEntrance = (scope: Element) => {
  if (prefersReducedMotion()) return null
  return gsap.context(() => {
    gsap.timeline({ defaults: { ease: 'power3.out' } })
      .from('[data-reveal="hero-copy"]', { autoAlpha: 0, y: 18, duration: 0.46 })
      .from('[data-reveal="hero-time"]', { autoAlpha: 0, y: 16, scale: 0.985, duration: 0.42 }, '-=0.3')
      .from('.prayer-card', { autoAlpha: 0, y: 14, duration: 0.32, stagger: 0.045 }, '-=0.2')
      .from('[data-reveal="footer"]', { autoAlpha: 0, duration: 0.24 }, '-=0.12')
  }, scope)
}

export const animatePrayerState = (scope: Element, prayerKey: string) => {
  if (prefersReducedMotion()) return
  const activeCard = scope.querySelector(`[data-prayer="${prayerKey}"]`)
  const orb = scope.querySelector('.ambient-orb')
  if (orb) {
    gsap.fromTo(orb, { scale: 0.96, autoAlpha: 0.65 }, { scale: 1, autoAlpha: 1, duration: 0.7, ease: 'power2.out' })
  }
  if (activeCard) {
    gsap.fromTo(activeCard, { y: 2 }, { y: 0, duration: 0.38, ease: 'power3.out', clearProps: 'transform' })
  }
}

export const animateCounter = (element: Element | null) => {
  if (!element || prefersReducedMotion()) return
  gsap.fromTo(element, { autoAlpha: 0.72, y: 3 }, { autoAlpha: 1, y: 0, duration: 0.2, ease: 'power2.out', clearProps: 'opacity,transform,visibility' })
}

export const enterPane = (element: Element, done: () => void) => {
  if (prefersReducedMotion()) return completeImmediately(element, done)
  gsap.fromTo(
    element,
    { autoAlpha: 0, y: 12 },
    { autoAlpha: 1, y: 0, duration: 0.32, ease: 'power3.out', clearProps: 'opacity,transform,visibility', onComplete: done }
  )
}

export const leavePane = (element: Element, done: () => void) => {
  if (prefersReducedMotion()) return completeImmediately(element, done)
  gsap.to(element, { autoAlpha: 0, y: -4, duration: 0.13, ease: 'power1.in', onComplete: done })
}

export const enterToast = (element: Element, done: () => void) => {
  if (prefersReducedMotion()) return completeImmediately(element, done)
  gsap.fromTo(element, { autoAlpha: 0, x: 18, scale: 0.98 }, { autoAlpha: 1, x: 0, scale: 1, duration: 0.26, ease: 'power3.out', onComplete: done })
}

export const leaveToast = (element: Element, done: () => void) => {
  if (prefersReducedMotion()) return completeImmediately(element, done)
  gsap.to(element, { autoAlpha: 0, x: 12, duration: 0.14, ease: 'power1.in', onComplete: done })
}
