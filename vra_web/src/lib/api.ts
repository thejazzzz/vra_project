//vra_web/src/lib/api.ts
import axios, { AxiosInstance } from "axios";
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

// Shared config
const baseConfig = {
    baseURL: API_URL,
    headers: {
        "Content-Type": "application/json",
    },
    withCredentials: true, // Send cookies with requests
};

// 1. Default Client (Fast endpoints: 300s -> Increased for heavy chains)
const defaultApi = axios.create({
    ...baseConfig,
    timeout: 300000, // 5 minutes (Increased from 30s)
});

// 2. Long-Running Client (Heavy endpoints: 300s)
const longRunningApi = axios.create({
    ...baseConfig,
    timeout: 300000, // 5 minutes
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

// Centralized Interceptor Setup
const setupInterceptors = (instance: AxiosInstance) => {
    instance.interceptors.response.use(
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
                            return instance(originalRequest);
                        })
                        .catch((err) => {
                            return Promise.reject(err);
                        });
                }

                originalRequest._retry = true;
                isRefreshing = true;

                try {
                    // Attempt to refresh the token using the HttpOnly cookie
                    // Use defaultApi for refresh call (it's fast)
                    await defaultApi.post(
                        "/auth/refresh",
                        {},
                        {
                            // @ts-ignore - custom config property
                            skipAuthRefresh: true,
                        },
                    );

                    // If successful, retry the queued requests
                    processQueue(null);
                    isRefreshing = false;

                    // Retry the original request
                    return instance(originalRequest);
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
        },
    );
};

// Inject Authorization Header from LocalStorage (Fallback for Localhost Cookie issues)
const injectToken = (instance: AxiosInstance) => {
    instance.interceptors.request.use(
        (config) => {
            if (typeof window !== "undefined") {
                const token =
                    localStorage.getItem("vra_auth_token") ||
                    // Fallback to reading cookie manually if localstorage missing
                    document.cookie
                        .split("; ")
                        .find((row) => row.startsWith("vra_auth_token="))
                        ?.split("=")[1];

                if (token && !config.headers["Authorization"]) {
                    config.headers["Authorization"] = `Bearer ${token}`;
                }
            }
            return config;
        },
        (error) => Promise.reject(error),
    );
};

// Apply logic to both
injectToken(defaultApi);
injectToken(longRunningApi);
setupInterceptors(defaultApi);
setupInterceptors(longRunningApi);

// EXPORTS

// Auth: Fast
export const authApi = {
    login: (email: string) =>
        defaultApi.post("/auth/login", { email }).then((res) => res.data),

    me: () => defaultApi.get<UserResponse>("/auth/me").then((res) => res.data),

    logout: () =>
        defaultApi.post("/auth/logout").then(() => {
            if (typeof window !== "undefined") {
                localStorage.removeItem("vra_auth_token");
            }
        }),
};

// Planner: Mixed
export const plannerApi = {
    plan: (
        query: string,
        include_paper_ids: string[] = [],
        audience: string = "industry",
        taskId?: string, // Generated by client
    ): Promise<PlanResponse> =>
        longRunningApi // HEAVY
            .post<PlanResponse>("/planner/plan", {
                query,
                include_paper_ids,
                audience,
                task_id: taskId,
            })
            .then((res) => res.data),

    status: (query: string): Promise<StatusResponse> =>
        defaultApi // Fast
            .get<StatusResponse>(`/planner/status/${encodeURIComponent(query)}`)
            .then((res) => res.data),

    review: (payload: ReviewPayload): Promise<ReviewResponse> =>
        defaultApi // Fast
            .post<ReviewResponse>("/planner/review", payload)
            .then((res) => res.data),

    reviewGraph: (payload: GraphReviewPayload): Promise<GraphReviewResponse> =>
        defaultApi // Fast
            .post<GraphReviewResponse>("/planner/review-graph", payload)
            .then((res) => res.data),

    continue: (sessionId: string): Promise<StatusResponse> =>
        defaultApi // Usually fast status update
            .post<StatusResponse>(
                `/planner/continue/${encodeURIComponent(sessionId)}`,
            )
            .then((res) => res.data),

    getSessions: (): Promise<any> =>
        defaultApi.get<any>("/planner/sessions").then((res) => res.data),
};

