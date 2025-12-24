import axios from "axios";

// Default to localhost:7000 (User's current port) if not specified
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:7000";

const api = axios.create({
    baseURL: API_URL,
    timeout: 120000, // 120 seconds for long research tasks
    headers: {
        "Content-Type": "application/json",
        "X-User-Id": process.env.NEXT_PUBLIC_USER_ID || "demo-user",
    },
});
import {
    PlanRequest,
    PlanResponse,
    ReviewPayload,
    ReviewResponse,
    GraphReviewPayload,
    GraphReviewResponse,
    StatusResponse,
} from "../types";

export const plannerApi = {
    plan: (query: string) =>
        api
            .post<PlanResponse>("/planner/plan", { query })
            .then((res) => res.data),

    status: (query: string) =>
        api
            .get<StatusResponse>(`/planner/status/${encodeURIComponent(query)}`)
            .then((res) => res.data),

    review: (payload: ReviewPayload) =>
        api
            .post<ReviewResponse>("/planner/review", payload)
            .then((res) => res.data),

    reviewGraph: (payload: GraphReviewPayload) =>
        api
            .post<GraphReviewResponse>("/planner/review-graph", payload)
            .then((res) => res.data),

    continue: (query: string) =>
        api
            .post<PlanResponse>("/planner/continue", { query })
            .then((res) => res.data),
};

export const researchApi = {
    addManualPaper: async (payload: {
        query: string;
        title: string;
        abstract: string;
        url?: string;
        authors?: string[];
        year?: number;
        source?: string;
    }) => api.post("/research/manual", payload),
};

export const graphApi = {
    getData: async (query: string) =>
        api.get(`/graphs/graphs/${encodeURIComponent(query)}`),
    getAuthors: async (query: string) =>
        api.get(`/graphs/authors/${encodeURIComponent(query)}`),
    getTrends: async (query: string) =>
        api.get(`/graphs/trends/${encodeURIComponent(query)}`),
    getGaps: async (query: string) =>
        api.get(`/graphs/gaps/${encodeURIComponent(query)}`),
};

export default api;
