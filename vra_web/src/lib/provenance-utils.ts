//vra_web/src/lib/provenance-utils.ts
import { ReactNode } from "react";

// Regex Patterns
// arXiv: 2310.12345 or 2310.12345v1
const ARXIV_REGEX = /\b\d{4}\.\d{4,5}(v\d+)?\b/i;
// simple DOI: 10.xxxx/yyyy
const DOI_REGEX = /\b10\.\d{4,9}\/[-._;()/:a-zA-Z0-9]+\b/i;
// Semantic Scholar: Enforce s2: prefix
const S2_REGEX = /\b(s2:)[0-9a-f]{40}\b/i;
// Generic URL Protocol
const URL_REGEX = /^https?:\/\//i;

export type SourceType =
    | "arXiv"
    | "DOI"
    | "SemanticScholar"
    | "URL"
    | "Unknown";

/**
 * Validates if a string looks like a supported Paper ID.
 */
export function isPaperId(str: string): boolean {
    if (!str) return false;
    const clean = str.trim();
    return (
        ARXIV_REGEX.test(clean) ||
        DOI_REGEX.test(clean) ||
        S2_REGEX.test(clean) ||
        URL_REGEX.test(clean)
    );
}

/**
 * Identifies the type of source based on the ID format.
 */
export function identifySourceType(id: string): SourceType {
    if (!id) return "Unknown";
    const clean = id.trim();
    if (ARXIV_REGEX.test(clean)) return "arXiv";
    if (DOI_REGEX.test(clean)) return "DOI";
    if (S2_REGEX.test(clean)) return "SemanticScholar";
    if (URL_REGEX.test(clean)) return "URL";
    return "Unknown";
}

/**
 * Generates a deterministic URL for the given Paper ID.
 */
export function getPaperUrl(id: string): string {
    const type = identifySourceType(id);
    const clean = id.trim();

    switch (type) {
        case "arXiv":
            // Extract actual ID if embedded in text
            const arxivMatch = clean.match(ARXIV_REGEX);
            return `https://arxiv.org/abs/${
                arxivMatch ? arxivMatch[0] : clean
            }`;
        case "DOI":
            // Extract DOI substring
            const doiMatch = clean.match(DOI_REGEX);
            return `https://doi.org/${doiMatch ? doiMatch[0] : clean}`;
        case "SemanticScholar":
            // Extract hash (remove s2: if present)
            const s2Match = clean.match(S2_REGEX);
            const fullS2 = s2Match ? s2Match[0] : clean;
            const hash = fullS2.replace(/^s2:/i, "");
            return `https://www.semanticscholar.org/paper/${hash}`;
        case "URL":
            return clean;
        default:
            // Fallback for search/google if unknown?
            // For now, assume it might be a partial ID or handle gracefully.
            return `https://scholar.google.com/scholar?q=${encodeURIComponent(
                clean
            )}`;
    }
}

/**
 * Recursively extracts all unique paper IDs from an evidence object/string/array.
 */
export function extractPaperIds(evidence: any): string[] {
    const ids = new Set<string>();

    const traverse = (obj: any) => {
        if (!obj) return;

        if (typeof obj === "string") {
            // Check if strict ID
            if (isPaperId(obj)) {
                ids.add(obj.trim());
            } else {
                // Check for embedded IDs in text
                const arxivMatches = obj.match(new RegExp(ARXIV_REGEX, "g"));
                if (arxivMatches)
                    arxivMatches.forEach((m: string) => ids.add(m));

                const doiMatches = obj.match(new RegExp(DOI_REGEX, "g"));
                if (doiMatches) doiMatches.forEach((m: string) => ids.add(m));

                const s2Matches = obj.match(new RegExp(S2_REGEX, "g"));
                if (s2Matches) s2Matches.forEach((m: string) => ids.add(m));
            }
        } else if (Array.isArray(obj)) {
            obj.forEach(traverse);
        } else if (typeof obj === "object") {
            Object.values(obj).forEach(traverse);
        }
    };

    traverse(evidence);
    return Array.from(ids);
}
