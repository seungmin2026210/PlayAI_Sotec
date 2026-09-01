const TOKEN_KEY = "quote_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void): void {
  onUnauthorized = fn;
}

async function raise(res: Response): Promise<never> {
  let code = "UNKNOWN";
  let message = `요청 실패 (${res.status})`;
  try {
    const body = await res.json();
    const d = body?.detail;
    if (d && typeof d === "object") {
      code = d.code ?? code;
      message = d.message ?? message;
    } else if (typeof d === "string") {
      message = d;
    }
  } catch {
    /* non-JSON */
  }
  if (res.status === 401 && onUnauthorized) onUnauthorized();
  throw new ApiError(res.status, code, message);
}

function headers(extra?: Record<string, string>): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json", ...extra };
  const t = getToken();
  if (t) h["Authorization"] = `Bearer ${t}`;
  return h;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: headers() });
  if (!res.ok) await raise(res);
  return res.json() as Promise<T>;
}

export async function apiSend<T>(
  method: "POST" | "PUT" | "DELETE",
  path: string,
  body?: unknown,
): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: headers(),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) await raise(res);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** 파일 다운로드 (엑셀/PDF). 서버가 에러를 주면 ApiError 로 변환. */
export async function apiDownload(path: string): Promise<void> {
  const res = await fetch(path, { headers: headers() });
  if (!res.ok) await raise(res);
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition") ?? "";
  const m = cd.match(/filename="?([^"]+)"?/);
  const filename = m ? m[1] : "download";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function buildQuery(params: Record<string, unknown>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    q.set(k, String(v));
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}
