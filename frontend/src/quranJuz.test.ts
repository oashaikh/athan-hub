import { describe, expect, it } from 'vitest'
import { JUZ_BOUNDARIES, groupSurahsByJuz } from './quranJuz'

describe('groupSurahsByJuz', () => {
  it('has 30 juz boundaries', () => {
    expect(JUZ_BOUNDARIES).toHaveLength(30)
  })

  it('places Al-Fatihah (surah 1) in Juz 1', () => {
    const groups = groupSurahsByJuz([{ id: 1 }])
    expect(groups).toEqual([{ juz: 1, surahs: [{ id: 1 }] }])
  })

  it('places Al-Baqarah (surah 2) in Juz 1, not its own group', () => {
    const groups = groupSurahsByJuz([{ id: 1 }, { id: 2 }])
    expect(groups).toHaveLength(1)
    expect(groups[0].juz).toBe(1)
    expect(groups[0].surahs.map(s => s.id)).toEqual([1, 2])
  })

  it('places An-Nas (surah 114) in Juz 30', () => {
    const groups = groupSurahsByJuz([{ id: 114 }])
    expect(groups).toEqual([{ juz: 30, surahs: [{ id: 114 }] }])
  })

  it('includes every input surah exactly once across all groups', () => {
    const surahs = Array.from({ length: 114 }, (_, i) => ({ id: i + 1 }))
    const groups = groupSurahsByJuz(surahs)
    const seen = groups.flatMap(g => g.surahs.map(s => s.id))
    expect(seen).toHaveLength(114)
    expect(new Set(seen).size).toBe(114)
  })
})
