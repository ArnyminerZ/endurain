<script setup lang="ts">
import { computed } from 'vue'

import { cn } from '@/lib/utils'

interface Props {
  /** Bars to light up, 0 up to `max`. */
  level: number
  /** Total number of bars drawn. */
  max?: number
  /** Accessible description, e.g. "Phone signal: 3 of 4 bars". */
  label: string
  /** Colour of the lit bars. */
  tone?: 'ink' | 'effort' | 'hr'
}

const props = withDefaults(defineProps<Props>(), { max: 4, tone: 'ink' })

const bars = computed(() =>
  Array.from({ length: props.max }, (_, index) => ({
    index,
    lit: index < props.level,
    // Each bar is taller than the last, like a phone's signal icon.
    height: `${((index + 1) / props.max) * 100}%`,
  })),
)

const LIT_CLASS = { ink: 'bg-foreground', effort: 'bg-effort', hr: 'bg-hr' } as const
</script>

<template>
  <span
    role="img"
    :aria-label="label"
    class="inline-flex h-5 items-end gap-0.5"
    data-slot="signal-bars"
  >
    <span
      v-for="bar in bars"
      :key="bar.index"
      :class="cn('w-1.5 rounded-sm', bar.lit ? LIT_CLASS[tone] : 'bg-muted-foreground/30')"
      :style="{ height: bar.height }"
    />
  </span>
</template>
