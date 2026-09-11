import type { MasteryClassification } from "@/lib/act/types";

const labels: Record<MasteryClassification, string> = {
  strong_evidence_of_mastery: "Strong evidence of mastery",
  likely_mastered: "Likely mastered",
  developing: "Developing",
  likely_weak: "Likely weak",
  strong_evidence_of_weakness: "Strong evidence of weakness",
  insufficient_evidence: "More evidence needed",
};

export function StatusLabel({ classification }: { classification: MasteryClassification }) {
  const attention = classification.includes("weak") || classification === "insufficient_evidence";
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
        attention ? "bg-amber-100 text-amber-900" : "bg-emerald-100 text-emerald-900"
      }`}
    >
      {labels[classification]}
    </span>
  );
}
