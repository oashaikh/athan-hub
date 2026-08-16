export interface JuzBoundary {
  juz: number
  surahId: number
  ayah: number
}

export interface JuzGroup<T extends { id: number }> {
  juz: number
  surahs: T[]
}

// Standard 30-Juz (Para) division: surah/ayah where each Juz begins.
export const JUZ_BOUNDARIES: JuzBoundary[] = [
  { juz: 1, surahId: 1, ayah: 1 },
  { juz: 2, surahId: 2, ayah: 142 },
  { juz: 3, surahId: 2, ayah: 253 },
  { juz: 4, surahId: 3, ayah: 92 },
  { juz: 5, surahId: 4, ayah: 24 },
  { juz: 6, surahId: 4, ayah: 148 },
  { juz: 7, surahId: 5, ayah: 82 },
  { juz: 8, surahId: 6, ayah: 111 },
  { juz: 9, surahId: 7, ayah: 88 },
  { juz: 10, surahId: 8, ayah: 41 },
  { juz: 11, surahId: 9, ayah: 93 },
  { juz: 12, surahId: 11, ayah: 6 },
  { juz: 13, surahId: 12, ayah: 53 },
  { juz: 14, surahId: 15, ayah: 1 },
  { juz: 15, surahId: 17, ayah: 1 },
  { juz: 16, surahId: 18, ayah: 75 },
  { juz: 17, surahId: 21, ayah: 1 },
  { juz: 18, surahId: 23, ayah: 1 },
  { juz: 19, surahId: 25, ayah: 21 },
  { juz: 20, surahId: 27, ayah: 56 },
  { juz: 21, surahId: 29, ayah: 46 },
  { juz: 22, surahId: 33, ayah: 31 },
  { juz: 23, surahId: 36, ayah: 28 },
  { juz: 24, surahId: 39, ayah: 32 },
  { juz: 25, surahId: 41, ayah: 47 },
  { juz: 26, surahId: 46, ayah: 1 },
  { juz: 27, surahId: 51, ayah: 31 },
  { juz: 28, surahId: 58, ayah: 1 },
  { juz: 29, surahId: 67, ayah: 1 },
  { juz: 30, surahId: 78, ayah: 1 },
]

function juzForSurah(surahId: number): number {
  // A surah is grouped under the Juz containing its first ayah (ayah 1), so a
  // boundary only applies once the surah it names has itself begun.
  let juz = 1
  for (const boundary of JUZ_BOUNDARIES) {
    if (boundary.surahId > surahId) break
    if (boundary.surahId === surahId && boundary.ayah > 1) break
    juz = boundary.juz
  }
  return juz
}

export function groupSurahsByJuz<T extends { id: number }>(surahs: T[]): JuzGroup<T>[] {
  const byJuz = new Map<number, T[]>()
  for (const surah of surahs) {
    const juz = juzForSurah(surah.id)
    const bucket = byJuz.get(juz)
    if (bucket) bucket.push(surah)
    else byJuz.set(juz, [surah])
  }
  return [...byJuz.entries()]
    .sort(([a], [b]) => a - b)
    .map(([juz, group]) => ({ juz, surahs: group }))
}
