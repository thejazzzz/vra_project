//File: src/api.js
import axios from "axios";

// Default to localhost:7000 (User's current port) if not specified
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:7000";
console.log("VRA Frontend connecting to API at:", API_URL);

const api = axios.create({
    baseURL: API_URL,
    headers: {
        "Content-Type": "application/json",
        "X-User-Id": "demo-user", // Required by backend
    },
});

export const plannerApi = {
    plan: (query) => api.post("/planner/plan", { query }),
    status: (query) => api.get(`/planner/status/${encodeURIComponent(query)}`),
    review: (payload) => api.post("/planner/review", payload),
    reviewGraph: (payload) => api.post("/planner/review-graph", payload),
    continue: () => api.post("/planner/continue", {}), // For general waiting steps
};

export const graphApi = {
    // Backend guide says: POST /graphs/graphs/{query} - Wait, file says GET /graphs/{query}
    // Using the one found in graphs.py
    getData: (query) => api.get(`/graphs/graphs/${encodeURIComponent(query)}`),
};

export default api;
