import { parseWon } from "../lib/money";

interface Props {
  value: number | null;
  onChange: (value: number) => void;
  placeholder?: string;
}

/** 금액 입력 전용 — 타이핑하는 동안 천단위 콤마를 실시간으로 보여준다(표시만 콤마, 값은 순수 숫자). */
export function MoneyInput({ value, onChange, placeholder }: Props) {
  const display = value ? value.toLocaleString("ko-KR") : "";
  return (
    <input
      inputMode="numeric"
      value={display}
      placeholder={placeholder}
      onChange={(e) => onChange(parseWon(e.target.value))}
    />
  );
}
