//vra_web/src/types.ts

/**
 * GLOBAL EVIDENCE CONVENTION
 *
 * Any analytical claim presented in the UI must expose at least one attributable
 * source (Paper ID) or be explicitly marked as "contextual" / "conceptual".
 *
 * Format: Claim -> Evidence -> Paper ID -> Source Link
 */

export interface Paper {
    id: string;
    title: string;
    summary?: string;
    authors?: string[];
    [key: string]: any;
}

export interface ResearchGap {
    gap_id?: string;
    type?: string;
    confidence?: number;
    description?: string;
    rationale?: string;
    evidence?: string;
    [key: string]: any;
}

export type TrendStatus =
    | "Emerging"
    | "New"
    | "Stable"
    | "Saturated"
    | "Declining"
    | "Sporadic"
    | "Unknown"
    | string;

export type TrendScope = "Global" | "Subfield" | "Niche" | "Unknown" | string;
export type TrendStability =
    | "Stable"
    | "Volatile"
    | "Transient"
    | "Unknown"
    | string;
export type SemanticDrift = "Low" | "Moderate" | "High" | "Unknown" | string;

export interface TrendMetrics {
    status: TrendStatus;
    scope: TrendScope;
    stability: TrendStability;
    semantic_drift: SemanticDrift;
    trend_confidence: number; // 0.0 - 1.0
    is_trend_valid: boolean;
    growth_rate: number;
    total_count: number;
    last_active_year: number;
    trend_vector: Array<{
        year: number;
        norm_freq: number;
        count: number;
        paper_ids: string[];
        top_related: string[];
    }>;
}

export interface TrendAnalysisResult {
    metadata?: {
        window_used?: { start: number; end: number };
    };
    trends: Record<string, TrendMetrics>;
}

export interface Hypothesis {
    id: string;
    statement: string;
    novelty_score: number;
    testability_score: number;
    supporting_evidence: string;
}

export interface Review {
    hypothesis_id: string;
    critique: string;
    suggestions: string;
    score: number;
}

export interface ResearchState {
    query: string;
    audience: string;
    currentStep: string;

    // Data
    papers: Paper[];
    selectedPapers: Paper[];

    // Graphs & Analysis
    knowledgeGraph: { nodes: GraphNode[]; links: GraphLink[]; graph?: any };

    authorGraph: {
        nodes: any[];
        links: any[];
        meta?: {
            edges_present: boolean;
            metrics_valid: boolean;
            warning?: string | null;
            [key: string]: any;
        };
    };
    trends: Record<string, TrendMetrics>;
    gaps: ResearchGap[];
    draftReport: string;
    globalAnalysis: any;

    // Phase 4
    hypotheses?: Hypothesis[];
    reviews?: Review[];

    stats?: {
        papers_found: number;
        concepts_extracted: number;
    };
    report?: string;
    error: string | null;

    // UI State
    isLoading: boolean;
    isSidebarOpen: boolean;

    // Actions
    addPaper: (payload: AddPaperPayload) => Promise<void>;
    syncState: (query: string) => Promise<void>;
    startResearch: (query: string) => Promise<boolean>;
    submitReview: (payload: ReviewPayload) => Promise<void>;
    submitGraphReview: (payload: GraphReviewPayload) => Promise<void>;
    toggleSidebar: () => void;
}

export interface ReviewPayload {
    query: string;
    selected_paper_ids?: string[];
    audience?: string;
    [key: string]: any;
}

export interface GraphReviewPayload {
    query: string;
    approved: boolean;
    feedback?: string;
    [key: string]: any;
}

export interface AddPaperPayload {
    query: string;
    title: string;
    abstract?: string;
    url?: string;
    authors?: string[];
    year?: string;
    source?: string;
    [key: string]: any;
}

export interface LocalPaper {
    paper_id: string; // The backend returns an int ID, but handling as string is often safer in JS, though we'll match backend.
    canonical_id: string;
    title: string;
    source: string;
    included: boolean; // Frontend state
}

export interface UploadPaperResponse {
    success: boolean;
    paper_id: string;
    canonical_id: string;
    title: string;
    source: string;
    error?: string;
}

export interface PlanRequest {
    query: string;
    audience?: string;
    include_paper_ids?: string[];
}

export interface BackendResearchState {
    query: string;
    audience: string;
    current_step: string;
    collected_papers: any[];
    selected_papers: any[];
    global_analysis: any;
    research_gaps: any[];
    concept_trends: Record<string, TrendMetrics>;
    hypotheses?: any[];
    reviews?: any[];
    author_graph: {
        nodes: any[];
        links: any[];
        meta?: {
            edges_present: boolean;
            metrics_valid: boolean;
            [key: string]: any;
        };
    };
    knowledge_graph: { nodes: GraphNode[]; links: GraphLink[]; graph?: any };

    draft_report: string;
    report_state?: ReportState; // Added logic from merged interface
    user_feedback?: string;
}

export interface PlanResponse {
    state: BackendResearchState;
    session_id: string;
}

export interface StatusResponse {
    state: BackendResearchState;
}

export interface ReviewResponse {
    state: BackendResearchState;
}

export interface GraphReviewResponse {
    state: BackendResearchState;
}

// Phase 4: Research-Grade Graph Types
export interface GraphNode {
    id: string;
    label: string;
    type: string;
    trend_state?: "emerging" | "stable" | "declining" | "reemerging";
    run_count?: number;
    weighted_frequency?: number;
    manual?: boolean;
    [key: string]: any;
}

export interface GraphLink {
    source: string;
    target: string;
    relation: string;
    confidence: number;
    is_hypothesis: boolean;
    is_manual: boolean;
    causal_strength?: "strong" | "weak" | "associative" | "causal";
    trend_state?: string;
    contested_count?: number;
    weighted_frequency?: number;
    evidence_count?: number;
    [key: string]: any;
}

export interface LoginRequest {
    email: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
}

export interface UserResponse {
    id: string;
    email: string;
    role: string;
    is_admin?: boolean;
}

// --- Reporting Agent Types (Phase 3.2) ---

export type ReportStatus =
    | "idle"
    | "planned"
    | "in_progress"
    | "awaiting_final_review"
    | "validating"
    | "finalizing"
    | "completed"
    | "failed";

export type SectionStatus =
    | "planned"
    | "generating"
    | "review"
    | "accepted"
    | "error";

export interface SectionHistory {
    revision: number;
    content: string;
    content_hash: string;
    feedback?: string;
    timestamp: string;
    prompt_version: string;
    model_name: string;
}

export interface ReportSection {
    section_id: string;
    status: SectionStatus;
    title: string;
    description: string;
    depends_on: string[];
    template_key: string;
    content?: string;
    revision: number;
    max_revisions: number;
    history: SectionHistory[];
    quality_scores?: Record<string, number>;
}

export interface ReportState {
    report_status: ReportStatus;
    sections: ReportSection[];
    locks: {
        report: boolean;
        sections: Record<string, boolean>;
    };
    last_successful_step?: { section_id: string; phase: string };
    section_order_hash: string;
    user_confirmed_start: boolean;
    user_confirmed_finalize: boolean;
    created_at: string;
    updated_at: string;
    metrics: Record<string, any>;
}

export interface ResetSectionRequest {
    session_id: string;
    force?: boolean;
}

// Update BackendResearchState to include report_state
// (Merged into main declaration above to avoid duplicates)
