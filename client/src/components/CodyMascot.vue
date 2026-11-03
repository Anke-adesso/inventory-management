<script>
// Module-level loader, shared by all instances.
//
// The Cody rig and artwork are official adesso assets and live ONLY in client/public/cody/
// (gitignored, so a fresh clone has no such folder). They must never enter Vite's module
// graph: everything is fetched at runtime and any failure resolves to null, which makes the
// component render nothing.
const BASE = `${import.meta.env.BASE_URL}cody/`
const FACES = ['happy', 'curious', 'excited'] // only the heads the moments use
const PARTS = ['torso', 'arm-left', 'arm-right', 'leg-left', 'leg-right']

let codyPromise = null

async function fetchJson(file) {
  const res = await fetch(BASE + file)
  if (!res.ok) throw new Error(`${file}: ${res.status}`)
  // The Vite dev server answers unknown paths with index.html (200); json() throws on that.
  return res.json()
}

function preload(url) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve()
    img.onerror = () => reject(new Error(`image: ${url}`))
    img.src = url
  })
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = src
    s.dataset.codyRig = ''
    s.onload = resolve
    s.onerror = () => reject(new Error('rig script'))
    document.head.appendChild(s)
  })
}

function loadCody() {
  if (!codyPromise) {
    codyPromise = (async () => {
      // Manifests first: if the folder is missing we bail out before injecting a <script>
      // (which would log a MIME-type error against the dev server's index.html fallback).
      const [manifest, extra] = await Promise.all([
        fetchJson('rig-manifest.json'),
        fetchJson('rig-extra.json'),
      ])
      const asm = manifest.assembly
      const A = manifest.assets
      const url = key => BASE + A[key].file
      await Promise.all([...PARTS.map(p => preload(url(`parts/${p}`))), ...FACES.map(f => preload(url(`heads/${f}`)))])

      // Same shape inject_cody.py builds, except assets are URLs (the rig just sets img.src).
      window.CODY_RIG = {
        canvas: asm.canvas,
        root: asm.root,
        joints: asm.joints,
        rest: asm.rest_rotations_degrees,
        draw_order: asm.draw_order_back_to_front,
        parts: Object.fromEntries(PARTS.map(p => [p, { pivot: A[`parts/${p}`].pivot, size: A[`parts/${p}`].size }])),
        head_pivot: A['parts/head-blank'].pivot,
        feet: extra.feet,
        arm_flip: extra.arm_flip,
        thumb_switch: extra.thumb_switch_deg,
      }
      window.CODY_ASSETS = {
        parts: Object.fromEntries(PARTS.map(p => [p, url(`parts/${p}`)])),
        heads: Object.fromEntries(FACES.map(f => [f, url(`heads/${f}`)])),
      }
      // The rig reads CODY_RIG/CODY_ASSETS once when it runs, and appends its SVG filter to
      // document.body once per page (module-level guard), so loading it a single time is what
      // prevents duplicates.
      if (!window.Cody) await loadScript(`${BASE}cody-rig.js`)
      if (!window.Cody) throw new Error('rig did not register')
      return window.Cody
    })().catch(() => null)
  }
  return codyPromise
}

// Stage geometry in rig pixels (rig is built for 1920x1080; we only need a box around one Cody).
// Cody is ~445px tall at rig scale 1; the box is CSS-scaled down so rig scale stays 1 (cap is 1.4).
const STAGE_W = 300
const STAGE_H = 470
const FEET_X = STAGE_W / 2
const FEET_Y = STAGE_H - 8
const BODY_H = 445
const TAIL = 3 // seconds of idle() after the moment, then the loop stops

// Each moment: face at start, a choreography (written chronologically, per the skill), and the
// timestamp of its key pose, which is what reduced-motion users get as a still frame.
const MOMENTS = {
  greet: {
    face: 'happy',
    still: 1.25, // mid-wave, arm up
    build(c) {
      let t = c.pop(0.1) // pop in...
      return c.wave(t + 0.1, { reps: 3 }) // ...then wave
    },
  },
  shrug: {
    face: 'curious',
    still: 1.0, // shrug pose reached, question mark visible
    build(c) {
      c.pop(0.1)
      c.emote(0.55, 'question') // face is already curious; emote lands with the reaction
      return Math.max(c.shrug(0.75), 0.55 + 1.6) // react (emote), then act (shrug)
    },
  },
  celebrate: {
    face: 'excited',
    still: 0.95, // apex of the hop, arms up
    build(c) {
      c.pop(0.1)
      c.emote(0.6, 'sparkle')
      const hopEnd = c.celebrate(0.65) // sets 'excited' + big hop
      return Math.max(hopEnd, 0.6 + 1.4)
    },
  },
}
</script>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  moment: {
    type: String,
    default: 'greet',
    validator: v => v in MOMENTS,
  },
  // Rendered height of Cody himself in px.
  size: { type: Number, default: 120 },
})

