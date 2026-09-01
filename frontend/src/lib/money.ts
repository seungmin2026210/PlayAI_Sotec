// open-6 임시결정 격리 지점: 금액 표기 = 천단위 콤마 + '원'. 통화기호 미사용.
// 협의 후 표기 규칙이 바뀌면 이 파일만 수정한다.

export function formatWon(n: number): string {
  return `${Math.round(n).toLocaleString("ko-KR")}원`;
}

export function parseWon(s: string): number {
  const digits = s.replace(/[^0-9-]/g, "");
  const n = Number(digits);
  return Number.isFinite(n) ? n : 0;
}
