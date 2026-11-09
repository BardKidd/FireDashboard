const twd0 = new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 0 })

export function money(v: number | null | undefined, currency: 'TWD' | 'USD' = 'TWD'): string {
  if (v == null || Number.isNaN(v)) return '—'
  if (currency === 'USD') {
    return 'US$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  return 'NT$' + twd0.format(v)
}

/** 1,234,567 -> "123 萬"; >= 1 億 -> "1.23 億". */
export function wan(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return '—'
  const a = Math.abs(v)
  if (a >= 1e8) return (v / 1e8).toFixed(2) + ' 億'
  if (a >= 1e4) return (v / 1e4).toFixed(a >= 1e6 ? 0 : 1) + ' 萬'
  return twd0.format(v)
}

export function pct(v: number | null | undefined, digits = 1): string {
  if (v == null || Number.isNaN(v)) return '—'
  return (v * 100).toFixed(digits) + '%'
}

export function shares(v: number, market: string): string {
  if (market === 'CASH') return v.toLocaleString('en-US', { maximumFractionDigits: 2 })
  if (market === 'TW') {
    const lots = Math.floor(v / 1000)
    const odd = Math.round(v - lots * 1000)
    if (lots && odd) return lots + ' 張 ' + odd + ' 股'
    if (lots) return lots + ' 張'
    return odd + ' 股'
  }
  return v.toLocaleString('en-US', { maximumFractionDigits: 4 }) + ' 股'
}

export function price(v: number | null | undefined, currency: 'TWD' | 'USD'): string {
  if (v == null) return '—'
  return currency === 'USD' ? '$' + v.toFixed(2) : v.toFixed(2)
}

export function ym(month: string | null | undefined): string {
  if (!month) return '—'
  const [y, m] = month.split('-')
  return y + ' 年 ' + Number(m) + ' 月'
}

export function todayISO(): string {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}
