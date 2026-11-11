// Words for the guided tour and the "?" tips. One place, so the tour and the
// tips never disagree about what a number means.
import type { Config, Summary } from '../api'
import type { MobileTab } from '../mobile'
import { money, pct, wan } from '../format'

export interface Explain {
  title: string
  body: string[]
}

/** Short definitions shown by the "?" next to a value. */
export const TIPS: Record<string, Explain> = {
  assets: {
    title: '柴堆（總資產）',
    body: [
      '所有持股、現金與約定存款的台幣市值加總。',
      '美股用「參數設定」選的匯率換算。若不是用即時匯率，下面會另外列出以即時匯率算的金額供對照。',
    ],
  },
  progress: {
    title: '火勢（Coast 達成率）',
    body: [
      '總資產 ÷ 今天的 Coast 線。到 100% 就代表從今天起一塊錢都不再投入，光靠複利也能在退休時長到終點。',
      '終點（FIRE 目標）＝退休年開銷 ÷ 安全提領率。',
      'Coast 線＝終點 ÷ (1 + 實質報酬)^距離退休的年數。越接近退休，Coast 線越高，最後等於終點。',
    ],
  },
  coastDate: {
    title: '不用再添柴',
    body: [
      '照目前每月定期定額繼續投入，資產第一次追上 Coast 線的月份。從那個月起就算停止投入，也能在退休時達標。',
      '若退休前都追不上，會顯示退休時還差多少。',
    ],
  },
  income: {
    title: '現在停手，退休後每月可領',
    body: [
      '假設今天起完全不再投入，現有資產以實質報酬一路長到退休，再用安全提領率每年提領，換算成每月金額。',
      '金額是今天的購買力，已扣掉通膨。',
    ],
  },
  trajectory: {
    title: 'Coast FIRE 雙軌預測',
    body: [
      'Coast 門檻（虛線）：每個月的 Coast 線，隨時間往上走，退休那天等於終點。',
      '零投入複利：現在停止投入，資產自己長的樣子。',
      '持續定期定額：照目前每月投入的樣子；和 Coast 門檻交叉的點就是「不用再添柴」的月份。',
      '歷史真實資產：每天收盤後記下的實際資產，已依通膨換算成今天的購買力。',
    ],
  },
  beta: {
    title: '組合 beta',
    body: [
      '整體組合跟著大盤動的程度。1 表示和大盤同步，0.5 表示大盤跌 10% 你約跌 5%。',
      '現金、債券、約定存款算 0；槓桿 ETF 依倍數（例如 2 倍槓桿算 2）。可在每檔持股的編輯中調整。',
    ],
  },
  cushion: {
    title: '可承受大盤下跌',
    body: [
      '大盤最多跌多少，資產仍然高於今天的 Coast 線。也就是「就算遇到這種跌幅，也不用重新開始添柴」。',
      '資產還沒超過 Coast 線時不會顯示。',
    ],
  },
  stress: {
    title: '壓力測試',
    body: [
      '假設大盤跌到「參數設定」裡的跌幅，用組合 beta 估算資產與達成率會變成多少。',
      '這只是暫時的帳面數字，每月定期定額照常進行。',
    ],
  },
  fx: {
    title: '美元匯率與平滑',
    body: [
      '即時：最新匯率。200 日均：過去 200 個交易日的平均匯率。',
      '預設用 200 日均算達成率，讓台幣升貶不會讓火勢每天忽大忽小。可在「參數設定」改成即時或自訂。',
    ],
  },
  weight: {
    title: '占比',
    body: ['這檔持股的台幣市值占總資產的比例，也就是營火裡那根柴的粗細。'],
  },
  dividends: {
    title: '股息入帳',
    body: [
      '依持股與除息資料自動計算，直接加進對應幣別的現金。',
      '美股扣除預扣稅（預設 30%），台股單筆達門檻時扣二代健保補充保費。',
    ],
  },
  stars: {
    title: '星星與等級',
    body: [
      '打卡、收集里程碑、領股息都會得到星星。等級看「累積獲得」的星星，兌換獎勵只花「可用星星」，不會降級。',
    ],
  },
  streak: {
    title: '連續週數',
    body: ['只要一週內有打卡就算連續，漏掉一兩天不會中斷，不用有壓力。'],
  },
  basket: {
    title: '目標股數籃子',
    body: [
      '把 Coast 或 FIRE 目標金額，依照你現在的配置比例分給每檔標的，再用 200 日均價換算成股數。',
      '之後只要專心收集股數，不用每天盯著市值。每張卡片可以手動調整目標股數。',
    ],
  },
}

