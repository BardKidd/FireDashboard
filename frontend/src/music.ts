/**
 * Campfire music: twenty gentle tunes (see music-tracks.ts) played in turn by
 * one soft pluck, synthesized with Web Audio. No audio files, so the nginx
 * image stays the same size.
 *
 * Each tune plays twice, then hands over to the next: the old tune's last
 * notes and reverb fade out while the new one fades in over a few seconds.
 */
import { TRACKS, parseMelody, type Note } from './music-tracks'

const VOLUME = 0.16
const PLAYS_PER_TRACK = 2
const FADE_IN = 3
const FADE_OUT = 5

const SONGS: Note[][] = TRACKS.map(parseMelody)

let ctx: AudioContext | undefined
let out: GainNode
let timer: number | undefined
let trackGain: GainNode | undefined
let track = Math.floor(Math.random() * TRACKS.length)
let idx = 0
let plays = 0
let next = 0
const listeners = new Set<(name: string) => void>()

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
function pluck(dest: AudioNode, freq: number, t: number, dur: number) {
  const c = ctx!
  const g = c.createGain()
  g.gain.setValueAtTime(0, t)
  g.gain.linearRampToValueAtTime(0.45, t + 0.03)
  g.gain.exponentialRampToValueAtTime(0.3, t + 0.4)
  g.gain.setValueAtTime(0.3 * Math.pow(0.8, dur), t + dur * 0.9)
  g.gain.exponentialRampToValueAtTime(0.0008, t + dur + 1.6)
  g.connect(dest)
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

/** Give the current tune its own gain, faded in from `t`. */
function startTrack(t: number, fade: boolean) {
  const c = ctx!
  trackGain = c.createGain()
  trackGain.gain.setValueAtTime(fade ? 0 : 1, t)
  if (fade) trackGain.gain.linearRampToValueAtTime(1, t + FADE_IN)
  trackGain.connect(out)
  idx = 0
  plays = 0
  for (const fn of listeners) fn(TRACKS[track].name)
}

/** Fade the current tune out from `t` and move on to the next one. */
function advance(t: number) {
  const old = trackGain!
  old.gain.setValueAtTime(1, t)
  old.gain.linearRampToValueAtTime(0, t + FADE_OUT)
  window.setTimeout(() => old.disconnect(), (t - ctx!.currentTime + FADE_OUT + 1) * 1000)
  track = (track + 1) % TRACKS.length
  startTrack(t, true)
}

function tick() {
  const c = ctx!
  while (next < c.currentTime + 1.2) {
    const song = SONGS[track]
    const beat = 60 / TRACKS[track].bpm
    const [freq, beats] = song[idx]
    const last = idx === song.length - 1
    // The closing rest is a breath between repeats; on the final repeat the
    // next tune enters there instead, while this one's tail dies away.
    if (last && freq === null && plays === PLAYS_PER_TRACK - 1) {
      advance(next)
      continue
    }
    const lilt = idx % TRACKS[track].meter === 0 ? 0 : 0.015
    if (freq) pluck(trackGain!, freq, next + lilt, beats * beat)
    next += beats * beat
    idx++
    if (idx === song.length) {
      idx = 0
      plays++
      if (plays === PLAYS_PER_TRACK) advance(next)
    }
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
    next = c.currentTime + 0.1
    // Resuming after a mute starts the same tune again from the top.
    trackGain?.disconnect()
    startTrack(next, false)
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

/** The tune that is playing (or will play next), e.g. for a tooltip. */
export function currentTrackName(): string {
  return TRACKS[track].name
}

/** Be told whenever a new tune starts. Returns an unsubscribe function. */
export function onTrackChange(fn: (name: string) => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
