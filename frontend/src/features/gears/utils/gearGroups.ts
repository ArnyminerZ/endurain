import type { Gear, GearType } from '@/features/gears/types'
import { GEAR_TYPE_VALUES } from '@/features/gears/utils/gearType'

/**
 * A run of gears sharing one gear type, used to render grouped pickers.
 *
 * @property gearType - Gear type shared by the group.
 * @property gears - The gears of that type, in their original order.
 */
export interface GearGroup {
  gearType: GearType
  gears: Gear[]
}

/**
 * Splits gears into one group per gear type, dropping empty types. The
 * `preferredType` group (the family that suits the activity) comes first; the
 * rest follow in gear-type display order so the picker layout is stable.
 *
 * @param gears - The gears to group (any mix of types).
 * @param preferredType - Gear type to list first, or `null` for none.
 * @returns The non-empty groups, preferred type first.
 */
export function groupGearsByType(
  gears: readonly Gear[],
  preferredType: GearType | null,
): GearGroup[] {
  const byType = new Map<GearType, Gear[]>()
  for (const gear of gears) {
    const bucket = byType.get(gear.gearType)
    if (bucket) {
      bucket.push(gear)
    } else {
      byType.set(gear.gearType, [gear])
    }
  }

  const order = (type: GearType) => GEAR_TYPE_VALUES.indexOf(type)
  return [...byType.entries()]
    .map(([gearType, groupGears]) => ({ gearType, gears: groupGears }))
    .sort((a, b) => {
      if (a.gearType === preferredType) {
        return -1
      }
      if (b.gearType === preferredType) {
        return 1
      }
      return order(a.gearType) - order(b.gearType)
    })
}
