import { apiGet } from "./client";
import type { Meta } from "../types";

export function fetchMeta(): Promise<Meta> {
  return apiGet<Meta>("/api/meta");
}
