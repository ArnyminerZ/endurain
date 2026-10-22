import { beforeEach, describe, expect, it, vi } from 'vitest'

import { flushPromises, mount } from '@vue/test-utils'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'

import { apiFetch } from '@/services/http'
import i18n from '@/i18n'
import LiveContactFormDialog from '@/features/live/components/LiveContactFormDialog.vue'

// Replace only the network seam; keep a real `HttpError` for the dialog's
// `instanceof` checks in its error paths.
vi.mock('@/services/http', () => {
  class HttpError extends Error {
    constructor(
      public status: number,
      message?: string,
    ) {
      super(message)
    }
  }
  return { apiFetch: vi.fn<typeof apiFetch>(), HttpError }
})

/** Passthrough stub so the reka-ui portal/focus-trap is skipped. */
const passthrough = { template: '<div><slot /></div>' }

function mountDialog() {
  return mount(LiveContactFormDialog, {
    props: { open: true },
    global: {
      plugins: [i18n, [VueQueryPlugin, { queryClient: new QueryClient() }]],
      stubs: {
        Dialog: passthrough,
        DialogContent: passthrough,
        DialogHeader: passthrough,
        DialogTitle: passthrough,
        DialogDescription: passthrough,
        DialogFooter: passthrough,
      },
    },
  })
}

async function fillAndSubmit(wrapper: ReturnType<typeof mountDialog>, name: string, email: string) {
  await wrapper.find('input[name="name"]').setValue(name)
  await wrapper.find('input[name="email"]').setValue(email)
  await wrapper.find('form').trigger('submit')
  await flushPromises()
}

describe('LiveContactFormDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('adds the person and reports success', async () => {
    vi.mocked(apiFetch).mockResolvedValue({ id: 1, name: 'Ana', email: 'ana@example.com' })
    const wrapper = mountDialog()

    await fillAndSubmit(wrapper, 'Ana', 'ana@example.com')

    expect(apiFetch).toHaveBeenCalledTimes(1)
    const [path, init] = vi.mocked(apiFetch).mock.calls[0] ?? []
    expect(path).toBe('/live/contacts')
    expect(JSON.parse(String(init?.body))).toEqual({ name: 'Ana', email: 'ana@example.com' })
    expect(wrapper.emitted('success')).toBeTruthy()
  })

  it('does not call the API for an invalid email', async () => {
    const wrapper = mountDialog()

    await fillAndSubmit(wrapper, 'Ana', 'not-an-email')

    expect(apiFetch).not.toHaveBeenCalled()
    expect(wrapper.emitted('success')).toBeFalsy()
  })

  it('does not call the API without a name', async () => {
    const wrapper = mountDialog()

    await fillAndSubmit(wrapper, '', 'ana@example.com')

    expect(apiFetch).not.toHaveBeenCalled()
  })

  it('explains a duplicate email and keeps the dialog open', async () => {
    const { HttpError } = await import('@/services/http')
    vi.mocked(apiFetch).mockRejectedValue(new HttpError(409, 'Conflict'))
    const wrapper = mountDialog()

    await fillAndSubmit(wrapper, 'Ana', 'ana@example.com')

    expect(wrapper.emitted('error')?.[0]).toEqual([
      i18n.global.t('settings.liveContacts.form.duplicate'),
    ])
    expect(wrapper.emitted('update:open')).toBeFalsy()
  })

  it('explains a full list', async () => {
    const { HttpError } = await import('@/services/http')
    vi.mocked(apiFetch).mockRejectedValue(new HttpError(400, 'Bad request'))
    const wrapper = mountDialog()

    await fillAndSubmit(wrapper, 'Ana', 'ana@example.com')

    expect(wrapper.emitted('error')?.[0]).toEqual([
      i18n.global.t('settings.liveContacts.form.limitReached'),
    ])
  })
})
