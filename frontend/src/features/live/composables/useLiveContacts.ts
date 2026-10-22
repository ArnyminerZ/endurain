import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { storeToRefs } from 'pinia'

import type { LiveContact, LiveContactInput } from '@/features/live/types'

import { useAuthStore } from '@/features/auth/stores/auth'
import {
  createLiveContact,
  deleteLiveContact,
  fetchLiveContacts,
} from '@/features/live/services/contacts'
import { queryKeys } from '@/services/queryKeys'

/**
 * The authenticated user's live track contacts. Gated on authentication so it
 * never fires on the login screen.
 *
 * @returns The TanStack Query result for the contact list.
 */
export function useLiveContactsQuery() {
  const { isAuthenticated } = storeToRefs(useAuthStore())

  return useQuery({
    queryKey: queryKeys.liveContacts.list(),
    queryFn: ({ signal }) => fetchLiveContacts(signal),
    enabled: isAuthenticated,
  })
}

/**
 * Add mutation. Invalidates the contact list on settle so it refetches the
 * server-authoritative state.
 *
 * @returns The TanStack Query mutation for adding a contact.
 */
export function useCreateLiveContactMutation() {
  const client = useQueryClient()

  return useMutation<LiveContact, Error, LiveContactInput>({
    mutationKey: queryKeys.liveContacts.all(),
    mutationFn: (input) => createLiveContact(input),
    onSettled: () => {
      void client.invalidateQueries({ queryKey: queryKeys.liveContacts.all() })
    },
  })
}

/**
 * Delete mutation. Invalidates the contact list on settle.
 *
 * @returns The TanStack Query mutation for removing a contact.
 */
export function useDeleteLiveContactMutation() {
  const client = useQueryClient()

  return useMutation<void, Error, number>({
    mutationKey: queryKeys.liveContacts.all(),
    mutationFn: (id) => deleteLiveContact(id),
    onSettled: () => {
      void client.invalidateQueries({ queryKey: queryKeys.liveContacts.all() })
    },
  })
}
