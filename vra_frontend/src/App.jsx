//File: src/App.jsx
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import WorkflowPage from "./pages/WorkflowPage";
import Navbar from "./components/Navbar";

function App() {
    return (
        <Router>
            <Navbar />
            <div className="main-content">
                <Routes>
                    <Route path="/" element={<LandingPage />} />
                    <Route
                        path="/research/:queryId"
                        element={<WorkflowPage />}
                    />
                </Routes>
            </div>
        </Router>
    );
}

export default App;