export interface TourStep {
  /** data-tour value of the element to spotlight; none = centered card. */
  target?: string
  title: string
  body: string[]
  /** Phone layout: the bottom tab that holds the target. */
  tab?: MobileTab
  mobileOnly?: boolean
}

export type TourName = 'dashboard' | 'collect'

export function dashboardTour(s?: Summary, c?: Config, mobile = false): TourStep[] {
  const rr = s ? pct(s.real_return) : '實質報酬'
  const years = s ? Math.round(s.months_remaining / 12) : null
  const steps: TourStep[] = [
    {
      title: '歡迎來到營火旁',
      body: [
        '這裡追蹤的是 Coast FIRE：存到一個「就算從此不再投入，複利也會在退休時幫你長到目標」的金額。',
        '接下來用一分鐘帶你看每個數字的意思。',
      ],
    },
    {
      target: 'campfire',
      tab: 'fire',
      title: '這堆營火就是你的投資組合',
      body: [
        '每根柴是一檔持股（小的會合併成一組），越粗代表占比越高。',
        '火焰高度是 Coast 達成率；黃色虛線輪廓是 100%，火燒到那裡就不用再添柴。',
        '大盤下跌的日子火會被風吹得晃一點，但柴都還在。',
        '點一根柴，可以直接記錄那檔的買賣。',
      ],
    },
    {
      target: 'assets',
      tab: 'fire',
      title: '柴堆（總資產）',
      body: [
        '所有持股、現金與約定存款換算成台幣的總和。',
        s ? `美股目前用 ${s.fx.mode === 'live' ? '即時' : s.fx.mode === 'ma200' ? '200 日均' : '自訂'}匯率換算，可在「參數設定」更改。` : '美股依「參數設定」裡選的匯率換算。',
      ],
    },
    {
      target: 'progress',
      tab: 'fire',
      title: '火勢（Coast 達成率）',
      body: [
        '總資產 ÷ 今天的 Coast 線。',
        s && c
          ? `終點 ${wan(s.fire_target)} ＝ 年開銷 ${wan(c.annual_expense_twd)} ÷ 提領率 ${pct(c.swr)}。`
          : '終點 ＝ 退休年開銷 ÷ 安全提領率。',
        s
          ? `Coast 線 ${wan(s.coast_target)} ＝ 終點往回折現 ${years} 年（實質報酬 ${rr}／年）。`
          : 'Coast 線 ＝ 終點依實質報酬往回折現到今天。',
        s ? `所以現在 ${wan(s.total_assets)} ÷ ${wan(s.coast_target)} ＝ ${pct(s.progress)}。` : '',
      ].filter(Boolean),
    },
    {
      target: 'coast-date',
      tab: 'fire',
      title: '不用再添柴',
      body: [
        c
          ? `照目前每月投入 ${money(c.monthly_contribution_twd)}，資產追上 Coast 線的月份。`
          : '照目前每月定期定額，資產追上 Coast 線的月份。',
        '從那個月起就算停止投入，複利也會在退休時把你帶到終點。',
      ],
    },
    {
      target: 'income',
      tab: 'fire',
      title: '現在停手，退休後每月可領',
      body: [
        '假設今天起完全不再投入，現有資產長到退休後，用安全提領率每月可以領多少。',
        '是今天的購買力，已經扣掉通膨，可以直接和現在的生活費比較。',
      ],
    },
    {
      target: 'trajectory',
      tab: 'path',
      title: 'Coast FIRE 雙軌預測',
      body: [
        '虛線是每個月的 Coast 門檻，會一路往上走到退休時的終點。',
        '兩條預測線分別是「現在停止投入」與「持續定期定額」；後者碰到虛線的點就是不用再添柴的月份。',
        '歷史真實資產每天收盤後自動多一個點。可切換「未來 10 年」放大近期。',
      ],
    },
    {
      target: 'stress',
      tab: 'path',
      title: '抗跌安全邊際',
      body: [
        '組合 beta：整體跟大盤連動的程度。現金、債券、約定存款算 0，槓桿 ETF 依倍數。',
        '可承受大盤下跌：大盤跌多少以內，資產仍高於今天的 Coast 線。',
        s ? `若大盤下跌 ${pct(s.stress.drop, 0)}：估算的資產與達成率，提醒你下跌只是暫時的帳面數字。` : '若大盤下跌：估算的資產與達成率。',
      ],
    },
    {
      target: 'fx',
      tab: 'path',
      title: '美元匯率',
      body: [
        '列出即時匯率與 200 日均匯率。',
        '預設用 200 日均算達成率，讓台幣升貶不會讓火勢每天忽大忽小。這就是「平滑匯率」。',
      ],
    },
    {
      target: 'holdings',
      tab: 'logs',
      title: '持倉',
      body: [
        '「新增標的」加入台股或美股（代號會自動抓報價），「＋ 約定存款」加入儲蓄險或零存整付。',
        mobile
          ? '點一列就能新增買賣，或補登過去某天的股數；鉛筆可以改名稱、類型與 beta。'
          : '每列的「記錄」可以新增買賣，或補登過去某天的股數；鉛筆可以改名稱、類型與 beta。',
        '占比就是營火裡那根柴的粗細。勾選「顯示成本與損益」才會出現均價與未實現損益。',
      ],
    },
    {
      target: 'add-fab',
      mobileOnly: true,
      title: '添柴',
      body: ['底部中間的「＋」隨時可以記錄買賣，也能加入新的標的或約定存款。'],
    },
    {
      target: 'dividends',
      tab: 'logs',
      title: '股息入帳',
      body: [
        '依除息資料自動計算，稅後金額直接加進現金，不用手動記。',
        '美股扣預扣稅，台股單筆達門檻時扣二代健保。點一下展開明細。',
      ],
    },
    {
      target: 'config',
      title: '參數設定',
      body: [
        '出生年月、退休年齡、年開銷、提領率、預期報酬、通膨、每月投入、匯率模式與壓力測試跌幅都在這裡。',
        '上面所有數字都由這些假設算出來，改了會立刻重算。',
      ],
    },
    {
      target: 'refresh',
      title: '更新報價',
      body: [
        '系統每天收盤後會自動抓價，想馬上更新可以按這裡。左上角會顯示報價更新到哪一天。',
        ...(mobile ? ['在頁面最上方往下拉，也能更新報價。'] : []),
      ],
    },
    {
      target: 'view-switch',
      title: mobile ? '底部分頁' : '儀表板與收集冊',
      body: [
        ...(mobile ? ['營火、柴堆（持股與股息）、軌跡（預測圖與抗跌）分在不同分頁。'] : []),
        '「收集冊」是只看股數、不看市值的收集模式，有打卡、成就與獎勵。第一次打開時也會有導覽。',
      ],
    },
    {
      target: 'help',
      title: '隨時可以再看一次',
      body: ['按「導覽」就能重新播放這段介紹。各數值旁的小「?」也可以隨時點開看定義。'],
    },
  ]
  return steps.filter((x) => mobile || !x.mobileOnly)
}

