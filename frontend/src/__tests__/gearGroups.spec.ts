import { describe, expect, it } from 'vitest'

import type { Gear } from '@/features/gears/types'

import { GEAR_TYPE } from '@/features/gears/utils/gearType'
import { groupGearsByType } from '@/features/gears/utils/gearGroups'

const gear = (id: number, gearType: number) => ({ id, gearType, nickname: `gear ${id}` }) as Gear

describe('groupGearsByType', () => {
  const gears = [
    gear(1, GEAR_TYPE.SHOES),
    gear(2, GEAR_TYPE.BICYCLE),
    gear(3, GEAR_TYPE.SHOES),
    gear(4, GEAR_TYPE.SKIS),
  ]

  it('groups gears by type and keeps their original order inside a group', () => {
    const groups = groupGearsByType(gears, null)

    expect(groups.map((group) => group.gearType)).toEqual([
      GEAR_TYPE.BICYCLE,
      GEAR_TYPE.SHOES,
      GEAR_TYPE.SKIS,
    ])
    expect(groups[1]?.gears.map((g) => g.id)).toEqual([1, 3])
  })

  it('lists the preferred type first and the rest in ascending type order', () => {
    const groups = groupGearsByType(gears, GEAR_TYPE.SKIS)

    expect(groups.map((group) => group.gearType)).toEqual([
      GEAR_TYPE.SKIS,
      GEAR_TYPE.BICYCLE,
      GEAR_TYPE.SHOES,
    ])
  })

  it('ignores a preferred type the user has no gear for', () => {
    const groups = groupGearsByType(gears, GEAR_TYPE.WETSUIT)

    expect(groups.map((group) => group.gearType)).toEqual([
      GEAR_TYPE.BICYCLE,
      GEAR_TYPE.SHOES,
      GEAR_TYPE.SKIS,
    ])
  })

  it('returns no groups for no gears', () => {
    expect(groupGearsByType([], GEAR_TYPE.SHOES)).toEqual([])
  })
})
