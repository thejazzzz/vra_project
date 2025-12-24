import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import { Layout } from "./components/common/Layout";
// Pages
import ResearchOverview from "./pages/ResearchOverview";
import KnowledgeGraphExplorer from "./pages/KnowledgeGraphExplorer";
import AuthorNetworkView from "./pages/AuthorNetworkView";
import TrendsDashboard from "./pages/TrendsDashboard";
import ResearchGapsView from "./pages/ResearchGapsView";
import ReportViewer from "./pages/ReportViewer";

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<LandingPage />} />

                {/* Research Workflow Routes */}
                <Route path="/research/:queryId" element={<Layout />}>
                    <Route index element={<ResearchOverview />} />
                    <Route
                        path="knowledge"
                        element={<KnowledgeGraphExplorer />}
                    />
                    <Route path="authors" element={<AuthorNetworkView />} />
                    <Route path="trends" element={<TrendsDashboard />} />
                    <Route path="gaps" element={<ResearchGapsView />} />
                    <Route path="report" element={<ReportViewer />} />
                </Route>
            </Routes>
        </Router>
    );
}

export default App;
