import { apiDownload, apiGet, apiSend, buildQuery } from "./client";
import type {
  Asset,
  AssetCategory,
  AssetFields,
  AssetListFilters,
  AssetListResponse,
  AssetUnit,
  AssignTarget,
} from "../types";

const enc = encodeURIComponent;

export function listAssets(f: AssetListFilters): Promise<AssetListResponse> {
  return apiGet(`/api/assets${buildQuery(f as unknown as Record<string, unknown>)}`);
}

export function downloadAssetList(f: AssetListFilters): Promise<void> {
  const { page: _p, size: _s, ...rest } = f;
  return apiDownload(`/api/assets/export.xlsx${buildQuery(rest as unknown as Record<string, unknown>)}`);
}

export function getAsset(assetNo: string): Promise<Asset> {
  return apiGet(`/api/assets/${enc(assetNo)}`);
}

export function createAssets(
  category: AssetCategory,
  quantity: number,
  fields: AssetFields,
): Promise<{ asset_nos: string[] }> {
  return apiSend("POST", "/api/assets", { ...fields, category, quantity });
}

export function importAssets(
  unitNo: string,
  quantity: number,
  fields: AssetFields,
): Promise<{ asset_nos: string[] }> {
  return apiSend("POST", "/api/assets/import", { ...fields, unit_no: unitNo, quantity });
}

export function cancelImport(unitNo: string): Promise<{ asset_nos: string[] }> {
  return apiSend("POST", "/api/assets/import/cancel", { unit_no: unitNo });
}

export function listImportable(category: AssetCategory): Promise<AssetUnit[]> {
  return apiGet(`/api/assets/importable${buildQuery({ category })}`);
}

export function updateAsset(assetNo: string, fields: Partial<AssetFields>): Promise<Asset> {
  return apiSend("PATCH", `/api/assets/${enc(assetNo)}`, fields);
}

export function deletePassword(assetNo: string): Promise<Asset> {
  return apiSend("DELETE", `/api/assets/${enc(assetNo)}/password`);
}

export function revealPassword(assetNo: string, action: "REVEAL" | "COPY"): Promise<{ password: string }> {
  return apiSend("POST", `/api/assets/${enc(assetNo)}/password/reveal`, { action });
}

export function disposeAsset(assetNo: string): Promise<Asset> {
  return apiSend("POST", `/api/assets/${enc(assetNo)}/dispose`);
}

export function deleteAsset(assetNo: string, reason: string): Promise<Asset> {
  return apiSend("POST", `/api/assets/${enc(assetNo)}/delete`, { reason });
}

export function assignAsset(assetNo: string, t: AssignTarget, startDate: string, note: string): Promise<Asset> {
  return apiSend("POST", `/api/assets/${enc(assetNo)}/assign`, { ...t, start_date: startDate, note });
}

export function returnAsset(assetNo: string, endDate: string, note: string): Promise<Asset> {
  return apiSend("POST", `/api/assets/${enc(assetNo)}/return`, { end_date: endDate, note });
}

export function transferAsset(assetNo: string, t: AssignTarget, date: string, note: string): Promise<Asset> {
  return apiSend("POST", `/api/assets/${enc(assetNo)}/transfer`, { ...t, date, note });
}

export function cancelAssignment(assetNo: string): Promise<Asset> {
  return apiSend("POST", `/api/assets/${enc(assetNo)}/assignment/cancel`);
}

export function editAssignment(
  id: string,
  patch: { start_date?: string; end_date?: string; note?: string | null },
): Promise<Asset> {
  return apiSend("PATCH", `/api/asset-assignments/${enc(id)}`, patch);
}

export function renewAssets(body: {
  asset_nos: string[];
  new_valid_to: string;
  new_valid_from: string | null;
  unit_no: string | null;
}): Promise<{ asset_nos: string[] }> {
  return apiSend("POST", "/api/assets/renew", body);
}
