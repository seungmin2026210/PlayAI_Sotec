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
    onChange([...items, { name: "", qty: 1, unit_price: 0 }]);
  }
  function removeRow(idx: number) {
    onChange(items.filter((_, i) => i !== idx));
  }

  return (
    <table className="items-editor">
      <thead>
        <tr>
          <th style={{ width: "44%" }}>품목</th>
          <th style={{ width: "14%" }}>갯수</th>
          <th style={{ width: "20%" }}>단가(공급가액)</th>
          <th style={{ width: "18%" }}>금액</th>
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
                placeholder="예: SonarQube Enterprise 연간"
              />
            </td>
            <td>
              <input
                type="number"
                min={1}
                value={it.qty}
                onChange={(e) => update(idx, { qty: Number(e.target.value) })}
              />
            </td>
            <td>
              <input
                type="number"
                min={1}
                value={it.unit_price}
                onChange={(e) => update(idx, { unit_price: Number(e.target.value) })}
              />
            </td>
            <td className="num">
              {formatWon((Number(it.qty) || 0) * (Number(it.unit_price) || 0))}
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
