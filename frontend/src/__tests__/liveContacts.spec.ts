import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  createLiveContact,
  deleteLiveContact,
  fetchLiveContacts,
} from '@/features/live/services/contacts'
import { apiFetch } from '@/services/http'

vi.mock('@/services/http', () => ({ apiFetch: vi.fn<typeof apiFetch>() }))

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe('fetchLiveContacts', () => {
  it('reads the contact list', async () => {
    const contacts = [{ id: 1, name: 'Ana', email: 'ana@example.com' }]
    vi.mocked(apiFetch).mockResolvedValueOnce(contacts)

    await expect(fetchLiveContacts()).resolves.toEqual(contacts)
    expect(apiFetch).toHaveBeenCalledWith('/live/contacts', { signal: undefined })
  })
})

describe('createLiveContact', () => {
  it('posts the trimmed name and email as JSON', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ id: 2, name: 'Bo', email: 'bo@example.com' })

    await createLiveContact({ name: '  Bo ', email: ' bo@example.com ' })

    const [path, init] = vi.mocked(apiFetch).mock.calls[0] ?? []
    expect(path).toBe('/live/contacts')
    expect(init?.method).toBe('POST')
    expect(JSON.parse(String(init?.body))).toEqual({ name: 'Bo', email: 'bo@example.com' })
  })
})

describe('deleteLiveContact', () => {
  it('deletes by id without expecting a body', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(undefined)

    await deleteLiveContact(7)

    expect(apiFetch).toHaveBeenCalledWith('/live/contacts/7', {
      method: 'DELETE',
      responseType: 'void',
    })
  })
})
