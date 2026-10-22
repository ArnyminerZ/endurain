import type { PublicLive } from '@/features/live/types'

import { apiFetch } from '@/services/http'

/**
 * Fetches a live session by its share token. Anonymous by design: the token is
 * the credential, so no auth header is sent and a 401 never triggers a refresh.
 *
 * @param token - The share token from the `/live/<token>` link.
 * @param since - Return only points recorded after this ISO timestamp.
 * @param signal - Optional abort signal for cancellation.
 * @returns The athlete, session metadata, latest point and (new) track points.
 * @throws {HttpError} With status 404 when the link is unknown, forged or ended.
 */
export function fetchPublicLive(
  token: string,
  since?: string | null,
  signal?: AbortSignal,
): Promise<PublicLive> {
  const query = since ? `?since=${encodeURIComponent(since)}` : ''
  return apiFetch<PublicLive>(`/public/live/${encodeURIComponent(token)}${query}`, {
    auth: false,
    signal,
  })
}
