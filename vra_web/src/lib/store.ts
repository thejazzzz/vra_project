import { create } from "zustand";
import { plannerApi, researchApi } from "./api"; // Added researchApi import
import {
    Paper,
    ResearchState,
    ReviewPayload,
    GraphReviewPayload,
    AddPaperPayload,
} from "../types"; // Switched to relative import

export const useResearchStore = create<ResearchState>((set, get) => {
    // Helper to centralize submission logic with error handling and state management
    const handleSubmission = async (
        apiCall: () => Promise<any>,
        query: string
    ) => {
        set({ currentStep: "processing", error: null });
        try {
            await apiCall();
            await get().syncState(query);
        } catch (err: any) {
            console.error("Submission Error:", err);
            set({ error: err.message });
        }
    };

    return {
        query: "",
        audience: "general",
        currentStep: "initial",
        papers: [],
        selectedPapers: [],
        knowledgeGraph: { nodes: [], links: [] },
        authorGraph: { nodes: [], links: [] },
        trends: {},
        gaps: [],
        draftReport: "",
        globalAnalysis: {},
        hypotheses: [],
        reviews: [],
        isLoading: false,
        error: null,
        isSidebarOpen: true,

        addPaper: async (payload: AddPaperPayload) => {
            set({ isLoading: true });
            try {
                await researchApi.addManualPaper({
                    ...payload,
                    abstract: payload.abstract || "",
                    year: payload.year ? parseInt(payload.year) : undefined,
                });
                await get().syncState(payload.query);
                set({ isLoading: false });
            } catch (err: any) {
                console.error("Add Paper Error:", err);
                set({ error: err.message, isLoading: false });
            }
        },

        syncState: async (queryId: string) => {
            set({ isLoading: true, error: null });
            try {
                const response = await plannerApi.status(queryId);
                const state = response.state;

                // Map backend snake_case to frontend camelCase if needed
                // Assuming backend mostly mirrors this structure or we map it here
                set({
                    query: state.query,
                    audience: state.audience,
                    currentStep: state.current_step,
                    papers: state.collected_papers || [],
                    selectedPapers: state.selected_papers || [],
                    globalAnalysis: state.global_analysis || {},
                    gaps: state.research_gaps || [],
                    trends: state.concept_trends || {},
                    hypotheses: state.hypotheses || [],
                    reviews: state.reviews || [],
                    authorGraph:
                        state.author_graph && state.author_graph.nodes
                            ? state.author_graph
                            : { nodes: [], links: [] },
                    knowledgeGraph:
                        state.knowledge_graph && state.knowledge_graph.nodes
                            ? state.knowledge_graph
                            : {
                                  nodes: [],
                                  links: [],
                              },
                    draftReport: state.draft_report || "",
                    isLoading: false,
                });
            } catch (err: any) {
                console.error("Sync Error:", err);
                set({
                    error: err.message || "Failed to sync state",
                    isLoading: false,
                });
            }
        },

        startResearch: async (query: string): Promise<boolean> => {
            set({ isLoading: true, error: null });
            try {
                await plannerApi.plan(query);
                set({ query, currentStep: "awaiting_analysis" });
                return true;
            } catch (err: any) {
                console.error("startResearch error", err);
                set({ error: err.message });
                return false;
            } finally {
                set({ isLoading: false });
            }
        },

        submitReview: async (payload: ReviewPayload) => {
            await handleSubmission(
                () => plannerApi.review(payload),
                payload.query
            );
        },

        submitGraphReview: async (payload: GraphReviewPayload) => {
            await handleSubmission(
                () => plannerApi.reviewGraph(payload),
                payload.query
            );
        },

        toggleSidebar: () =>
            set((state: ResearchState) => ({
                isSidebarOpen: !state.isSidebarOpen,
            })),
    };
});
