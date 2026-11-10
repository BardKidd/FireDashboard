export type FxMode = 'live' | 'ma200' | 'custom'
export type AssetType = 'equity' | 'leveraged' | 'bond' | 'cash' | 'contract'
export type LogKind = 'buy' | 'sell' | 'adjust' | 'deposit' | 'withdraw'

export interface Config {
  birth_year: number
  birth_month: number
  target_retire_age: number
  annual_expense_twd: number
  swr: number
  expected_nominal_return: number
  inflation_rate: number
  monthly_contribution_twd: number
  contribution_indexed: boolean
  fx_mode: FxMode
  custom_fx_rate: number | null
  stress_drop: number
  us_dividend_tax: number
  tw_nhi_rate: number
  tw_nhi_threshold: number
}

export interface FxInfo {
  mode: FxMode
  live: number | null
  ma200: number | null
  custom: number | null
  used: number | null
}

export interface Position {
  symbol: string
  name: string
  market: 'US' | 'TW' | 'CASH' | 'CONTRACT'
  asset_type: AssetType
  currency: 'USD' | 'TWD'
  shares: number
  avg_cost: number | null
  stress_beta: number
  target_shares: number | null
  archived: boolean
  price: number | null
  price_date: string | null
  prev_close: number | null
  ma20: number | null
  ma60: number | null
  ma200: number | null
  high_52w: number | null
  value_native: number | null
  value_twd: number | null
  live_value_twd: number | null
  cost_native: number | null
  pnl_native: number | null
  weight: number
  contract?: ContractInfo
}

export interface ContractInput {
  name: string
  start_month: string
  monthly_deposit: number
  term_months: number
  payout: number
  valuation: 'accrued' | 'deposited'
  closed: boolean
  note: string | null
}

export interface ContractInfo extends ContractInput {
  id: number
  paid_months: number
  deposited: number
  accrued: number
  value: number
  matured: boolean
  payout_month: string
  implied_annual_rate: number
}

export interface Holdings {
  fx: FxInfo
  rows: Position[]
  total_twd: number
}

export interface TimeToCoast {
  status: 'achieved' | 'reachable' | 'unreachable'
  months: number | null
  month: string | null
  gap_at_retirement?: number
  retire_month?: string | null
}

export interface Summary {
  today: string
  age_years: number
  months_remaining: number
  real_return: number
  fire_target: number
  coast_target: number
  total_assets: number
  total_assets_live_fx: number
  progress: number | null
  time_to_coast: TimeToCoast
  monthly_income_if_stop: number
  stress: {
    beta: number
    drop: number
    progress: number | null
    stressed_value: number
    stressed_progress: number | null
    max_market_drop: number | null
  }
  fx: FxInfo
  day_change_twd: number | null
  missing_prices: string[]
}

export interface ProjectionPoint {
  t: number
  month: string
  coast_target: number
  no_contribution: number
  with_contribution: number
}

export interface Projection {
  today: string
  fire_target: number
  series: ProjectionPoint[]
}

export interface HistoryPoint {
  date: string
  total_value_twd: number
  total_value_real: number
  total_value_usd: number
  cash_twd: number
  fx_rate: number | null
  fx_ma200: number | null
  coast_target_twd: number | null
}

export interface ShareLog {
  id: number
  date: string
  symbol: string
  kind: LogKind | 'split' | 'dividend'
  delta_shares: number
  split_ratio: number | null
  total_shares_after: number
  note: string | null
  source_symbol: string | null
  created_at: string
}

export interface DividendRow {
  symbol: string
  ex_date: string
  per_share: number
  shares_held: number
  gross: number
  tax_withheld: number
  nhi_premium: number
  net: number
  currency: 'USD' | 'TWD'
}

export interface Status {
  refreshing: boolean
  last_success_date: string | null
  symbols: { symbol: string; last_success_date: string | null; last_attempt_at: string | null; last_error: string | null }[]
  errors: string[]
}

export interface SplitRow {
  id: number
  symbol: string
  date: string
  ratio: number
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch('/api' + path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let msg = res.status + ' ' + res.statusText
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') msg = body.detail
      else if (Array.isArray(body.detail)) msg = body.detail.map((d: { msg: string }) => d.msg).join('；')
    } catch {
      /* keep status text */
    }
    throw new Error(msg)
  }
  return res.json() as Promise<T>
}

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) })
const enc = encodeURIComponent

export const api = {
  config: () => request<Config>('/config'),
  saveConfig: (c: Config) => request<Config>('/config', json('PUT', c)),
  holdings: () => request<Holdings>('/holdings'),
  addHolding: (b: {
    symbol: string
    name?: string
    shares: number
    date?: string
    avg_cost?: number | null
    asset_type?: Exclude<AssetType, 'cash' | 'contract'> | null
  }) => request<{ symbol: string }>('/holdings', json('POST', b)),
  patchHolding: (
    symbol: string,
    b: Partial<Pick<Position, 'name' | 'avg_cost' | 'asset_type' | 'stress_beta' | 'target_shares' | 'archived'>>,
  ) => request<{ ok: boolean }>('/holdings/' + enc(symbol), json('PATCH', b)),
  deleteHolding: (symbol: string) =>
    request<{ archived?: boolean; deleted?: boolean }>('/holdings/' + enc(symbol), { method: 'DELETE' }),
  logs: (symbol?: string) => request<ShareLog[]>('/logs' + (symbol ? '?symbol=' + enc(symbol) : '')),
  addLog: (b: {
    symbol: string
    date: string
    kind: LogKind
    delta?: number
    set_total?: number
    price?: number
    note?: string
  }) => request<ShareLog>('/logs', json('POST', b)),
  patchLog: (id: number, b: { date?: string; delta?: number; note?: string }) =>
    request<ShareLog>('/logs/' + id, json('PATCH', b)),
  deleteLog: (id: number) => request<{ ok: boolean }>('/logs/' + id, { method: 'DELETE' }),
  splits: () => request<SplitRow[]>('/splits'),
  addSplit: (b: { symbol: string; date: string; ratio: number }) => request<{ ok: boolean }>('/splits', json('POST', b)),
  summary: () => request<Summary>('/summary'),
  projection: () => request<Projection>('/projection'),
  history: () => request<HistoryPoint[]>('/history'),
  dividends: () => request<DividendRow[]>('/dividends'),
  status: () => request<Status>('/status'),
  addContract: (b: ContractInput) => request<ContractInfo>('/contracts', json('POST', b)),
  updateContract: (id: number, b: ContractInput) => request<ContractInfo>('/contracts/' + id, json('PUT', b)),
  deleteContract: (id: number) => request<{ ok: boolean }>('/contracts/' + id, { method: 'DELETE' }),
  refresh: () => request<{ started: boolean }>('/refresh', { method: 'POST' }),
}
