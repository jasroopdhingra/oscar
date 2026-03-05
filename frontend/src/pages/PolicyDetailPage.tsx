import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import type { PolicyDetail } from "../types";
import { getPolicy } from "../api/client";
import CriteriaTree from "../components/CriteriaTree";

export default function PolicyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [policy, setPolicy] = useState<PolicyDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getPolicy(Number(id))
      .then(setPolicy)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading policy...</div>
      </div>
    );
  }

  if (error || !policy) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error || "Policy not found"}
      </div>
    );
  }

  const structured = policy.structured_policies.find(
    (sp) => sp.structured_json && !sp.validation_error
  );

  return (
    <div>
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        ← Back to policies
      </Link>

      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h1 className="text-xl font-bold text-gray-900 mb-3">{policy.title}</h1>

        <div className="flex flex-wrap gap-4 text-sm">
          <a
            href={policy.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 underline"
          >
            View PDF
          </a>
          <a
            href={policy.source_page_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 underline"
          >
            Source Page
          </a>
          <span className="text-gray-400">
            Discovered: {new Date(policy.discovered_at).toLocaleDateString()}
          </span>
        </div>

        {policy.downloads.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
              Download Status
            </h3>
            {policy.downloads.map((dl) => (
              <div key={dl.id} className="flex items-center gap-3 text-sm">
                {dl.error ? (
                  <span className="text-red-600">Failed: {dl.error}</span>
                ) : (
                  <span className="text-green-600">
                    Downloaded (HTTP {dl.http_status})
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {structured?.structured_json ? (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-900">
              Criteria Tree: {structured.structured_json.title}
            </h2>
            {structured.llm_metadata && (
              <span className="text-xs text-gray-400">
                Model: {String(structured.llm_metadata.model || "unknown")}
              </span>
            )}
          </div>
          <CriteriaTree root={structured.structured_json.rules} />
        </div>
      ) : (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-8 text-center text-gray-400">
          No structured criteria tree available for this policy.
          {policy.structured_policies.some((sp) => sp.validation_error) && (
            <p className="mt-2 text-sm text-red-400">
              Structuring was attempted but failed validation.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
