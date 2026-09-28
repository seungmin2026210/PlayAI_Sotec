import { apiGet, buildQuery } from "./client";
import type { RenewalCalendar } from "../types";

export function fetchRenewals(from: string, to: string): Promise<RenewalCalendar> {
  return apiGet(`/api/dashboard/renewals${buildQuery({ from, to })}`);
}
