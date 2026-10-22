import { effectScope } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { PublicLive } from '@/features/live/types'

import { POLL_INTERVAL_MS, useLiveSession } from '@/features/live/composables/useLiveSession'
import { fetchPublicLive } from '@/features/live/services/live'
import { HttpError } from '@/services/http'

vi.mock('@/features/live/services/live', () => ({
  fetchPublicLive: vi.fn<typeof fetchPublicLive>(),
}))

function response(seconds: number[], total = seconds.length): PublicLive {
  const points = seconds.map((s) => ({
    recorded_at: new Date(Date.UTC(2026, 9, 22, 8, 0, s)).toISOString(),
    latitude: 39,
    longitude: -0.5,
    heart_rate: 100 + s,
  }))
  return {
    athlete: 'Arnau',
    activity_type: 'Run',
    name: null,
    started_at: points[0]?.recorded_at ?? '2026-10-22T08:00:00Z',
    last_update_at: points[points.length - 1]?.recorded_at ?? '2026-10-22T08:00:00Z',
    latest: points[points.length - 1] ?? null,
    points,
    total_points: total,
  }
}

function start() {
  const scope = effectScope()
  const live = scope.run(() => useLiveSession('tok'))!
  return { live, stop: () => scope.stop() }
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.mocked(fetchPublicLive).mockReset()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useLiveSession', () => {
  it('loads the track, then asks only for newer points', async () => {
    vi.mocked(fetchPublicLive)
      .mockResolvedValueOnce(response([0, 10], 2))
      .mockResolvedValueOnce(response([20], 3))
    const { live, stop } = start()

    await vi.advanceTimersByTimeAsync(0)
    expect(live.status.value).toBe('live')
    expect(live.points.value).toHaveLength(2)
    expect(vi.mocked(fetchPublicLive).mock.calls[0]?.[1]).toBeNull()

    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS)
    expect(live.points.value).toHaveLength(3)
    expect(vi.mocked(fetchPublicLive).mock.calls[1]?.[1]).toBe(
      new Date(Date.UTC(2026, 9, 22, 8, 0, 10)).toISOString(),
    )
    expect(live.latest.value?.heart_rate).toBe(120)
    stop()
  })

  it('ends for good on a 404 and stops polling', async () => {
    vi.mocked(fetchPublicLive).mockRejectedValue(new HttpError(404, 'Not Found'))
    const { live, stop } = start()
    await vi.advanceTimersByTimeAsync(0)
    expect(live.status.value).toBe('ended')

    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 5)
    expect(fetchPublicLive).toHaveBeenCalledTimes(1)
    stop()
  })

  it('shows an error before any data and retries with backoff', async () => {
    vi.mocked(fetchPublicLive)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValue(response([0]))
    const { live, stop } = start()
    await vi.advanceTimersByTimeAsync(0)
    expect(live.status.value).toBe('error')

    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 2)
    expect(live.status.value).toBe('live')
    stop()
  })

  it('keeps the data and flags reconnecting when a later poll fails', async () => {
    vi.mocked(fetchPublicLive)
      .mockResolvedValueOnce(response([0]))
      .mockRejectedValueOnce(new Error('offline'))
    const { live, stop } = start()
    await vi.advanceTimersByTimeAsync(0)
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS)

    expect(live.status.value).toBe('live')
    expect(live.reconnecting.value).toBe(true)
    expect(live.points.value).toHaveLength(1)
    stop()
  })

  it('catches up quickly while the server still has older points', async () => {
    vi.mocked(fetchPublicLive)
      .mockResolvedValueOnce(response([0, 10], 4))
      .mockResolvedValueOnce(response([20, 30], 4))
    const { live, stop } = start()
    await vi.advanceTimersByTimeAsync(0)
    await vi.advanceTimersByTimeAsync(300)
    expect(live.points.value).toHaveLength(4)
    stop()
  })

  it('stops polling when its scope is disposed', async () => {
    vi.mocked(fetchPublicLive).mockResolvedValue(response([0]))
    const { stop } = start()
    await vi.advanceTimersByTimeAsync(0)
    stop()
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 3)
    expect(fetchPublicLive).toHaveBeenCalledTimes(1)
  })
})
