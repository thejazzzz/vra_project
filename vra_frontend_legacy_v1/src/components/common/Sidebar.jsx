// src/components/common/Sidebar.jsx
import React from "react";
import { NavLink } from "react-router-dom";
import {
    LayoutDashboard,
    Network,
    Users,
    TrendingUp,
    AlertTriangle,
    FileText,
    Settings,
} from "lucide-react";
import { cn } from "../../utils"; // Assuming utils or clsx usage

const NavItem = ({ to, icon: Icon, label }) => (
    <NavLink
        to={to}
        className={({ isActive }) =>
            cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg transition-all text-sm font-medium",
                isActive
                    ? "bg-primary/15 text-primary"
                    : "text-muted-foreground hover:bg-white/5 hover:text-white"
            )
        }
    >
        <Icon size={18} />
        <span>{label}</span>
    </NavLink>
);

export const Sidebar = ({ queryId }) => {
    if (!queryId) return null;

    const baseUrl = `/research/${queryId}`;

    return (
        <aside className="w-64 border-r border-border bg-card/50 backdrop-blur-xl h-screen flex flex-col fixed left-0 top-0 z-50">
            <div className="p-6 border-b border-border/50">
                <div className="flex items-center gap-2 text-xl font-bold text-white">
                    <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center text-xs">
                        AI
                    </span>
                    <span>VRA</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                    Research Intelligence
                </p>
            </div>

            <nav className="flex-1 p-4 space-y-1">
                <div className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Analysis
                </div>
                <NavItem
                    to={`${baseUrl}`}
                    icon={LayoutDashboard}
                    label="Overview"
                />
                <NavItem
                    to={`${baseUrl}/knowledge`}
                    icon={Network}
                    label="Knowledge Graph"
                />
                <NavItem
                    to={`${baseUrl}/authors`}
                    icon={Users}
                    label="Author Network"
                />
                <NavItem
                    to={`${baseUrl}/trends`}
                    icon={TrendingUp}
                    label="Trends"
                />
                <NavItem
                    to={`${baseUrl}/gaps`}
                    icon={AlertTriangle}
                    label="Research Gaps"
                />

                <div className="mt-8 px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Output
                </div>
                <NavItem
                    to={`${baseUrl}/report`}
                    icon={FileText}
                    label="Report"
                />
            </nav>

            <div className="p-4 border-t border-border/50">
                <div className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-white cursor-pointer transition-colors">
                    <Settings size={18} />
                    <span>Settings</span>
                </div>
            </div>
        </aside>
    );
};
