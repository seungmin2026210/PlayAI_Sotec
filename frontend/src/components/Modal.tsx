import type { ReactNode } from "react";

/** 간단한 모달 — 폼 제출은 children 안의 form 이 처리한다. `wide` = 표가 들어가는 넓은 모달. */
export function Modal({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className={wide ? "card modal modal-wide" : "card modal"}
        role="dialog"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <h2>{title}</h2>
          <button type="button" className="ghost" onClick={onClose} aria-label="닫기">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
