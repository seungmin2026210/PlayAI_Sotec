import { apiGet, apiSend, buildQuery } from "./client";
import type {
  AssetProduct,
  AssetProductListResponse,
  AssetProductPatchPayload,
  AssetProductPayload,
  AssetUnit,
  AssetUnitListFilters,
  AssetUnitListResponse,
  AssetUnitPayload,
} from "../types";

export function listAssetProducts(isActive?: boolean): Promise<AssetProductListResponse> {
  const q = isActive === undefined ? "" : buildQuery({ is_active: isActive });
  return apiGet<AssetProductListResponse>(`/api/asset-products${q}`);
}

export function createAssetProduct(payload: AssetProductPayload): Promise<AssetProduct> {
  return apiSend<AssetProduct>("POST", "/api/asset-products", payload);
}

export function patchAssetProduct(
  id: string,
  payload: AssetProductPatchPayload,
): Promise<AssetProduct> {
  return apiSend<AssetProduct>("PATCH", `/api/asset-products/${id}`, payload);
}

export function listAssetUnits(filters: AssetUnitListFilters): Promise<AssetUnitListResponse> {
  return apiGet<AssetUnitListResponse>(
    `/api/asset-units${buildQuery(filters as Record<string, unknown>)}`,
  );
}

export function getAssetUnit(unitNo: string): Promise<AssetUnit> {
  return apiGet<AssetUnit>(`/api/asset-units/${encodeURIComponent(unitNo)}`);
}

export function createAssetUnit(payload: AssetUnitPayload): Promise<AssetUnit> {
  return apiSend<AssetUnit>("POST", "/api/asset-units", payload);
}

export function retireAssetUnit(unitNo: string): Promise<AssetUnit> {
  return apiSend<AssetUnit>("POST", `/api/asset-units/${encodeURIComponent(unitNo)}/retire`);
}
