import type { ItemInput } from "../types";
import { formatWon } from "../lib/money";

interface Props {
  items: ItemInput[];
  onChange: (items: ItemInput[]) => void;
}

export function ItemsEditor({ items, onChange }: Props) {
  function update(idx: number, patch: Partial<ItemInput>) {
    onChange(items.map((it, i) => (i === idx ? { ...it, ...patch } : it)));
  }
  function addRow() {
    onChange([...items, { name: "", qty: 1, unit_price: 0, period_start: null, period_end: null }]);
  }
  function removeRow(idx: number) {
    onChange(items.filter((_, i) => i !== idx));
  }

  return (
    <table className="items-editor">
      <thead>
        <tr>
          <th style={{ width: "34%" }}>용역(계약)</th>
          <th style={{ width: "16%" }}>기간 시작</th>
          <th style={{ width: "16%" }}>기간 종료</th>
          <th style={{ width: "26%" }}>공급가액</th>
          <th style={{ width: "4%" }} />
        </tr>
      </thead>
      <tbody>
        {items.map((it, idx) => (
          <tr key={idx}>
            <td>
              <input
                value={it.name}
                onChange={(e) => update(idx, { name: e.target.value })}
                placeholder="예: 프론트엔드 개발"
              />
            </td>
            <td>
              <input
                type="date"
                value={it.period_start ?? ""}
                onChange={(e) => update(idx, { period_start: e.target.value || null })}
              />
            </td>
            <td>
              <input
                type="date"
                value={it.period_end ?? ""}
                onChange={(e) => update(idx, { period_end: e.target.value || null })}
              />
            </td>
            <td>
              <input
                type="number"
                min={1}
                value={it.unit_price}
                onChange={(e) => update(idx, { qty: 1, unit_price: Number(e.target.value) })}
              />
              <span className="num">{formatWon(Number(it.unit_price) || 0)}</span>
            </td>
            <td>
              <button
                type="button"
                className="link-danger"
                onClick={() => removeRow(idx)}
                disabled={items.length === 1}
                title={items.length === 1 ? "최소 1개 항목이 필요합니다" : "행 삭제"}
              >
                ✕
              </button>
            </td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <td colSpan={5}>
            <button type="button" onClick={addRow}>
              + 항목 추가
            </button>
          </td>
        </tr>
      </tfoot>
    </table>
  );
}
