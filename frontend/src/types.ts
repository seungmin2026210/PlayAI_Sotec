export type Role = "SUPER_ADMIN" | "GROUP_MANAGER";

export type QuoteStatus = "SUBMITTED" | "APPROVED" | "REJECTED" | "CANCELLED" | "CLOSED";

export interface User {
  username: string;
  role: Role;
  group_code: string | null;
  display_name: string;
}

export interface Group {
  code: string;
  name: string;
}

export interface Meta {
  groups: Group[];
  company: Record<string, string>;
  vat_rate: number;
  truncate_unit: number;
  statuses: { code: QuoteStatus; label: string }[];
  asset_categories: { code: AssetCategory; label: string }[];
  asset_subcategories: Record<AssetCategory, { code: string; label: string }[]>;
  asset_statuses: { code: AssetStatus; label: string }[];
}

export interface QuoteItem {
  line_no: number;
  name: string;
  qty: number;
  unit_price: number;
  line_amount: number;
  period_start: string | null;
  period_end: string | null;
}

export interface Quote {
  id: string; // Firestore 문서ID == mgmt_no
  mgmt_no: string;
  seq_year: number;
  group_code: string;
  group_name: string;
  seq_no: number;
  title: string;
  issue_date: string;
  issuer_name: string;
  customer_name: string;
  customer_department: string | null;
  customer_contact_name: string | null;
  customer_contact_phone: string | null;
  customer_cc: string | null;
  vat_included: boolean;
  supply_amount: number;
  vat_amount: number;
  total_with_vat: number;
  items_raw_total: number;
  status: QuoteStatus;
  status_label: string;
  reject_reason: string | null;
  purchase_locked: boolean;
  read_only: boolean;
  created_by: string;
  created_at: string;
  updated_at: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  cancelled_at: string | null;
  locked_at: string | null;
  closed_at: string | null;
  company: Record<string, string>;
  items: QuoteItem[];
}

export interface QuoteListItem {
  id: string; // Firestore 문서ID == mgmt_no
  mgmt_no: string;
  group_code: string;
  group_name: string;
  title: string;
  customer_name: string;
  issue_date: string;
  issuer_name: string;
  supply_amount: number;
  vat_amount: number;
  total_with_vat: number;
  vat_included: boolean;
  status: QuoteStatus;
  status_label: string;
  purchase_locked: boolean;
  created_at: string;
}

export interface QuoteListResponse {
  total: number;
  page: number;
  size: number;
  items: QuoteListItem[];
}

export interface ItemInput {
  name: string;
  qty: number;
  unit_price: number;
  period_start: string | null;
  period_end: string | null;
}

export interface QuotePayload {
  group_code: string;
  title: string;
  issue_date: string;
  issuer_name: string;
  customer_name: string;
  customer_department: string | null;
  customer_contact_name: string | null;
  customer_contact_phone: string | null;
  customer_cc: string | null;
  vat_included: boolean;
  items: ItemInput[];
}

export interface MessageResponse {
  message: string;
}

export interface ListFilters {
  mgmt_no?: string;
  title?: string;
  group_code?: string;
  status?: string;
  issue_date_from?: string;
  issue_date_to?: string;
  issuer_name?: string;
  page?: number;
  size?: number;
}

// --------------------------------------------------------------------------- PURCHASE-1
export type AssetCategory = "SW" | "HW" | "EDU";
export type AssetUnitStatus = "AVAILABLE" | "ASSIGNED" | "EXPIRED";
export type AssetUnitType = "KEY" | "ACCOUNT";

export interface AssetProduct {
  id: string;
  name: string;
  vendor: string | null;
  asset_category: AssetCategory;
  asset_category_label: string;
  is_active: boolean;
  created_at: string;
}

export interface AssetProductListResponse {
  items: AssetProduct[];
}

export interface AssetProductPayload {
  name: string;
  vendor: string | null;
  asset_category: AssetCategory;
}

export interface AssetProductPatchPayload {
  name?: string;
  vendor?: string | null;
  is_active?: boolean;
}

export interface AssetUnit {
  id: string; // == unit_no
  unit_no: string;
  product_id: string;
  product_name: string;
  asset_category: AssetCategory;
  asset_category_label: string;
  purchase_date: string;
  purchased_from: string | null;
  price: number;
  unit_type: AssetUnitType | null;
  unit_type_label: string | null;
  key_value: string | null;
  expire_date: string | null;
  status: AssetUnitStatus;
  status_label: string;
  source_quote_id: string | null;
  group_code: string;
  group_name: string;
  created_at: string;
  updated_at: string | null;
  retired_at: string | null;
  asset_link_kind: AssetLinkKind | null;
  asset_link_label: string | null;
  asset_nos: string[];
}

export interface AssetUnitListItem {
  id: string;
  unit_no: string;
  product_name: string;
  asset_category: AssetCategory;
  asset_category_label: string;
  purchase_date: string;
  price: number;
  status: AssetUnitStatus;
  status_label: string;
  group_code: string;
  group_name: string;
  asset_link_kind: AssetLinkKind | null;
  asset_link_label: string | null;
  asset_nos: string[];
}

