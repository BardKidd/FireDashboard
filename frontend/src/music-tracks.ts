/**
 * Twenty campfire tunes in the same family: gentle major-key melodies,
 * 72–86 BPM, mostly 3/4 waltzes, all played by the same soft pluck.
 *
 * Melodies are written in scale degrees so every tune shares one vocabulary
 * and can sit in whichever key keeps it close to its neighbours:
 *   1–7      degrees of the major scale, around the tonic
 *   5, 6,    a trailing comma drops an octave
 *   1'       a trailing apostrophe raises an octave
 *   -        a rest
 *   :n       length in beats (default 1)
 *   |        bar line, checked against the meter
 *
 * Keys walk the circle of fifths (G, D, C, F) so that one tune hands over to
 * the next without a jarring change of colour.
 */
export interface Track {
  name: string
  /** MIDI note of the tonic (60 = C4). */
  tonic: number
  bpm: number
  /** Beats per bar. */
  meter: 3 | 4
  melody: string
}

const C = 60
const D = 62
const F = 65
const G = 67

export const TRACKS: Track[] = [
  {
    name: '營火圓舞曲',
    tonic: G, bpm: 80, meter: 3,
    melody: `5, 1 3 | 5:2 3 | 4 3 2 | 1:3 |
             6, 1 4 | 3:2 1 | 2 3 2 | 5,:3 |
             5, 1 3 | 5:2 6 | 5 3 1 | 4:2 6 |
             5 3 1 | 2:2 3 | 2:2 7, | 1:3 | -:3`,
  },
  {
    name: '餘燼小徑',
    tonic: D, bpm: 78, meter: 3,
    melody: `1 3 5 | 6:2 5 | 4 3 2 | 3:3 |
             1 3 5 | 1':2 7 | 6 5 4 | 5:3 |
             6 5 4 | 3:2 1 | 2 3 4 | 5:2 3 |
             4 3 2 | 1:2 7, | 1:3 | -:3`,
  },
  {
    name: '提燈山丘',
    tonic: G, bpm: 76, meter: 3,
    melody: `5:2 3 | 1:2 3 | 5 6 5 | 3:3 |
             4:2 2 | 7,:2 2 | 4 5 4 | 2:3 |
             5:2 3 | 1':2 7 | 6 5 6 | 5:2 3 |
             4 3 2 | 3:2 2 | 1:3 | -:3`,
  },
  {
    name: '松煙',
    tonic: C, bpm: 80, meter: 3,
    melody: `3 2 1 | 5,:2 1 | 2 3 4 | 3:3 |
             3 2 1 | 6,:2 1 | 2 1 7, | 1:3 |
             5 4 3 | 4:2 2 | 3 2 1 | 2:3 |
             3 2 1 | 5,:2 6, | 7, 2 7, | 1:3 | -:3`,
  },
  {
    name: '豐收月',
    tonic: F, bpm: 74, meter: 3,
    melody: `1:2 2 | 3:2 5 | 6 5 3 | 5:3 |
             6:2 5 | 3:2 1 | 2 3 2 | 1:3 |
             1:2 2 | 3:2 5 | 6 1' 6 | 5:2 3 |
             2 3 5 | 3:2 2 | 1:3 | -:3`,
  },
  {
    name: '靜靜的小溪',
    tonic: C, bpm: 72, meter: 4,
    melody: `1 2 3 5 | 3:2 2:2 | 1 2 3 1 | 6,:4 |
             5, 1 2 3 | 2:2 1 6, | 5,:2 6,:2 | 1:4 |
             3 5 6 5 | 3:2 2:2 | 3 5 6 1' | 5:4 |
             6 5 3 2 | 3:2 2 1 | 1:4 | -:4`,
  },
  {
    name: '毛毯',
    tonic: G, bpm: 76, meter: 3,
    melody: `5,:2 1 | 3:2 2 | 1 7, 6, | 5,:3 |
             6,:2 7, | 1:2 3 | 2:3 | 2:2 - |
             5,:2 1 | 3:2 5 | 6 5 3 | 5:3 |
             4 3 2 | 1:2 7, | 1:3 | -:3`,
  },
  {
    name: '爐邊之歌',
    tonic: D, bpm: 82, meter: 3,
    melody: `3 4 5 | 5:2 3 | 4 3 2 | 2:2 - |
             2 3 4 | 4:2 2 | 3 2 1 | 1:3 |
             5 6 5 | 4:2 3 | 2 3 4 | 5:3 |
             6 5 4 | 3:2 2 | 1:3 | -:3`,
  },
  {
    name: '穀倉燈火',
    tonic: G, bpm: 80, meter: 3,
    melody: `5, 1 2 | 3:2 1 | 2 3 4 | 3:2 1 |
             6, 7, 1 | 2:2 5, | 6, 7, 2 | 1:3 |
             3 4 5 | 6:2 5 | 4 3 2 | 3:2 1 |
             2:2 3 | 2:2 7, | 1:3 | -:3`,
  },
  {
    name: '老門廊',
    tonic: C, bpm: 72, meter: 4,
    melody: `5:2 6 5 | 3:2 1:2 | 2 3 4 3 | 2:4 |
             5:2 6 5 | 3:2 1':2 | 7 6 5 4 | 5:4 |
             6:2 5 4 | 3:2 1:2 | 2 3 4 2 | 7,:2 5,:2 |
             1 2 3 2 | 1:2 7, 2 | 1:4 | -:4`,
  },
  {
    name: '楓葉小路',
    tonic: F, bpm: 78, meter: 3,
    melody: `1 2 3 | 5:2 3 | 2 1 6, | 1:3 |
             1 2 3 | 6:2 5 | 3 2 3 | 2:3 |
             1 2 3 | 5:2 6 | 1' 6 5 | 3:2 5 |
             6 5 3 | 2:2 3 | 1:3 | -:3`,
  },
  {
    name: '螢火蟲圓舞曲',
    tonic: C, bpm: 84, meter: 3,
    melody: `5, 6, 7, | 1:2 3 | 5:2 3 | 2:3 |
             6, 7, 1 | 2:2 4 | 6:2 5 | 3:3 |
             5 6 5 | 4:2 2 | 3 4 3 | 2:2 7, |
             1 2 3 | 2:2 7, | 1:3 | -:3`,
  },
  {
    name: '蘋果酒的傍晚',
    tonic: G, bpm: 76, meter: 3,
    melody: `3:2 2 | 1:2 6, | 5,:2 6, | 1:3 |
             2:2 3 | 5:2 3 | 2:3 | 2:2 - |
             3:2 5 | 6:2 1' | 6:2 5 | 3:3 |
             2:2 3 | 2 1 6, | 1:3 | -:3`,
  },
  {
    name: '星空草原',
    tonic: D, bpm: 74, meter: 4,
    melody: `1:2 3 5 | 1':2 7 6 | 5:2 3 4 | 5:4 |
             6:2 5 4 | 3:2 2 1 | 2 3 4 5 | 2:4 |
             1:2 3 5 | 1':2 7 6 | 5 6 5 3 | 4:4 |
             3:2 2 1 | 7,:2 2:2 | 1:4 | -:4`,
  },
  {
    name: '水壺冒煙',
    tonic: G, bpm: 82, meter: 3,
    melody: `3 3 4 | 5:2 1 | 6 6 5 | 3:3 |
             4 4 3 | 2:2 5, | 2 2 3 | 1:3 |
             3 3 4 | 5:2 1' | 7 6 5 | 6:3 |
             5 3 1 | 2:2 7, | 1:3 | -:3`,
  },
  {
    name: '河邊石頭',
    tonic: C, bpm: 80, meter: 3,
    melody: `1:2 5, | 6,:2 1 | 2 3 2 | 1:3 |
             3:2 2 | 1:2 6, | 5,:3 | 5,:2 - |
             1:2 3 | 5:2 6 | 5 3 2 | 3:3 |
             2:2 1 | 6,:2 2 | 1:3 | -:3`,
  },
  {
    name: '柴堆',
    tonic: F, bpm: 80, meter: 3,
    melody: `1 3 5 | 1:2 3 | 2 4 6 | 5:3 |
             5 4 3 | 4:2 6 | 5 3 2 | 1:3 |
             6 5 4 | 3:2 5 | 4 3 2 | 3:3 |
             4 3 2 | 5,:2 7, | 1:3 | -:3`,
  },
  {
    name: '黃昏牧場',
    tonic: C, bpm: 76, meter: 3,
    melody: `3:3 | 2 3 5 | 6:3 | 5 3 2 |
             3:3 | 2 1 6, | 1:3 | 1:2 - |
             5:3 | 6 5 3 | 2:3 | 3 5 6 |
             5:2 3 | 2 3 2 | 1:3 | -:3`,
  },
  {
    name: '拼布被',
    tonic: G, bpm: 74, meter: 4,
    melody: `5, 1 2 3 | 3:2 2:2 | 1 2 3 5 | 2:4 |
             2 3 5 6 | 5:2 3:2 | 2 1 2 3 | 1:4 |
             5 6 5 3 | 2:2 1:2 | 6, 1 2 3 | 5:4 |
             6 5 3 2 | 1 2 3:2 | 1:4 | -:4`,
  },
  {
    name: '最後的餘燼',
    tonic: D, bpm: 72, meter: 3,
    melody: `5:2 4 | 3:2 2 | 1:2 7, | 1:3 |
             6:2 5 | 4:2 3 | 2:3 | 2:2 - |
             5:2 4 | 3:2 1' | 7:2 6 | 5:3 |
             4:2 3 | 2:2 7, | 1:3 | -:3`,
  },
]

const MAJOR = [0, 2, 4, 5, 7, 9, 11]

/** A parsed note: frequency in Hz (null for a rest) and length in beats. */
export type Note = [number | null, number]

export function parseMelody(t: Track): Note[] {
  const notes: Note[] = []
  for (const [i, bar] of t.melody.split('|').entries()) {
    let beats = 0
    for (const tok of bar.trim().split(/\s+/).filter(Boolean)) {
      const m = /^([1-7-])([,']*)(?::(\d+))?$/.exec(tok)
      if (!m) throw new Error(`${t.name}: bad token "${tok}"`)
      const len = m[3] ? Number(m[3]) : 1
      beats += len
      if (m[1] === '-') {
        notes.push([null, len])
        continue
      }
      const octave = [...m[2]].reduce((o, c) => o + (c === "'" ? 1 : -1), 0)
      const midi = t.tonic + MAJOR[Number(m[1]) - 1] + 12 * octave
      notes.push([440 * Math.pow(2, (midi - 69) / 12), len])
    }
    if (beats !== t.meter) throw new Error(`${t.name}: bar ${i + 1} has ${beats} beats, expected ${t.meter}`)
  }
  return notes
}
