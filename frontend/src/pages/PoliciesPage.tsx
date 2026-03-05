import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Policy } from "../types";
import { getPolicies } from "../api/client";

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "structured" | "unstructured">("all");

  useEffect(() => {
    getPolicies()
      .then(setPolicies)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const filtered = policies.filter((p) => {
    if (filter === "structured") return p.has_structured_tree;
    if (filter === "unstructured") return !p.has_structured_tree;
    return true;
  });

  const structuredCount = policies.filter((p) => p.has_structured_tree).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading policies...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        Error: {error}
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Oscar Medical Guidelines
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {policies.length} policies discovered · {structuredCount} structured
          </p>
        </div>
        <div className="flex gap-2">
          {(["all", "structured", "unstructured"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                filter === f
                  ? "bg-gray-900 text-white border-gray-900"
                  : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
              }`}
            >
              {f === "all"
                ? `All (${policies.length})`
                : f === "structured"
                ? `Structured (${structuredCount})`
                : `Unstructured (${policies.length - structuredCount})`}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                Policy Title
              </th>
              <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider w-32">
                Download
              </th>
              <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider w-32">
                Structured
              </th>
              <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider w-24">
                PDF
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map((policy) => (
              <tr
                key={policy.id}
                className="hover:bg-gray-50 transition-colors"
              >
                <td className="px-4 py-3">
                  <Link
                    to={`/policies/${policy.id}`}
                    className="text-sm font-medium text-gray-900 hover:text-blue-600 transition-colors"
                  >
                    {policy.title}
                  </Link>
                </td>
                <td className="px-4 py-3 text-center">
                  {policy.download_status === "success" && (
                    <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700">
                      Downloaded
                    </span>
                  )}
                  {policy.download_status === "failed" && (
                    <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700">
                      Failed
                    </span>
                  )}
                  {!policy.download_status && (
                    <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-500">
                      Pending
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  {policy.has_structured_tree ? (
                    <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700">
                      Tree Ready
                    </span>
                  ) : (
                    <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-500">
                      —
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  <a
                    href={policy.pdf_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-500 hover:text-blue-700 text-sm"
                  >
                    View
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            No policies found. Run the pipeline first.
          </div>
        )}
      </div>
    </div>
  );
}
