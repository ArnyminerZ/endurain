import { computed, onScopeDispose, ref, type ComputedRef, type Ref } from 'vue'

import type { LivePoint, PublicLive } from '@/features/live/types'

import { fetchPublicLive } from '@/features/live/services/live'
import { mergePoints, newestTimestamp } from '@/features/live/utils/liveTrack'
import { HttpError } from '@/services/http'

/** Delay between polls while the page is visible. */
export const POLL_INTERVAL_MS = 5_000
/** Delay before the next poll when the server still has older points to send. */
const CATCH_UP_INTERVAL_MS = 250
/** Ceiling for the retry delay after consecutive network failures. */
const MAX_BACKOFF_MS = 60_000

/** Where the viewer is in the life of the shared session. */
export type LiveStatus = 'loading' | 'live' | 'ended' | 'error'

/** Result of {@link useLiveSession}. */
export interface UseLiveSession {
  /** Lifecycle status; `ended` means the link is dead for good. */
  status: Ref<LiveStatus>
  /** Latest session metadata (athlete, name, activity type, start time). */
  session: Ref<PublicLive | null>
  /** The whole track received so far, oldest first. */
  points: Ref<LivePoint[]>
  /** The newest point, if any. */
  latest: ComputedRef<LivePoint | null>
  /** `true` while polling keeps failing but earlier data is still shown. */
  reconnecting: Ref<boolean>
  /** Retries immediately, e.g. from an error screen. */
  retry: () => void
}

/**
 * Follows a live share link by polling the public endpoint. Each poll asks only
 * for points newer than the ones already held (`since`), pauses while the tab
 * is hidden, backs off on network errors and stops for good on a 404, which is
 * how an ended, expired or forged link answers.
 *
 * @param token - The share token from the route.
 * @returns Reactive session state plus a manual {@link UseLiveSession.retry}.
 */
export function useLiveSession(token: string): UseLiveSession {
  const status = ref<LiveStatus>('loading')
  const session = ref<PublicLive | null>(null)
  const points = ref<LivePoint[]>([])
  const reconnecting = ref(false)
  const latest = computed(() => points.value[points.value.length - 1] ?? null)

  let timer: ReturnType<typeof setTimeout> | null = null
  let controller: AbortController | null = null
  let failures = 0
  let stopped = false

  /** Cancels the scheduled poll, if any. */
  function clearTimer(): void {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
  }

  /**
   * Schedules the next poll unless polling has ended or the tab is hidden.
   *
   * @param delayMs - Delay before the poll runs.
   */
  function schedule(delayMs: number): void {
    clearTimer()
    if (stopped || document.hidden) {
      return
    }
    timer = setTimeout(() => void poll(), delayMs)
  }

  /** Fetches newer points once and plans the next poll from the outcome. */
  async function poll(): Promise<void> {
    clearTimer()
    controller?.abort()
    controller = new AbortController()
    try {
      const data = await fetchPublicLive(token, newestTimestamp(points.value), controller.signal)
      failures = 0
      reconnecting.value = false
      session.value = data
      points.value = mergePoints(points.value, data.points)
      status.value = 'live'
      const behind = points.value.length < data.total_points
      schedule(behind ? CATCH_UP_INTERVAL_MS : POLL_INTERVAL_MS)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return
      }
      if (error instanceof HttpError && error.status === 404) {
        stopped = true
        status.value = 'ended'
        return
      }
      failures += 1
      if (session.value === null) {
        status.value = 'error'
      } else {
        reconnecting.value = true
      }
      schedule(Math.min(POLL_INTERVAL_MS * 2 ** failures, MAX_BACKOFF_MS))
    }
  }

  /** Pauses while hidden and catches up immediately when shown again. */
  function onVisibilityChange(): void {
    if (stopped) {
      return
    }
    if (document.hidden) {
      clearTimer()
    } else {
      void poll()
    }
  }

  document.addEventListener('visibilitychange', onVisibilityChange)
  void poll()

  onScopeDispose(() => {
    stopped = true
    clearTimer()
    controller?.abort()
    document.removeEventListener('visibilitychange', onVisibilityChange)
  })

  return {
    status,
    session,
    points,
    latest,
    reconnecting,
    retry: () => {
      if (!stopped) {
        status.value = session.value === null ? 'loading' : status.value
        void poll()
      }
    },
  }
}