const ready = ref(false) // box is only reserved once assets are loaded
const state = ref('idle') // idle | playing | done | still (exposed for tests via data attribute)
const stageEl = ref(null)

const k = computed(() => props.size / BODY_H)
const boxStyle = computed(() => ({
  width: `${STAGE_W * k.value}px`,
  height: `${STAGE_H * k.value}px`,
}))
const stageStyle = computed(() => ({
  width: `${STAGE_W}px`,
  height: `${STAGE_H}px`,
  transform: `scale(${k.value})`,
}))

let cody = null
let endT = 0
let rafId = 0
let startedAt = 0
let elapsed = 0 // seconds already played (survives pause)
let disposed = false
let motionQuery = null

const reduced = () => !!motionQuery?.matches

function stopLoop() {
  if (rafId) cancelAnimationFrame(rafId)
  rafId = 0
}

function frame(now) {
  rafId = 0
  elapsed = (now - startedAt) / 1000
  if (elapsed >= endT) {
    // Hold the final frame: idle() fades out at its end, so this is a clean rest pose.
    cody.render(endT + 0.01)
    state.value = 'done'
    return // loop ends here, nothing is rescheduled
  }
  cody.render(elapsed)
  rafId = requestAnimationFrame(frame)
}

function play() {
  if (!cody || disposed || document.hidden) return
  stopLoop()
  state.value = 'playing'
  startedAt = performance.now() - elapsed * 1000 // resume where we paused
  rafId = requestAnimationFrame(frame)
}

function showStill() {
  stopLoop()
  cody.render(MOMENTS[props.moment].still)
  state.value = 'still'
}

function onVisibility() {
  if (!cody || state.value !== 'playing') return
  if (document.hidden) {
    stopLoop() // elapsed keeps the last rendered time; resume continues from it
  } else {
    play()
  }
}

function onMotionChange() {
  if (!cody) return
  if (reduced()) showStill()
  else if (state.value === 'still') {
    elapsed = 0
    play()
  }
}

onMounted(async () => {
  const Cody = await loadCody()
  if (!Cody || disposed) return
  ready.value = true
  await nextTick()
  if (disposed || !stageEl.value) return

  try {
    const def = MOMENTS[props.moment]
    cody = Cody.create(stageEl.value, { x: FEET_X, y: FEET_Y, scale: 1, face: def.face, opacity: 0 })
    const end = def.build(cody)
    endT = cody.idle(end + 0.15, end + 0.15 + TAIL)
  } catch (e) {
    // Never surface a half-built mascot: drop the box too.
    cleanupCody()
    ready.value = false
    return
  }

  motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  motionQuery.addEventListener('change', onMotionChange)
  document.addEventListener('visibilitychange', onVisibility)

  if (reduced()) {
    // pop() keys opacity at t=0.1, so the still frame is already past it
    showStill()
  } else {
    cody.render(0)
    play()
  }
})

function cleanupCody() {
  stopLoop()
  if (cody) {
    cody.destroy?.() // removes the instance from the rig's global list (see client/public/cody/cody-rig.js)
    cody = null
  }
  // Fallback if the rig has no destroy(): at least drop its DOM so nothing is left attached.
  stageEl.value?.replaceChildren()
}

onBeforeUnmount(() => {
  disposed = true
  document.removeEventListener('visibilitychange', onVisibility)
  motionQuery?.removeEventListener('change', onMotionChange)
  cleanupCody()
})
</script>

<template>
  <div
    v-if="ready"
    class="cody-mascot"
    :style="boxStyle"
    :data-moment="moment"
    :data-state="state"
    aria-hidden="true"
  >
    <div ref="stageEl" class="cody-stage" :style="stageStyle"></div>
  </div>
</template>

<style scoped>
.cody-mascot {
  position: relative;
  flex: none;
  /* Emotes and hops intentionally overflow the box a little; never catch clicks. */
  pointer-events: none;
  user-select: none;
}

.cody-stage {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: 0 0;
}
</style>
