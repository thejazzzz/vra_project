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
    knowledgeGraph: { nodes: any[]; links: any[] };
    authorGraph: { nodes: any[]; links: any[] };
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

export interface PlanRequest {
    query: string;
    audience?: string;
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
    author_graph: { nodes: any[]; links: any[] };
    knowledge_graph: { nodes: any[]; links: any[] };
    draft_report: string;
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
}
