/**
 * Campfire waltz: a short G-major melody in 3/4, synthesized with Web Audio.
 * No audio files, so the nginx image stays the same size.
 */
const NOTES: Record<string, number> = {
  D4: 293.66, E4: 329.63, 'F#4': 369.99, G4: 392.0, A4: 440.0, B4: 493.88, C5: 523.25, D5: 587.33, E5: 659.25,
}

// [note, beats]; null is a rest. 16 bars plus one bar of breath before it loops.
const SONG: [string | null, number][] = [
  ['D4', 1], ['G4', 1], ['B4', 1], ['D5', 2], ['B4', 1], ['C5', 1], ['B4', 1], ['A4', 1], ['G4', 3],
  ['E4', 1], ['G4', 1], ['C5', 1], ['B4', 2], ['G4', 1], ['A4', 1], ['B4', 1], ['A4', 1], ['D4', 3],
  ['D4', 1], ['G4', 1], ['B4', 1], ['D5', 2], ['E5', 1], ['D5', 1], ['B4', 1], ['G4', 1], ['C5', 2], ['E5', 1],
  ['D5', 1], ['B4', 1], ['G4', 1], ['A4', 2], ['B4', 1], ['A4', 2], ['F#4', 1], ['G4', 3], [null, 3],
]
const BEAT = 60 / 80
const VOLUME = 0.16

let ctx: AudioContext | undefined
let out: GainNode
let timer: number | undefined
let idx = 0
let next = 0

function setup() {
  const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
  ctx = new AC()
  out = ctx.createGain()
  out.gain.value = 0
  const lp = ctx.createBiquadFilter()
  lp.type = 'lowpass'
  lp.frequency.value = 2200
  // A small generated room so notes ring a little after they end.
  const verb = ctx.createConvolver()
  const len = Math.floor(ctx.sampleRate * 2.4)
  const ir = ctx.createBuffer(2, len, ctx.sampleRate)
  for (let c = 0; c < 2; c++) {
    const d = ir.getChannelData(c)
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 3)
  }
  verb.buffer = ir
  const wet = ctx.createGain()
  wet.gain.value = 0.35
  out.connect(lp)
  lp.connect(ctx.destination)
  lp.connect(verb)
  verb.connect(wet)
  wet.connect(ctx.destination)
}

/** A soft plucked note that holds for its beats, then fades over ~1.6 s. */
function pluck(freq: number, t: number, dur: number) {
  const c = ctx!
  const g = c.createGain()
  g.gain.setValueAtTime(0, t)
  g.gain.linearRampToValueAtTime(0.45, t + 0.03)
  g.gain.exponentialRampToValueAtTime(0.3, t + 0.4)
  g.gain.setValueAtTime(0.3 * Math.pow(0.8, dur), t + dur * 0.9)
  g.gain.exponentialRampToValueAtTime(0.0008, t + dur + 1.6)
  g.connect(out)
  for (const [type, mul, vol] of [['triangle', 1, 1], ['sine', 2, 0.18]] as const) {
    const o = c.createOscillator()
    const v = c.createGain()
    o.type = type
    o.frequency.value = freq * mul
    v.gain.value = vol
    o.connect(v)
    v.connect(g)
    o.start(t)
    o.stop(t + dur + 1.7)
  }
}

function tick() {
  const c = ctx!
  while (next < c.currentTime + 1.2) {
    const [n, beats] = SONG[idx]
    const lilt = idx % 3 === 0 ? 0 : 0.015
    if (n) pluck(NOTES[n], next + lilt, beats * BEAT)
    next += beats * BEAT
    idx = (idx + 1) % SONG.length
  }
}

export function playMusic() {
  if (!ctx) setup()
  const c = ctx!
  void c.resume()
  out.gain.cancelScheduledValues(c.currentTime)
  out.gain.setValueAtTime(out.gain.value, c.currentTime)
  out.gain.linearRampToValueAtTime(VOLUME, c.currentTime + 1.5)
  if (timer === undefined) {
    idx = 0
    next = c.currentTime + 0.1
    tick()
    timer = window.setInterval(tick, 250)
  }
}

export function stopMusic() {
  if (!ctx) return
  out.gain.cancelScheduledValues(ctx.currentTime)
  out.gain.setValueAtTime(out.gain.value, ctx.currentTime)
  out.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.8)
  window.clearInterval(timer)
  timer = undefined
}
