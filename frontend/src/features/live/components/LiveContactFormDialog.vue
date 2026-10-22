<script setup lang="ts">
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { FormDialog } from '@/components/ui/form-dialog'
import { FormField } from '@/components/ui/form-field'
import { Input } from '@/components/ui/input'
import { useForm } from '@/composables/useForm'
import { useCreateLiveContactMutation } from '@/features/live/composables/useLiveContacts'
import { HttpError } from '@/services/http'
import { compose, email, maxLength, required } from '@/utils/validators'

const open = defineModel<boolean>('open', { required: true })

const emit = defineEmits<{
  success: [message: string]
  error: [message: string]
}>()

const { t } = useI18n()
const createMutation = useCreateLiveContactMutation()

/** Form shape. */
interface ContactFormValues {
  name: string
  email: string
}

const NAME_MAX = 100
const EMAIL_MAX = 255

/**
 * Adds the contact, emitting the outcome to the parent and closing on success.
 * Known backend refusals (duplicate email, full list) become specific messages
 * and keep the dialog open for correction.
 *
 * @param values - The validated form values.
 */
async function submitForm(values: ContactFormValues): Promise<void> {
  try {
    await createMutation.mutateAsync({ name: values.name, email: values.email })
    emit('success', t('settings.liveContacts.form.createSuccess'))
    open.value = false
  } catch (error) {
    if (error instanceof HttpError && error.status === 409) {
      emit('error', t('settings.liveContacts.form.duplicate'))
    } else if (error instanceof HttpError && error.status === 400) {
      emit('error', t('settings.liveContacts.form.limitReached'))
    } else {
      emit('error', t('settings.liveContacts.form.saveError'))
    }
  }
}

const { values, errors, isValid, isSubmitting, handleSubmit, handleBlur, reset } =
  useForm<ContactFormValues>({
    initialValues: { name: '', email: '' },
    validators: {
      name: compose(
        required<string>(t('settings.liveContacts.form.nameRequired')),
        maxLength(NAME_MAX, t('settings.liveContacts.form.nameTooLong')),
      ),
      email: compose(
        required<string>(t('settings.liveContacts.form.emailRequired')),
        email(t('settings.liveContacts.form.emailInvalid')),
        maxLength(EMAIL_MAX, t('settings.liveContacts.form.emailTooLong')),
      ),
    },
    onSubmit: submitForm,
  })

// Start from a blank form each time the dialog opens.
watch(open, (isOpen) => {
  if (isOpen) {
    reset()
  }
})
</script>

<template>
  <FormDialog
    v-model:open="open"
    :title="t('settings.liveContacts.form.addTitle')"
    :description="t('settings.liveContacts.form.description')"
    :submit-label="t('settings.liveContacts.form.create')"
    :cancel-label="t('settings.liveContacts.form.cancel')"
    :close-label="t('settings.liveContacts.form.close')"
    :submitting="isSubmitting"
    :can-submit="isValid"
    @submit="handleSubmit"
  >
    <div class="grid grid-cols-1 gap-2">
      <FormField :label="t('settings.liveContacts.form.name')" :error="errors.name" required>
        <template #default="{ fieldId, describedBy, invalid }">
          <Input
            :id="fieldId"
            v-model="values.name"
            :aria-describedby="describedBy"
            :aria-invalid="invalid"
            name="name"
            autocomplete="off"
            :maxlength="NAME_MAX"
            :disabled="isSubmitting"
            @blur="handleBlur('name')"
          />
        </template>
      </FormField>

      <FormField :label="t('settings.liveContacts.form.email')" :error="errors.email" required>
        <template #default="{ fieldId, describedBy, invalid }">
          <Input
            :id="fieldId"
            v-model="values.email"
            :aria-describedby="describedBy"
            :aria-invalid="invalid"
            name="email"
            type="email"
            autocomplete="off"
            :maxlength="EMAIL_MAX"
            :disabled="isSubmitting"
            @blur="handleBlur('email')"
          />
        </template>
      </FormField>
    </div>
  </FormDialog>
</template>