// Research: Fast? Depends. Assuming manual add is fast.
export const researchApi = {
    addManualPaper: async (payload: {
        query: string;
        title: string;
        abstract: string;
        url?: string;
        authors?: string[];
        year?: number;
        source?: string;
    }) => defaultApi.post("/research/manual", payload),

    getProgress: async (taskId: string) =>
        defaultApi.get(`/research/progress/${taskId}`).then((res) => res.data),
};

// Graph: Fast reads
export const graphApi = {
    getData: async (query: string) =>
        defaultApi.get(`/graphs/graphs/${encodeURIComponent(query)}`),
    getAuthors: async (query: string) =>
        defaultApi.get(`/graphs/authors/${encodeURIComponent(query)}`),
    getTrends: async (query: string) =>
        defaultApi.get(`/graphs/trends/${encodeURIComponent(query)}`),
    getGaps: async (query: string) =>
        defaultApi.get(`/graphs/gaps/${encodeURIComponent(query)}`),
    getConceptContext: async (concept: string) =>
        defaultApi.get<{
            concept: string;
            snippets: Array<{
                document: string;
                metadata: { canonical_id: string };
            }>;
        }>(`/graph-viewer/context/${encodeURIComponent(concept)}`),

    // Phase 4: Approval Gate
    approve: async (query: string, userId: string) =>
        defaultApi
            .post(`/graphs/${encodeURIComponent(query)}/approve`, {
                user_id: userId,
            })
            .then((res) => res.data),
};

// Reporting: Mixed
export const reportingApi = {
    // Init: Fast
    init: (sessionId: string, confirm: boolean = true) =>
        defaultApi
            .post("/reporting/init", {
                session_id: sessionId,
                confirm,
            })
            .then((res) => res.data.report_state),

    // Get State: Fast (Polling)
    getState: (sessionId: string) =>
        defaultApi
            .get(`/reporting/state/${encodeURIComponent(sessionId)}`)
            .then((res) => res.data.report_state),

    // Generate: VERY HEAVY
    generateSection: (sessionId: string, sectionId: string) =>
        longRunningApi
            .post(
                `/reporting/section/${encodeURIComponent(sectionId)}/generate`,
                {
                    session_id: sessionId,
                },
            )
            .then((res) => res.data.section),

    // Review: Fast
    submitReview: (
        sessionId: string,
        sectionId: string,
        payload: {
            accepted: boolean;
            feedback?: string;
        },
    ) =>
        defaultApi
            .post(
                `/reporting/section/${encodeURIComponent(sectionId)}/review`,
                {
                    session_id: sessionId,
                    ...payload,
                },
            )
            .then((res) => res.data.section),

    // Reset: Fast
    resetSection: (
        sessionId: string,
        sectionId: string,
        force: boolean = false,
    ) =>
        defaultApi
            .post(`/reporting/section/${encodeURIComponent(sectionId)}/reset`, {
                session_id: sessionId,
                force,
            })
            .then((res) => res.data.section),

    // Finalize: HEAVY (Virtual assembly can be slow)
    finalize: (sessionId: string) =>
        longRunningApi
            .post("/reporting/finalize", {
                session_id: sessionId,
                confirm: true,
            })
            .then((res) => res.data.report_state),

    // Export: HEAVY
    exportReport: (sessionId: string, format: "pdf" | "docx" | "markdown") =>
        longRunningApi
            .post(
                "/reporting/export",
                {
                    session_id: sessionId,
                    format,
                },
                {
                    responseType: "blob", // Important for binary downloads
                },
            )
            .then((res) => res.data),
};

// Upload: Heavy
export const uploadApi = {
    uploadPaper: (file: File) => {
        const formData = new FormData();
        formData.append("file", file);
        return longRunningApi
            .post("/upload/", formData, {
                headers: {
                    "Content-Type": "multipart/form-data",
                },
            })
            .then((res) => res.data);
    },
};

// Default export for generic usage, defaulting to short timeout safely
export default defaultApi;
