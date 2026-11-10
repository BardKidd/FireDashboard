import type { Theme } from './api'

/** Level-unlocked accent themes override the Tailwind theme variables at runtime. */
export function applyTheme(themes: Theme[], key: string) {
  const t = themes.find((x) => x.key === key && x.unlocked) ?? themes[0]
  if (!t) return
  const root = document.documentElement.style
  root.setProperty('--color-accent', t.accent)
  root.setProperty('--color-accent-soft', t.soft)
}

export function accentColor(): string {
  return getComputedStyle(document.documentElement).getPropertyValue('--color-accent').trim() || '#f59e4b'
}
