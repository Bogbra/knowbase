/**
 * Typed API client — generated structure matches OpenAPI schema from backend.
 * Base URL configured via NEXT_PUBLIC_API_URL env var.
 */

const BASE_URL = process.env["NEXT_PUBLIC_API_URL"] ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init: RequestInit & { token?: string } = {}): Promise<T> {
  const { token, ...fetchInit } = init;
  const headers = new Headers(fetchInit.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE_URL}${path}`, { ...fetchInit, headers });

  if (!res.ok) {
    let code = "unknown_error";
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { code?: string; detail?: string; title?: string };
      code = body.code ?? code;
      detail = body.detail ?? body.title ?? detail;
    } catch {
      // response body not JSON — keep defaults
    }
    throw new ApiError(res.status, code, detail);
  }

  return res.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string, token?: string) => request<T>(path, { method: "GET", token }),
  post: <T>(path: string, body: unknown, token?: string) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body), token }),
  put: <T>(path: string, body: unknown, token?: string) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body), token }),
  patch: <T>(path: string, body: unknown, token?: string) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body), token }),
  delete: <T>(path: string, token?: string) => request<T>(path, { method: "DELETE", token }),
};

export async function parseErrorResponse(res: Response): Promise<ApiError> {
  let code = "unknown_error";
  let detail = res.statusText;
  try {
    const body = (await res.json()) as { code?: string; detail?: string; title?: string };
    code = body.code ?? code;
    detail = body.detail ?? body.title ?? detail;
  } catch {
    // response body not JSON — keep defaults
  }
  return new ApiError(res.status, code, detail);
}
