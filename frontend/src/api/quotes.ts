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

export function getQuote(id: string): Promise<Quote> {
  return apiGet<Quote>(`/api/quotes/${id}`);
}

export function createQuote(payload: QuotePayload): Promise<Quote> {
  return apiSend<Quote>("POST", "/api/quotes", payload);
}

export function updateQuote(id: string, payload: QuotePayload): Promise<Quote> {
  return apiSend<Quote>("PUT", `/api/quotes/${id}`, payload);
}

export function deleteQuote(id: string): Promise<MessageResponse> {
  return apiSend<MessageResponse>("DELETE", `/api/quotes/${id}`);
}

export function approveQuote(id: string): Promise<Quote> {
  return apiSend<Quote>("POST", `/api/quotes/${id}/approve`);
}

export function rejectQuote(id: string, reason: string): Promise<Quote> {
  return apiSend<Quote>("POST", `/api/quotes/${id}/reject`, { reason });
}

export function cancelQuote(id: string): Promise<Quote> {
  return apiSend<Quote>("POST", `/api/quotes/${id}/cancel`);
}

export function purchaseLockQuote(id: string): Promise<Quote> {
  return apiSend<Quote>("POST", `/api/quotes/${id}/purchase-lock`);
}

export function sendQuote(id: string): Promise<MessageResponse> {
  return apiSend<MessageResponse>("POST", `/api/quotes/${id}/send`);
}

export function downloadQuoteXlsx(id: string): Promise<void> {
  return apiDownload(`/api/quotes/${id}/export.xlsx`);
}

export function downloadQuotePdf(id: string): Promise<void> {
  return apiDownload(`/api/quotes/${id}/export.pdf`);
}

export function downloadListXlsx(filters: ListFilters): Promise<void> {
  const { page: _p, size: _s, ...rest } = filters;
  return apiDownload(`/api/quotes/export.xlsx${buildQuery(rest as Record<string, unknown>)}`);
}
