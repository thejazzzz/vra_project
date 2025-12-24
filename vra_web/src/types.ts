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

export interface ResearchState {
    query: string;
    audience: string;
    currentStep: string;

    // Data
    papers: Paper[];
    selectedPapers: string[];

    // Graphs & Analysis
    knowledgeGraph: { nodes: any[]; links: any[] };
    authorGraph: { nodes: any[]; links: any[] };
    trends: Record<string, any>;
    gaps: any[];
    draftReport: string;
    globalAnalysis: any;

    // UI State
    isLoading: boolean;
    error: string | null;
    isSidebarOpen: boolean;

    // Actions
    syncState: (queryId: string) => Promise<void>;
    startResearch: (query: string) => Promise<boolean>;
    submitReview: (payload: ReviewPayload) => Promise<void>;
    submitGraphReview: (payload: GraphReviewPayload) => Promise<void>;
    addPaper: (payload: AddPaperPayload) => Promise<void>;
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
    concept_trends: Record<string, any>;
    author_graph: { nodes: any[]; links: any[] };
    knowledge_graph: { nodes: any[]; links: any[] };
    draft_report: string;
    user_feedback?: string;
}

export interface PlanResponse {
    state: BackendResearchState;
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
