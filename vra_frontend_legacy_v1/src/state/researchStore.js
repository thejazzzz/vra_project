import { create } from "zustand";
import api, { plannerApi, graphApi } from "../api";

const useResearchStore = create((set, get) => ({
    // ----------------------------------------------------------------
    // State Mirror (Read-Only from Backend mostly)
    // ----------------------------------------------------------------
    query: "",
    audience: "general",
    currentStep: "initial", // initial, awaiting_analysis, etc.

    // Data
    papers: [],
    selectedPapers: [],

    // Analysis & Phase 3 Data
    globalAnalysis: {},
    knowledgeGraph: { nodes: [], links: [] },
    citationGraph: { nodes: [], links: [] },
    authorGraph: { nodes: [], links: [] },
    trends: {},
    gaps: [],
    paperSummaries: {}, // Structured summaries

    // UI State
    isLoading: false,
    error: null,
    isSidebarOpen: true,

    // ----------------------------------------------------------------
    // Actions
    // ----------------------------------------------------------------

    // Initialize or Sync State
    syncState: async (queryId) => {
        set({ isLoading: true, error: null });
        try {
            // Fetch validation/status
            const statusRes = await plannerApi.status(queryId);
            const state = statusRes.data;

            // Map backend snake_case to frontend camelCase where needed, or keep consistent
            set({
                query: state.query,
                audience: state.audience,
                currentStep: state.current_step,
                papers: state.collected_papers || [],
                selectedPapers: state.selected_papers || [],
                globalAnalysis: state.global_analysis || {},
                // Phase 3
                paperSummaries: state.paper_structured_summaries || {},
                gaps: state.research_gaps || [],
                trends: state.concept_trends || {},
                authorGraph: state.author_graph || { nodes: [], links: [] },
                knowledgeGraph: state.knowledge_graph || {
                    nodes: [],
                    links: [],
                },
                citationGraph: state.citation_graph || { nodes: [], links: [] },
                draftReport: state.draft_report || "",
                isLoading: false,
            });

            // If graphs are missing but step implies they exist, fetch explicitly?
            // Usually state has them.
        } catch (err) {
            console.error("Failed to sync state:", err);
            set({ error: err.message, isLoading: false });
        }
    },

    // Poll for updates (optional helper)
    pollStatus: async (queryId) => {
        const { syncState } = get();
        await syncState(queryId);
    },

    // UI Actions
    toggleSidebar: () =>
        set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

    // Backend Triggers
    startResearch: async (query) => {
        set({ isLoading: true, error: null });
        try {
            await plannerApi.plan(query);
            // After plan, we might need to wait or just separate concerns
            set({ query, currentStep: "awaiting_analysis" }); // Optimistic update
        } catch (err) {
            set({ error: err.message });
        } finally {
            set({ isLoading: false });
        }
    },

    // Submit HITL Feedback
    submitReview: async (payload) => {
        try {
            // Optimistic update
            set({ currentStep: "processing" });
            await plannerApi.review(payload);
            // State will sync via polling or explicit sync
            get().syncState(payload.query);
        } catch (err) {
            console.error(err);
            set({ error: err.message });
        }
    },

    submitGraphReview: async (payload) => {
        try {
            set({ currentStep: "processing" });
            await plannerApi.reviewGraph(payload);
            get().syncState(payload.query);
        } catch (err) {
            console.error(err);
            set({ error: err.message });
        }
    },
}));

export default useResearchStore;
