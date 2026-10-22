import { describe, expect, it } from 'vitest'

import type { LivePoint } from '@/features/live/types'

import {
  batterySeverity,
  coarseDuration,
  gpsQuality,
  lastKnown,
  lastKnownSignalBars,
  mergePoints,
  newestTimestamp,
  pointSignalBars,
  secondsSince,
  signalBars,
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

describe('signalBars', () => {
  it('rates LTE/5G readings like the phone does', () => {
    expect(signalBars(-85, 'rsrp')).toBe(4)
    expect(signalBars(-98, 'rsrp')).toBe(4)
    expect(signalBars(-100, 'rsrp')).toBe(3)
    expect(signalBars(-110, 'rsrp')).toBe(2)
    expect(signalBars(-120, 'rsrp')).toBe(1)
    expect(signalBars(-130, 'rsrp')).toBe(0)
  })

  it('uses a different scale for each kind of reading', () => {
    // The same -90 dBm earns a different number of bars for each kind of reading.
    expect(signalBars(-90, 'rscp')).toBe(3)
    expect(signalBars(-90, 'rsrp')).toBe(4)
    expect(signalBars(-90, 'rssi')).toBe(2)
  })
})

describe('pointSignalBars', () => {
  it('prefers the reading in dBm', () => {
    const p = point(0, { phone_signal: 1, phone_signal_dbm: -95, phone_signal_type: 'rsrp' })
    expect(pointSignalBars(p)).toBe(4)
  })

  it('still understands the old 0-4 level', () => {
    expect(pointSignalBars(point(0, { phone_signal: 2 }))).toBe(2)
    expect(pointSignalBars(point(0, { phone_signal: 0 }))).toBe(0)
  })

  it('is null when the point has no signal, or there is no point', () => {
    expect(pointSignalBars(point(0))).toBeNull()
    expect(pointSignalBars(undefined)).toBeNull()
  })
})

describe('lastKnownSignalBars', () => {
  it('looks back to the last point that reported a signal', () => {
    const points = [
      point(0, { phone_signal_dbm: -110, phone_signal_type: 'rsrp' }),
      point(10),
      point(20),
    ]
    expect(lastKnownSignalBars(points)).toBe(2)
  })

  it('is null when nothing was ever reported', () => {
    expect(lastKnownSignalBars([point(0), point(10)])).toBeNull()
  })
})

describe('gpsQuality', () => {
  it('rates by the accuracy radius when there is one', () => {
    expect(gpsQuality(point(0, { horizontal_accuracy: 4 }))).toBe('good')
    expect(gpsQuality(point(0, { horizontal_accuracy: 10 }))).toBe('good')
    expect(gpsQuality(point(0, { horizontal_accuracy: 25 }))).toBe('fair')
    expect(gpsQuality(point(0, { horizontal_accuracy: 80 }))).toBe('poor')
  })

  it('falls back to the satellite count', () => {
    expect(gpsQuality(point(0, { satellites: 12 }))).toBe('good')
    expect(gpsQuality(point(0, { satellites: 6 }))).toBe('fair')
    expect(gpsQuality(point(0, { satellites: 3 }))).toBe('poor')
  })

  it('trusts the accuracy over the satellite count', () => {
    expect(gpsQuality(point(0, { horizontal_accuracy: 60, satellites: 14 }))).toBe('poor')
  })

  it('is null without any measure', () => {
    expect(gpsQuality(point(0))).toBeNull()
    expect(gpsQuality(undefined)).toBeNull()
  })
})
