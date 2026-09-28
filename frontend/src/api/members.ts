import { apiGet, apiSend } from "./client";
import type { Member, MemberDetail } from "../types";

export function listMembers(): Promise<{ items: Member[] }> {
  return apiGet("/api/members");
}

export function getMember(employeeNo: string): Promise<MemberDetail> {
  return apiGet(`/api/members/${encodeURIComponent(employeeNo)}`);
}

export function createMember(body: { employee_no: string; name: string; group_code: string }): Promise<Member> {
  return apiSend("POST", "/api/members", body);
}

export function patchMember(
  employeeNo: string,
  body: { name?: string; group_code?: string; active?: boolean },
): Promise<Member> {
  return apiSend("PATCH", `/api/members/${encodeURIComponent(employeeNo)}`, body);
}
