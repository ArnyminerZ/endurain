<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ErrorState } from '@/components/ui/error-state'
import { LoadingState } from '@/components/ui/loading-state'
import { MetricPill } from '@/components/ui/metric-pill'
import ActivityMap from '@/features/activities/components/ActivityMap.vue'
import { useDisplayUnits } from '@/features/activities/composables/useActivityDetail'
import {
  formatElevation,
  formatHmsDuration,
  speedToDisplay,
  speedUnitLabel,
  temperatureToDisplay,
} from '@/features/activities/utils/format'
import { useLiveSession } from '@/features/live/composables/useLiveSession'
import { coarseDuration, secondsSince, toGeoPoints } from '@/features/live/utils/liveTrack'

/** A generic "workout" activity type: the live feed carries only a label, so speed and cadence use neutral units. */
const GENERIC_ACTIVITY_TYPE = 10
/** After this many seconds without an update the viewer is warned the phone may be offline. */
const STALE_AFTER_SECONDS = 90

const route = useRoute()
const { t } = useI18n()
const units = useDisplayUnits()

const token = String(route.params.token ?? '')
const { status, session, points, latest, reconnecting, retry } = useLiveSession(token)

// A 1 Hz clock drives the "updated N s ago" and elapsed-time readouts.
const nowMs = ref(Date.now())
let clock: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  clock = setInterval(() => (nowMs.value = Date.now()), 1000)
})
onBeforeUnmount(() => {
  if (clock !== null) {
    clearInterval(clock)
  }
})

const geoPoints = computed(() => toGeoPoints(points.value))
const title = computed(() => session.value?.name || session.value?.activity_type || t('live.title'))

/**
 * Formats a duration as the coarsest readable unit, e.g. "12 s" or "3 min".
 *
 * @param seconds - Duration in whole seconds.
 * @returns The localised short duration.
 */
function formatAgo(seconds: number): string {
  const { unit, value } = coarseDuration(seconds)
  return t(`live.ago.${unit}`, { n: value })
}

const sinceUpdate = computed(() =>
  session.value ? secondsSince(session.value.last_update_at, nowMs.value) : 0,
)
const isStale = computed(() => status.value === 'live' && sinceUpdate.value >= STALE_AFTER_SECONDS)
const elapsed = computed(() =>
  session.value ? formatHmsDuration(secondsSince(session.value.started_at, nowMs.value)) : '--',
)

const heartRate = computed(() => latest.value?.heart_rate ?? null)
const speed = computed(() => {
  const value = latest.value?.speed
  return value === null || value === undefined
    ? null
    : speedToDisplay(value, GENERIC_ACTIVITY_TYPE, units.value).toFixed(1)
})
const elevation = computed(() => {
  const value = latest.value?.elevation
  return value === null || value === undefined ? null : formatElevation(value, units.value)
})

/**
 * Formats a Celsius reading in the viewer's unit system.
 *
 * @param celsius - Temperature in °C, or nullish when not reported.
 * @returns The rounded value, or `null` when there is no reading.
 */
function temperature(celsius: number | null | undefined): string | null {
  return celsius === null || celsius === undefined
    ? null
    : temperatureToDisplay(celsius, units.value).toFixed(1)
}
const temperatureUnit = computed(() => (units.value === 'imperial' ? '°F' : '°C'))
const ambient = computed(() => temperature(latest.value?.temperature))
const skin = computed(() => temperature(latest.value?.skin_temperature))
const cadence = computed(() => latest.value?.cadence ?? null)
</script>

<template>
  <main class="mx-auto flex min-h-dvh w-full max-w-3xl flex-col gap-4 p-4">
    <LoadingState v-if="status === 'loading'" :label="t('live.loading')" class="my-auto" />

    <ErrorState
      v-else-if="status === 'error'"
      :title="t('live.error.title')"
      :description="t('live.error.message')"
      @retry="retry"
    />

    <Card
      v-else-if="status === 'ended'"
      class="my-auto flex flex-col items-center gap-3 p-8 text-center"
    >
      <h1 class="text-xl font-medium text-foreground">{{ t('live.ended.title') }}</h1>
      <p class="max-w-sm text-sm text-muted-foreground">{{ t('live.ended.message') }}</p>
      <Button as-child variant="outline">
        <RouterLink :to="{ name: 'home' }">{{ t('app.notFound.action') }}</RouterLink>
      </Button>
    </Card>

    <template v-else-if="session">
      <header class="flex flex-wrap items-center justify-between gap-2">
        <div class="min-w-0">
          <h1 class="truncate text-xl font-medium text-foreground">{{ title }}</h1>
          <p class="text-sm text-muted-foreground">
            {{ t('live.sharing', { name: session.athlete }) }}
          </p>
        </div>
        <Badge :variant="reconnecting ? 'warning' : 'info'" class="gap-1.5">
          <span
            class="size-2 rounded-full bg-current motion-safe:animate-pulse"
            aria-hidden="true"
          />
          {{ reconnecting ? t('live.reconnecting') : t('live.live') }}
        </Badge>
      </header>

      <Card class="h-[50vh] min-h-72 overflow-hidden p-0">
        <ActivityMap v-if="geoPoints.length > 0" :points="geoPoints" :refit-on-update="false" />
        <div
          v-else
          class="flex size-full items-center justify-center p-6 text-center text-sm text-muted-foreground"
        >
          {{ t('live.waiting') }}
        </div>
      </Card>

      <Card class="grid grid-cols-2 gap-4 p-4 sm:grid-cols-3">
        <MetricPill :label="t('live.metrics.elapsed')" :value="elapsed" />
        <MetricPill
          v-if="heartRate !== null"
          :label="t('live.metrics.heartRate')"
          :value="heartRate"
          unit="bpm"
          accent="hr"
        />
        <MetricPill
          v-if="speed !== null"
          :label="t('live.metrics.speed')"
          :value="speed"
          :unit="speedUnitLabel(GENERIC_ACTIVITY_TYPE, units)"
        />
        <MetricPill
          v-if="elevation !== null"
          :label="t('live.metrics.elevation')"
          :value="elevation.value"
          :unit="elevation.unit"
        />
        <MetricPill v-if="cadence !== null" :label="t('live.metrics.cadence')" :value="cadence" />
        <MetricPill
          v-if="ambient !== null"
          :label="t('live.metrics.temperature')"
          :value="ambient"
          :unit="temperatureUnit"
        />
        <MetricPill
          v-if="skin !== null"
          :label="t('live.metrics.skinTemperature')"
          :value="skin"
          :unit="temperatureUnit"
        />
      </Card>

      <p
        class="text-center text-sm"
        :class="isStale ? 'text-effort' : 'text-muted-foreground'"
        role="status"
      >
        {{
          isStale
            ? t('live.stale', { time: formatAgo(sinceUpdate) })
            : t('live.updated', { time: formatAgo(sinceUpdate) })
        }}
      </p>
    </template>
  </main>
</template>
