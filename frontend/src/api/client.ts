import type { Policy, PolicyDetail, PipelineStatus } from "../types";

const BASE = "/api";

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function getPolicies(): Promise<Policy[]> {
  return fetchJSON<Policy[]>(`${BASE}/policies`);
}

export async function getPolicy(id: number): Promise<PolicyDetail> {
  return fetchJSON<PolicyDetail>(`${BASE}/policies/${id}`);
}

export async function runDiscover(): Promise<PipelineStatus> {
  return fetchJSON<PipelineStatus>(`${BASE}/pipeline/discover`, {
    method: "POST",
  });
}

export async function runDownload(): Promise<PipelineStatus> {
  return fetchJSON<PipelineStatus>(`${BASE}/pipeline/download`, {
    method: "POST",
  });
}

export async function runStructure(): Promise<PipelineStatus> {
  return fetchJSON<PipelineStatus>(`${BASE}/pipeline/structure`, {
    method: "POST",
  });
}
