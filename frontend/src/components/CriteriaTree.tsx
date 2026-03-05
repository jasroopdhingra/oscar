import { useState } from "react";
import type { RuleNode } from "../types";

function OperatorBadge({ operator }: { operator: "AND" | "OR" }) {
  const colors =
    operator === "AND"
      ? "bg-blue-100 text-blue-800 border-blue-300"
      : "bg-amber-100 text-amber-800 border-amber-300";
  return (
    <span
      className={`inline-block px-2 py-0.5 text-xs font-bold rounded border ${colors} mr-2`}
    >
      {operator}
    </span>
  );
}

function TreeNode({ node, depth = 0 }: { node: RuleNode; depth?: number }) {
  const hasChildren = node.rules && node.rules.length > 0;
  const [expanded, setExpanded] = useState(depth < 2);

  return (
    <div className={`${depth > 0 ? "ml-6 border-l-2 border-gray-200 pl-4" : ""}`}>
      <div
        className={`flex items-start gap-2 py-2 ${hasChildren ? "cursor-pointer" : ""}`}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {hasChildren && (
          <span className="mt-0.5 text-gray-400 select-none w-4 text-center flex-shrink-0">
            {expanded ? "▼" : "▶"}
          </span>
        )}
        {!hasChildren && (
          <span className="mt-1 w-2 h-2 rounded-full bg-gray-400 flex-shrink-0 ml-1" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-gray-400 font-mono">{node.rule_id}</span>
            {node.operator && <OperatorBadge operator={node.operator} />}
          </div>
          <p className="text-sm text-gray-800 mt-0.5 leading-relaxed">
            {node.rule_text}
          </p>
        </div>
      </div>

      {hasChildren && expanded && (
        <div className="mt-1">
          {node.rules!.map((child) => (
            <TreeNode key={child.rule_id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function CriteriaTree({ root }: { root: RuleNode }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <TreeNode node={root} depth={0} />
    </div>
  );
}
