import type { LiveContact, LiveContactInput } from '@/features/live/types'

import { apiFetch } from '@/services/http'

/**
 * Fetches the people emailed when the user starts a live track.
 *
 * @param signal - Optional abort signal for cancellation.
 * @returns The user's live track contacts, oldest first.
 * @throws {HttpError} When the request fails.
 */
export function fetchLiveContacts(signal?: AbortSignal): Promise<LiveContact[]> {
  return apiFetch<LiveContact[]>('/live/contacts', { signal })
}

/**
 * Adds a person to the live track notification list.
 *
 * @param input - Display name and email address of the person.
 * @returns The created contact.
 * @throws {HttpError} 409 when the email is already on the list, 400 when the
 *   list is full.
 */
export function createLiveContact(input: LiveContactInput): Promise<LiveContact> {
  return apiFetch<LiveContact>('/live/contacts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: input.name.trim(), email: input.email.trim() }),
  })
}

/**
 * Removes a person from the live track notification list.
 *
 * @param id - The contact id.
 * @throws {HttpError} When the request fails.
 */
export async function deleteLiveContact(id: number): Promise<void> {
  await apiFetch<void>(`/live/contacts/${id}`, { method: 'DELETE', responseType: 'void' })
}