export function collectTour(): TourStep[] {
  return [
    {
      title: '收集冊：只看股數',
      body: [
        '這裡把投資變成慢慢收集。不看每天的市值漲跌，只看股數一點一點變多。',
      ],
    },
    {
      target: 'player',
      title: '等級與星星',
      body: [
        '打卡、收集里程碑、領股息都會得到星星與經驗值。',
        '等級看累積獲得的星星，兌換獎勵只花「可用星星」，等級不會因此下降。',
      ],
    },
    {
      target: 'checkin',
      title: '每日打卡',
      body: [
        '每天一次 +10 星星，可以順便寫一句話給未來的自己。',
        '連續是以「週」計算，一週內有打卡就算，漏掉一兩天不會中斷。',
      ],
    },
    {
      target: 'basket',
      title: '目標股數籃子',
      body: [
        '把 Coast（或 FIRE）目標金額依目前配置分給每檔標的，再用 200 日均價換算成要收集的股數。',
        '圓環是整個籃子的完成度。Coast 籃子集滿後可以切換成 FIRE 繼續。',
      ],
    },
    {
      target: 'collection',
      title: '收集卡',
      body: [
        '每檔股票一張卡：目前股數、收集天數、下一個里程碑與籃子進度。「調整」可以手動設定目標股數。',
        '價格低於 60 日均時會標「特價中」，告訴你同樣金額能多收集多少股。點卡片可以看收集曲線。',
      ],
    },
    {
      target: 'badges',
      title: '下一個目標與成就牆',
      body: ['列出快要達成的里程碑。成就一旦拿到就不會被收回，就算之後賣掉股票也一樣。'],
    },
    {
      target: 'rewards',
      title: '獎勵兌換',
      body: ['替自己設定真實生活的獎勵，例如一頓好吃的晚餐。也可以用等級解鎖不同的主題色。'],
    },
  ]
}
