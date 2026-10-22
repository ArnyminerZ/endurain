import type { GeoPoint } from '@/composables/useMapProvider'
import type { LivePoint } from '@/features/live/types'

/**
 * Merges newly received points into the accumulated track. Points are keyed by
 * `recorded_at`, so a re-delivered point never duplicates, and the result stays
 * in chronological order even if a response arrives out of order.
 *
 * @param existing - Points already held.
 * @param incoming - Points from the latest response.
 * @returns The combined, de-duplicated, time-ordered track.
 */
export function mergePoints(
  existing: readonly LivePoint[],
  incoming: readonly LivePoint[],
): LivePoint[] {
  if (incoming.length === 0) {
    return existing.slice()
  }
  const byTime = new Map<number, LivePoint>()
  for (const point of existing) {
    byTime.set(Date.parse(point.recorded_at), point)
  }
  for (const point of incoming) {
    byTime.set(Date.parse(point.recorded_at), point)
  }
  return [...byTime.entries()].sort(([a], [b]) => a - b).map(([, point]) => point)
}

/**
 * Returns the timestamp to ask the server for newer points than.
 *
 * @param points - The accumulated track.
 * @returns The newest `recorded_at`, or `null` when nothing was received yet.
 */
export function newestTimestamp(points: readonly LivePoint[]): string | null {
  return points.length > 0 ? (points[points.length - 1]?.recorded_at ?? null) : null
}

/**
 * Converts track points into map coordinates.
 *
 * @param points - The accumulated track.
 * @returns Coordinates in the map provider's shape.
 */
export function toGeoPoints(points: readonly LivePoint[]): GeoPoint[] {
  return points.map((point) => ({ lat: point.latitude, lng: point.longitude }))
}

/**
 * Whole seconds between two instants, never negative.
 *
 * @param from - The earlier instant (ISO string).
 * @param nowMs - The current time in milliseconds.
 * @returns Elapsed whole seconds, or `0` when `from` is not a valid date.
 */
export function secondsSince(from: string, nowMs: number): number {
  const start = Date.parse(from)
  return Number.isFinite(start) ? Math.max(0, Math.floor((nowMs - start) / 1000)) : 0
}

/** A duration split into the unit the viewer should read it in. */
export interface CoarseDuration {
  unit: 'seconds' | 'minutes' | 'hours'
  value: number
}

/**
 * Rounds a duration to its most readable unit for "updated 12 s ago" copy.
 *
 * @param seconds - Duration in whole seconds.
 * @returns The value and the unit it is expressed in.
 */
export function coarseDuration(seconds: number): CoarseDuration {
  if (seconds < 60) {
    return { unit: 'seconds', value: seconds }
  }
  if (seconds < 3600) {
    return { unit: 'minutes', value: Math.floor(seconds / 60) }
  }
  return { unit: 'hours', value: Math.floor(seconds / 3600) }
}

/** A viewer warns once this many push intervals pass without an update. */
const STALE_INTERVALS = 3
/** Floor for the warning threshold, so a 1 s interval does not flicker on a slow network. */
const MIN_STALE_SECONDS = 15

/**
 * Seconds without a new point after which the viewer warns the client is silent.
 * Derived from the interval the client declared when it started the session, so
 * a client that reports once a minute is not flagged after 90 seconds.
 *
 * @param updateIntervalSeconds - How often the client said it would push points.
 * @returns The stale threshold in seconds.
 */
export function staleThresholdSeconds(updateIntervalSeconds: number): number {
  return Math.max(MIN_STALE_SECONDS, Math.ceil(updateIntervalSeconds) * STALE_INTERVALS)
}

/** The device-status fields a point may carry. */
export type DeviceStatusKey = 'gadget_battery' | 'phone_battery' | 'phone_signal'

/** Battery percent at or below which a battery is flagged as low. */
export const LOW_BATTERY_PERCENT = 20
/** Battery percent at or below which a battery is flagged as critical. */
export const CRITICAL_BATTERY_PERCENT = 10
/** Signal level (0-4) at or below which the phone signal is flagged as weak. */
export const WEAK_SIGNAL_LEVEL = 1

/**
 * Finds the last value the client reported for a status field. Clients send
 * battery and signal only now and then, so the newest point usually lacks them
 * and the viewer has to look back to the most recent point that carried one.
 *
 * @param points - The accumulated track, oldest first.
 * @param key - The status field to look up.
 * @returns The most recent reported value, or `null` when it was never sent.
 */
export function lastKnown(points: readonly LivePoint[], key: DeviceStatusKey): number | null {
  for (let index = points.length - 1; index >= 0; index -= 1) {
    const value = points[index]?.[key]
    if (value !== null && value !== undefined) {
      return value
    }
  }
  return null
}

/** How worrying a status reading is. */
export type StatusSeverity = 'ok' | 'low' | 'critical'

/**
 * Classifies a battery percentage.
 *
 * @param percent - Battery level, 0-100.
 * @returns `critical` at or below 10 %, `low` at or below 20 %, otherwise `ok`.
 */
export function batterySeverity(percent: number): StatusSeverity {
  if (percent <= CRITICAL_BATTERY_PERCENT) {
    return 'critical'
  }
  return percent <= LOW_BATTERY_PERCENT ? 'low' : 'ok'
}

/**
 * Classifies a phone signal level.
 *
 * @param level - Signal level, 0 (none) to 4 (great).
 * @returns `critical` with no signal, `low` when weak, otherwise `ok`.
 */
export function signalSeverity(level: number): StatusSeverity {
  if (level <= 0) {
    return 'critical'
  }
  return level <= WEAK_SIGNAL_LEVEL ? 'low' : 'ok'
}
