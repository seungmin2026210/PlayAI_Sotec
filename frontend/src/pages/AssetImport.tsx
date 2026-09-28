import { useEffect, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { listImportable } from "../api/assets";
import { ApiError } from "../api/client";
import { useToast } from "../components/Toast";
import { CATEGORY_LABEL, categoryPath, slugToCategory } from "../components/AssetTabs";
import { formatWon } from "../lib/money";
import type { AssetUnit } from "../types";

/** 구매에서 가져오기 1단계: 아직 가져오지 않은·갱신에 안 쓰인·폐기 안 된 구매 유닛 선택(재판매품 포함 전부). */
export function AssetImport() {
  const { category: slug } = useParams();
  const category = slugToCategory(slug);
  const navigate = useNavigate();
  const toast = useToast();
  const [units, setUnits] = useState<AssetUnit[] | null>(null);

  useEffect(() => {
    if (!category) return;
    listImportable(category)
      .then(setUnits)
      .catch((err) => {
        toast.show(err instanceof ApiError ? err.message : "구매 기록을 불러오지 못했습니다.", "error");
        setUnits([]);
      });
  }, [category, toast]);

  if (!category) return <Navigate to="/assets/sw" replace />;

  return (
    <div className="page page-full">
      <div className="page-head">
        <div>
          <h1>구매에서 가져오기 · {CATEGORY_LABEL[category]}</h1>
          <p className="muted">
            자산으로 관리할 구매 기록을 고르세요. 고객사 대리구매(재판매)품은 가져오지 않으면 됩니다. 한 구매
            기록은 한 번만 가져올 수 있습니다.
          </p>
        </div>
        <button className="ghost" onClick={() => navigate(categoryPath(category))}>
          목록으로
        </button>
      </div>

      <div className="card">
        <table className="list-table">
          <thead>
            <tr>
              <th>구매 번호</th>
              <th>상품</th>
              <th>구매일</th>
              <th>구매처</th>
              <th className="num">금액</th>
              <th>만료일</th>
              <th>그룹</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {units === null && (
              <tr>
                <td colSpan={8} className="empty">
                  불러오는 중…
                </td>
              </tr>
            )}
            {units?.length === 0 && (
              <tr>
                <td colSpan={8} className="empty">
                  가져올 수 있는 구매 기록이 없습니다.
                </td>
              </tr>
            )}
            {units?.map((u) => (
              <tr key={u.unit_no}>
                <td>{u.unit_no}</td>
                <td>{u.product_name}</td>
                <td>{u.purchase_date}</td>
                <td>{u.purchased_from ?? "-"}</td>
                <td className="num">{formatWon(u.price)}</td>
                <td>{u.expire_date ?? "무기한"}</td>
                <td>{u.group_name}</td>
                <td>
                  <button
                    className="primary"
                    onClick={() =>
                      navigate(`${categoryPath(category)}/new?unit=${encodeURIComponent(u.unit_no)}`, { state: { unit: u } })
                    }
                  >
                    가져오기
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
