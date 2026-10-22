import { describe, expect, it } from 'vitest'

import type { LivePoint } from '@/features/live/types'

import {
  batterySeverity,
  coarseDuration,
  lastKnown,
  mergePoints,
  newestTimestamp,
  secondsSince,
  signalSeverity,
  staleThresholdSeconds,
  toGeoPoints,
} from '@/features/live/utils/liveTrack'

function point(second: number, extra: Partial<LivePoint> = {}): LivePoint {
  return {
    recorded_at: new Date(Date.UTC(2026, 9, 22, 8, 0, second)).toISOString(),
    latitude: 39 + second / 1000,
    longitude: -0.5,
    ...extra,
  }
}

describe('mergePoints', () => {
  it('appends new points in chronological order', () => {
    const merged = mergePoints([point(0), point(10)], [point(30), point(20)])
    expect(merged.map((p) => p.latitude)).toEqual([39, 39.01, 39.02, 39.03])
  })

  it('does not duplicate a re-delivered point and keeps the newer copy', () => {
    const merged = mergePoints([point(0, { heart_rate: 100 })], [point(0, { heart_rate: 110 })])
    expect(merged).toHaveLength(1)
    expect(merged[0]?.heart_rate).toBe(110)
  })

  it('returns a copy when nothing is incoming', () => {
    const existing = [point(0)]
    const merged = mergePoints(existing, [])
    expect(merged).toEqual(existing)
    expect(merged).not.toBe(existing)
  })
})

describe('newestTimestamp', () => {
  it('is null for an empty track', () => {
    expect(newestTimestamp([])).toBeNull()
  })

  it('is the last point time', () => {
    expect(newestTimestamp([point(0), point(10)])).toBe(point(10).recorded_at)
  })
})

describe('toGeoPoints', () => {
  it('maps latitude/longitude to lat/lng', () => {
    expect(toGeoPoints([point(0)])).toEqual([{ lat: 39, lng: -0.5 }])
  })
})

describe('secondsSince', () => {
  it('counts whole seconds and never goes negative', () => {
    const start = point(0).recorded_at
    const startMs = Date.parse(start)
    expect(secondsSince(start, startMs + 12_900)).toBe(12)
    expect(secondsSince(start, startMs - 5_000)).toBe(0)
  })

  it('is 0 for an invalid date', () => {
    expect(secondsSince('nope', Date.now())).toBe(0)
  })
})

describe('staleThresholdSeconds', () => {
  it('is three intervals for a slow client', () => {
    expect(staleThresholdSeconds(60)).toBe(180)
    expect(staleThresholdSeconds(10)).toBe(30)
  })

  it('never drops below the floor', () => {
    expect(staleThresholdSeconds(1)).toBe(15)
    expect(staleThresholdSeconds(5)).toBe(15)
  })
})

describe('lastKnown', () => {
  it('looks back to the most recent point that carried the field', () => {
    const points = [
      point(0, { phone_battery: 80 }),
      point(10, { phone_battery: 75 }),
      point(20),
      point(30),
    ]
    expect(lastKnown(points, 'phone_battery')).toBe(75)
  })

  it('is null when the client never sent it, and keeps a reported zero', () => {
    expect(lastKnown([point(0), point(10)], 'gadget_battery')).toBeNull()
    expect(lastKnown([point(0, { phone_signal: 0 }), point(10)], 'phone_signal')).toBe(0)
  })
})

describe('batterySeverity', () => {
  it('flags low and critical levels', () => {
    expect(batterySeverity(55)).toBe('ok')
    expect(batterySeverity(20)).toBe('low')
    expect(batterySeverity(11)).toBe('low')
    expect(batterySeverity(10)).toBe('critical')
    expect(batterySeverity(0)).toBe('critical')
  })
})

describe('signalSeverity', () => {
  it('flags weak and missing signal', () => {
    expect(signalSeverity(4)).toBe('ok')
    expect(signalSeverity(2)).toBe('ok')
    expect(signalSeverity(1)).toBe('low')
    expect(signalSeverity(0)).toBe('critical')
  })
})

describe('coarseDuration', () => {
  it('picks the most readable unit', () => {
    expect(coarseDuration(5)).toEqual({ unit: 'seconds', value: 5 })
    expect(coarseDuration(125)).toEqual({ unit: 'minutes', value: 2 })
    expect(coarseDuration(7300)).toEqual({ unit: 'hours', value: 2 })
  })
})
