import { apiDownload, apiGet, apiSend, buildQuery } from "./client";
import type {
  ListFilters,
  MessageResponse,
  Quote,
  QuoteListResponse,
  QuotePayload,
} from "../types";

export function listQuotes(filters: ListFilters): Promise<QuoteListResponse> {
  return apiGet<QuoteListResponse>(`/api/quotes${buildQuery(filters as Record<string, unknown>)}`);
}

export function getQuote(id: number): Promise<Quote> {
  return apiGet<Quote>(`/api/quotes/${id}`);
}

export function createQuote(payload: QuotePayload): Promise<Quote> {
  return apiSend<Quote>("POST", "/api/quotes", payload);
}

export function updateQuote(id: number, payload: QuotePayload): Promise<Quote> {
  return apiSend<Quote>("PUT", `/api/quotes/${id}`, payload);
}

export function deleteQuote(id: number): Promise<MessageResponse> {
  return apiSend<MessageResponse>("DELETE", `/api/quotes/${id}`);
}

export function approveQuote(id: number): Promise<Quote> {
  return apiSend<Quote>("POST", `/api/quotes/${id}/approve`);
}

export function rejectQuote(id: number, reason: string): Promise<Quote> {
  return apiSend<Quote>("POST", `/api/quotes/${id}/reject`, { reason });
}

export function cancelQuote(id: number): Promise<Quote> {
  return apiSend<Quote>("POST", `/api/quotes/${id}/cancel`);
}

export function purchaseLockQuote(id: number): Promise<Quote> {
  return apiSend<Quote>("POST", `/api/quotes/${id}/purchase-lock`);
}

export function sendQuote(id: number): Promise<MessageResponse> {
  return apiSend<MessageResponse>("POST", `/api/quotes/${id}/send`);
}

export function downloadQuoteXlsx(id: number): Promise<void> {
  return apiDownload(`/api/quotes/${id}/export.xlsx`);
}

export function downloadQuotePdf(id: number): Promise<void> {
  return apiDownload(`/api/quotes/${id}/export.pdf`);
}

export function downloadListXlsx(filters: ListFilters): Promise<void> {
  const { page: _p, size: _s, ...rest } = filters;
  return apiDownload(`/api/quotes/export.xlsx${buildQuery(rest as Record<string, unknown>)}`);
}
