// src/components/common/Layout.jsx
import React, { useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { Outlet, useParams } from "react-router-dom";
import useResearchStore from "../../state/researchStore";

export const Layout = () => {
    const { queryId } = useParams();
    const { syncState } = useResearchStore();

    useEffect(() => {
        if (queryId) {
            syncState(queryId);
            // Optional: Set up polling here if needed, or rely on specific pages to trigger updates
            // For now, let's poll every 5s to keep UI fresh
            const interval = setInterval(() => syncState(queryId), 5000);
            return () => clearInterval(interval);
        }
    }, [queryId, syncState]);

    return (
        <div className="min-h-screen bg-bg-app text-text-main flex">
            {/* Sidebar fixed */}
            <Sidebar queryId={queryId} />

            {/* Main Content */}
            <main className="flex-1 ml-64 min-w-0">
                <div className="container py-8 max-w-7xl mx-auto">
                    <Outlet />
                </div>
            </main>
        </div>
    );
};
