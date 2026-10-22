import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchPublicLive } from '@/features/live/services/live'
import { apiFetch } from '@/services/http'

vi.mock('@/services/http', () => ({ apiFetch: vi.fn<typeof apiFetch>() }))

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe('fetchPublicLive', () => {
  it('calls the public endpoint anonymously', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({})
    await fetchPublicLive('abc.def')
    expect(apiFetch).toHaveBeenCalledWith('/public/live/abc.def', {
      auth: false,
      signal: undefined,
    })
  })

  it('encodes the since timestamp', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({})
    await fetchPublicLive('tok', '2026-10-22T08:00:10+00:00')
    expect(vi.mocked(apiFetch).mock.calls[0]?.[0]).toBe(
      '/public/live/tok?since=2026-10-22T08%3A00%3A10%2B00%3A00',
    )
  })
})
