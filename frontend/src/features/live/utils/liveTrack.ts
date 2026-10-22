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
