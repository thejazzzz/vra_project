//vra_web/src/lib/api.ts
import axios from "axios";
import {
    LoginRequest,
    LoginResponse,
    UserResponse,
    PlanResponse,
    ReviewPayload,
    ReviewResponse,
    GraphReviewPayload,
    GraphReviewResponse,
    StatusResponse,
} from "../types";

// Default to localhost:7000 (User's current port) if not specified
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:7000";

const api = axios.create({
    baseURL: API_URL,
    timeout: 120000, // 120 seconds for long research tasks
    headers: {
        "Content-Type": "application/json",
    },
    withCredentials: true, // Send cookies with requests
});

// Refresh Token Logic
let isRefreshing = false;
let failedQueue: any[] = [];

const processQueue = (error: any = null) => {
    failedQueue.forEach((prom) => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve();
        }
    });

    failedQueue = [];
};

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // @ts-ignore
        if (
            error.response?.status === 401 &&
            !originalRequest._retry &&
            !originalRequest.skipAuthRefresh
        ) {
            if (isRefreshing) {
                return new Promise(function (resolve, reject) {
                    failedQueue.push({ resolve, reject });
                })
                    .then(() => {
                        return api(originalRequest);
                    })
                    .catch((err) => {
                        return Promise.reject(err);
                    });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            try {
                // Attempt to refresh the token using the HttpOnly cookie
                // Pass custom config to bypass interceptor loop
                await api.post(
                    "/auth/refresh",
                    {},
                    {
                        // @ts-ignore - custom config property
                        skipAuthRefresh: true,
                    }
                );

                // If successful, retry the queued requests
                processQueue(null);
                isRefreshing = false;

                // Retry the original request
                return api(originalRequest);
            } catch (err) {
                processQueue(err);
                isRefreshing = false;

                // If refresh fails, we must redirect to login
                if (typeof window !== "undefined") {
                    // Avoid infinite loops if already on login
                    if (!window.location.pathname.startsWith("/login")) {
                        window.location.href = "/login";
                    }
                }
                return Promise.reject(err);
            }
        }

        return Promise.reject(error);
    }
);

export const authApi = {
    login: (email: string) =>
        api.post("/auth/login", { email }).then((res) => res.data),

    me: () => api.get<UserResponse>("/auth/me").then((res) => res.data),

    logout: () =>
        api.post("/auth/logout").then(() => {
            // Determine if we need to do anything client side.
            // Since we rely on cookies, just ensuring the request sent is enough.
            if (typeof window !== "undefined") {
                // Force reload or redirect might be needed by caller,
                // but for API method just return promise.
                localStorage.removeItem("vra_auth_token"); // Cleanup legacy if exists
            }
        }),
};

export const plannerApi = {
    plan: (
        query: string,
        include_paper_ids: string[] = [],
        audience: string = "industry"
    ): Promise<PlanResponse> =>
        api
            .post<PlanResponse>("/planner/plan", {
                query,
                include_paper_ids,
                audience,
            })
            .then((res) => res.data),

    status: (query: string): Promise<StatusResponse> =>
        api
            .get<StatusResponse>(`/planner/status/${encodeURIComponent(query)}`)
            .then((res) => res.data),

    review: (payload: ReviewPayload): Promise<ReviewResponse> =>
        api
            .post<ReviewResponse>("/planner/review", payload)
            .then((res) => res.data),

    reviewGraph: (payload: GraphReviewPayload): Promise<GraphReviewResponse> =>
        api
            .post<GraphReviewResponse>("/planner/review-graph", payload)
            .then((res) => res.data),

    continue: (sessionId: string): Promise<StatusResponse> =>
        api
            .post<StatusResponse>(
                `/planner/continue/${encodeURIComponent(sessionId)}`
            )
            .then((res) => res.data),

    getSessions: (): Promise<any> =>
        api.get<any>("/planner/sessions").then((res) => res.data),
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
    getConceptContext: async (concept: string) =>
        api.get<{
            concept: string;
            snippets: Array<{
                document: string;
                metadata: { canonical_id: string };
            }>;
        }>(`/graph-viewer/context/${encodeURIComponent(concept)}`),
};

export const uploadApi = {
    uploadPaper: (file: File) => {
        const formData = new FormData();
        formData.append("file", file);
        return api
            .post("/upload/", formData, {
                headers: {
                    "Content-Type": "multipart/form-data",
                },
            })
            .then((res) => res.data);
    },
};

export default api;
