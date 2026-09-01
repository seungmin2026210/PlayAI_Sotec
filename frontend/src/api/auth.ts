import { apiGet, apiSend } from "./client";
import type { User } from "../types";

export interface LoginResult {
  token: string;
  user: User;
}

export function login(username: string, password: string): Promise<LoginResult> {
  return apiSend<LoginResult>("POST", "/api/auth/login", { username, password });
}

export function fetchMe(): Promise<User> {
  return apiGet<User>("/api/auth/me");
}