export interface AssetUnitListResponse {
  total: number;
  page: number;
  size: number;
  items: AssetUnitListItem[];
}

export interface AssetUnitPayload {
  product_id: string;
  purchase_date: string;
  purchased_from: string | null;
  price: number;
  unit_type: AssetUnitType | null;
  key_value: string | null;
  expire_date: string | null;
  group_code: string;
  source_quote_id: string | null;
}

export interface AssetUnitPatchPayload {
  purchase_date?: string;
  purchased_from?: string | null;
  price?: number;
  unit_type?: AssetUnitType | null;
  key_value?: string | null;
  expire_date?: string | null;
  group_code?: string;
}

export interface AssetUnitListFilters {
  product_id?: string;
  status?: string;
  group_code?: string;
  page?: number;
  size?: number;
}

// --------------------------------------------------------------------------- ASSET-1
export type AssetStatus = "IDLE" | "IN_USE" | "DISPOSED";
export type AssetLinkKind = "IMPORTED" | "RENEWED";
export type ExpiryBadge = "EXPIRED" | "EXPIRING";

export interface AssetListItem {
  asset_no: string;
  category: AssetCategory;
  category_label: string;
  subcategory: string | null;
  subcategory_label: string | null;
  name: string;
  status: AssetStatus;
  status_label: string;
  group_code: string;
  group_name: string;
  scope_group_code: string;
  scope_group_name: string;
  current_member_id: string | null;
  current_member_name: string | null;
  current_shared_label: string | null;
  current_external_label: string | null;
  current_start_date: string | null;
  purchase_date: string | null;
  price: number | null;
  valid_from: string | null;
  valid_to: string | null;
  expiry_badge: ExpiryBadge | null;
  version: string | null;
  license_key: string | null;
  account_id: string | null;
  has_password: boolean;
  manufacturer: string | null;
  model: string | null;
  serial_no: string | null;
  mac_address: string | null;
  course_title: string | null;
  course_url: string | null;
  quote_no: string | null;
  contract_no: string | null;
  source_unit_no: string | null;
  purchased_from: string | null;
  note: string | null;
  disposed_reason: string | null;
  disposed_reason_label: string | null;
  read_only: boolean;
}

export interface AssetAssignment {
  id: string;
  asset_no: string;
  category: AssetCategory;
  asset_name: string;
  member_id: string | null;
  member_name: string | null;
  shared_label: string | null;
  external_label: string | null;
  start_date: string;
  end_date: string | null;
  note: string | null;
  created_by: string | null;
  updated_at: string | null;
  updated_by: string | null;
}

export interface AssetRenewal {
  id: string;
  prev_valid_to: string;
  new_valid_from: string | null;
  new_valid_to: string;
  unit_no: string | null;
  count: number;
  created_at: string | null;
  created_by: string | null;
}

export interface Asset extends AssetListItem {
  disposed_at: string | null;
  created_at: string | null;
  created_by: string | null;
  updated_at: string | null;
  updated_by: string | null;
  assignments: AssetAssignment[];
  renewals: AssetRenewal[];
}

export interface AssetListResponse {
  total: number;
  page: number;
  size: number;
  items: AssetListItem[];
}

export interface AssetListFilters {
  category: AssetCategory;
  subcategory?: string;
  member_id?: string;
  group?: string;
  status?: string;
  expiry?: string;
  year?: string;
  name?: string;
  valid_to?: string;
  q?: string;
  page?: number;
  size?: number;
}

/** 등록/수정 폼 값. password: 빈 값 = 변경 없음(D42). */
export interface AssetFields {
  subcategory: string | null;
  name: string;
  group_code: string;
  purchase_date: string | null;
  price: number | null;
  purchased_from: string | null;
  quote_no: string | null;
  contract_no: string | null;
  valid_from: string | null;
  valid_to: string | null;
  version: string | null;
  license_key: string | null;
  account_id: string | null;
  password: string | null;
  manufacturer: string | null;
  model: string | null;
  serial_no: string | null;
  mac_address: string | null;
  course_title: string | null;
  course_url: string | null;
  note: string | null;
}

export interface AssignTarget {
  member_id: string | null;
  shared_label: string | null;
  external_label: string | null;
}

export interface Member {
  employee_no: string;
  name: string;
  group_code: string;
  group_name: string;
  active: boolean;
  counts: Record<AssetCategory, number>;
  warning: string | null;
}

export interface MemberHistoryRow extends AssetAssignment {
  linkable: boolean;
}

export interface MemberDetail extends Member {
  assignments: MemberHistoryRow[];
}

export interface RenewalGroup {
  date: string;
  name: string;
  category: AssetCategory;
  count: number;
  asset_nos: string[];
}

export interface RenewalCalendar {
  items: RenewalGroup[];
  kpi: { expired: number; d30: number; d90: number };
}
