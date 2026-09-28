// ASSET-1 D45: "오늘"은 한국 시간 기준. 서버 asset_dates.today_kst() 와 같은 규칙(프론트 유일 계산처).
// 날짜 입력의 max(미래 날짜 선택 불가)와 기본값에 쓴다. 서버가 최종 검사한다.

export function todayKst(): string {
  return new Date(Date.now() + 9 * 3600_000).toISOString().slice(0, 10);
}

export function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** 두 ISO 날짜 사이 일수(b - a). */
export function daysBetween(a: string, b: string): number {
  return Math.round((Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / 86_400_000);
}
