export type Role = "SUPER_ADMIN" | "GROUP_MANAGER";

export type QuoteStatus = "SUBMITTED" | "APPROVED" | "REJECTED" | "CANCELLED";

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
}

export interface QuoteItem {
  line_no: number;
  name: string;
  qty: number;
  unit_price: number;
  line_amount: number;
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
  customer_contact_name: string | null;
  customer_contact_phone: string | null;
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
}

export interface QuotePayload {
  group_code: string;
  title: string;
  issue_date: string;
  issuer_name: string;
  customer_name: string;
  customer_contact_name: string | null;
  customer_contact_phone: string | null;
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
