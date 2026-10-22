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

/** Which measurement a phone signal reading in dBm is. */
export type SignalType = NonNullable<LivePoint['phone_signal_type']>

/** Number of bars a signal indicator has. */
export const MAX_SIGNAL_BARS = 4

/**
 * Lowest dBm that earns 4, 3, 2 and 1 bars for each kind of reading. They mirror the
 * defaults Android uses for its own signal icon, so the bars match what the phone shows.
 */
const SIGNAL_BAR_THRESHOLDS: Record<SignalType, readonly [number, number, number, number]> = {
  rsrp: [-98, -108, -118, -128],
  rssi: [-78, -86, -97, -110],
  rscp: [-85, -95, -105, -115],
}

/**
 * Turns a mobile signal reading into bars, the way a phone's status bar does.
 *
 * @param dbm - Signal power in dBm (e.g. -97).
 * @param type - The kind of measurement `dbm` is.
 * @returns 0 (no usable signal) to 4 (great) bars.
 */
export function signalBars(dbm: number, type: SignalType): number {
  const thresholds = SIGNAL_BAR_THRESHOLDS[type]
  const reached = thresholds.findIndex((minimum) => dbm >= minimum)
  return reached === -1 ? 0 : MAX_SIGNAL_BARS - reached
}

/**
 * The signal bars a single point reports. A reading in dBm wins; clients that only
 * send the old 0-4 level are still understood.
 *
 * @param point - The point to read.
 * @returns 0-4 bars, or `null` when the point carries no signal reading.
 */
export function pointSignalBars(point: LivePoint | null | undefined): number | null {
  if (!point) {
    return null
  }
  if (
    point.phone_signal_dbm !== null &&
    point.phone_signal_dbm !== undefined &&
    point.phone_signal_type
  ) {
    return signalBars(point.phone_signal_dbm, point.phone_signal_type)
  }
  if (point.phone_signal !== null && point.phone_signal !== undefined) {
    return Math.min(Math.max(point.phone_signal, 0), MAX_SIGNAL_BARS)
  }
  return null
}

/**
 * Finds the signal bars of the most recent point that reported a signal. Clients send
 * the signal only now and then, so the newest point usually lacks it.
 *
 * @param points - The accumulated track, oldest first.
 * @returns 0-4 bars, or `null` when no point ever reported a signal.
 */
export function lastKnownSignalBars(points: readonly LivePoint[]): number | null {
  for (let index = points.length - 1; index >= 0; index -= 1) {
    const bars = pointSignalBars(points[index])
    if (bars !== null) {
      return bars
    }
  }
  return null
}

/** How trustworthy a position is, in words a non-technical viewer understands. */
export type GpsQuality = 'good' | 'fair' | 'poor'

/** Horizontal accuracy (meters) up to which a position is good / fair. */
export const GOOD_ACCURACY_METERS = 10
export const FAIR_ACCURACY_METERS = 30
/** Satellite count from which a fix is good / fair, when no accuracy is reported. */
export const GOOD_SATELLITES = 8
export const FAIR_SATELLITES = 5

/**
 * Rates the quality of a position. The accuracy radius says it directly; the number of
 * satellites is a rougher guide used only when the client sends no accuracy.
 *
 * @param point - The point to rate.
 * @returns `good`, `fair` or `poor`, or `null` when the point reports neither measure.
 */
export function gpsQuality(point: LivePoint | null | undefined): GpsQuality | null {
  if (!point) {
    return null
  }
  const accuracy = point.horizontal_accuracy
  if (accuracy !== null && accuracy !== undefined) {
    if (accuracy <= GOOD_ACCURACY_METERS) {
      return 'good'
    }
    return accuracy <= FAIR_ACCURACY_METERS ? 'fair' : 'poor'
  }
  const satellites = point.satellites
  if (satellites !== null && satellites !== undefined) {
    if (satellites >= GOOD_SATELLITES) {
      return 'good'
    }
    return satellites >= FAIR_SATELLITES ? 'fair' : 'poor'
  }
  return null
}

/** The bars (out of 3) that represent a {@link GpsQuality}. */
export const GPS_QUALITY_BARS: Record<GpsQuality, number> = { poor: 1, fair: 2, good: 3 }
