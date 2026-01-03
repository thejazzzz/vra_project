//vra_web/src/app/research/[id]/report/page.tsx
"use client";

import { use } from "react";
import { ReportDashboard } from "./report-dashboard";

export default function ReportPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const resolvedParams = use(params);
    const id = resolvedParams.id;

    return <ReportDashboard sessionId={id} />;
}
