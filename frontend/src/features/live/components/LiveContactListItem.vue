<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Mail, Trash2 } from '@lucide/vue'

import type { LiveContact } from '@/features/live/types'

defineProps<{
  /** The contact to render. */
  contact: LiveContact
}>()

const emit = defineEmits<{
  delete: [contact: LiveContact]
}>()

const { t } = useI18n()
</script>

<template>
  <div class="flex items-center gap-3 px-4 py-3">
    <div
      class="flex size-10 shrink-0 items-center justify-center rounded-input bg-muted-foreground/15 text-muted-foreground"
    >
      <Mail class="size-5" aria-hidden="true" />
    </div>

    <div class="min-w-0 flex-1">
      <p class="truncate font-medium text-foreground">{{ contact.name }}</p>
      <p class="truncate text-hint">{{ contact.email }}</p>
    </div>

    <button
      type="button"
      class="inline-flex size-8 shrink-0 items-center justify-center rounded-input text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-destructive/30"
      :aria-label="t('settings.liveContacts.list.delete', { name: contact.name })"
      @click="emit('delete', contact)"
    >
      <Trash2 class="size-4" aria-hidden="true" />
    </button>
  </div>
</template>
