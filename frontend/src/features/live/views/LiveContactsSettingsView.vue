<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { BellRing, Plus } from '@lucide/vue'

import type { LiveContact } from '@/features/live/types'

import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { EmptyState } from '@/components/ui/empty-state'
import { ListPanel } from '@/components/ui/list-panel'
import { Skeleton } from '@/components/ui/skeleton'
import { useToasts } from '@/composables/useToasts'
import LiveContactFormDialog from '@/features/live/components/LiveContactFormDialog.vue'
import LiveContactListItem from '@/features/live/components/LiveContactListItem.vue'
import {
  useDeleteLiveContactMutation,
  useLiveContactsQuery,
} from '@/features/live/composables/useLiveContacts'

const { t } = useI18n()
const toasts = useToasts()

const contactsQuery = useLiveContactsQuery()
const deleteMutation = useDeleteLiveContactMutation()

const contacts = computed(() => contactsQuery.data.value ?? [])
const isEmpty = computed(
  () =>
    !contactsQuery.isPending.value && !contactsQuery.isError.value && contacts.value.length === 0,
)

const isFormOpen = ref(false)

// Delete confirmation state.
const isDeleteOpen = ref(false)
const contactToDelete = ref<LiveContact | null>(null)

/** Opens the delete confirmation for the given contact. */
function openDelete(contact: LiveContact): void {
  contactToDelete.value = contact
  isDeleteOpen.value = true
}

/** Removes the pending contact and reports the outcome. */
function confirmDelete(): void {
  const contact = contactToDelete.value
  if (!contact) {
    return
  }
  deleteMutation.mutate(contact.id, {
    onSuccess: () => {
      isDeleteOpen.value = false
      toasts.success(t('settings.liveContacts.delete.success'))
    },
    onError: () => toasts.error(t('settings.liveContacts.delete.error')),
  })
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex flex-col gap-1">
        <h1 class="text-page-title">{{ t('settings.liveContacts.title') }}</h1>
        <p class="text-body">{{ t('settings.liveContacts.subtitle') }}</p>
      </div>
      <Button class="w-full sm:w-auto" @click="isFormOpen = true">
        <Plus class="size-4" aria-hidden="true" />
        {{ t('settings.liveContacts.buttonAdd') }}
      </Button>
    </div>

    <ListPanel
      :is-loading="contactsQuery.isPending.value"
      :is-error="contactsQuery.isError.value"
      :is-empty="isEmpty"
      :show-header="!contactsQuery.isError.value"
      :error-title="t('settings.liveContacts.error.title')"
      :error-description="t('settings.liveContacts.error.description')"
      :retry-label="t('settings.liveContacts.error.retry')"
      @retry="contactsQuery.refetch()"
    >
      <template #header>
        <div class="flex items-center justify-between gap-3 px-4 py-3">
          <Skeleton v-if="contactsQuery.isPending.value" class="h-4 w-44" />
          <p v-else class="text-hint">
            {{ t('settings.liveContacts.count', { count: contacts.length }) }}
          </p>
        </div>
      </template>

      <template #empty>
        <EmptyState
          :title="t('settings.liveContacts.empty.title')"
          :description="t('settings.liveContacts.empty.description')"
        >
          <template #icon>
            <BellRing class="size-8" aria-hidden="true" />
          </template>
          <template #action>
            <Button @click="isFormOpen = true">
              <Plus class="size-4" aria-hidden="true" />
              {{ t('settings.liveContacts.buttonAdd') }}
            </Button>
          </template>
        </EmptyState>
      </template>

      <ul class="divide-y divide-border">
        <li v-for="contact in contacts" :key="contact.id">
          <LiveContactListItem :contact="contact" @delete="openDelete" />
        </li>
      </ul>
    </ListPanel>

    <LiveContactFormDialog
      v-model:open="isFormOpen"
      @success="(message) => toasts.success(message)"
      @error="(message) => toasts.error(message)"
    />

    <ConfirmDialog
      v-model:open="isDeleteOpen"
      :title="t('settings.liveContacts.delete.title')"
      :description="t('settings.liveContacts.delete.body')"
      :confirm-label="t('settings.liveContacts.delete.confirm')"
      :cancel-label="t('settings.liveContacts.delete.cancel')"
      :close-label="t('settings.liveContacts.delete.close')"
      :pending="deleteMutation.isPending.value"
      @confirm="confirmDelete"
    />
  </div>
</template>
