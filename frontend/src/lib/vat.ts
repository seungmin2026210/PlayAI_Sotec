// 등록/수정 폼 실시간 미리보기용 계산. 서버(services/calculation.py)와 규칙 동일.
// 기획서 5장 / TECH 08: 항목 합계 → 십만단위 절사 → 부가세 10%.
import type { ItemInput } from "../types";

const TRUNCATE_UNIT = 100_000;
const VAT_RATE = 0.1;

export interface Computed {
  rawTotal: number;
  supplyAmount: number;
  vatAmount: number;
  totalWithVat: number;
}

export function computePreview(items: ItemInput[]): Computed {
  const rawTotal = items.reduce(
    (sum, it) => sum + (Number(it.qty) || 0) * (Number(it.unit_price) || 0),
    0,
  );
  const supplyAmount =
    rawTotal > 0 ? Math.floor(rawTotal / TRUNCATE_UNIT) * TRUNCATE_UNIT : 0;
  const vatAmount = Math.round(supplyAmount * VAT_RATE);
  return {
    rawTotal,
    supplyAmount,
    vatAmount,
    totalWithVat: supplyAmount + vatAmount,
  };
}
