# FUTURE_SCOPE.md

## 1. Multi-User Collaboration & Enterprise Support

- **Team Workspaces**: Enable multiple researchers to share a single "Research Project," allowing for collaborative graph building and shared hypothesis generation.
- **Role-Based Access Control (RBAC)**: Implement granular permissions (Viewer, Editor, Admin) for labs where senior PIs oversee students' research workflows.
- **Real-Time Sync**: Use WebSockets/CRDTs to allow real-time collaborative editing of the Knowledge Graph and Report drafts.

## 2. Advanced AI & Model Fine-Tuning

- **Domain-Specific Fine-Tuning**: Train smaller, efficient models (e.g., Llama-3-Bio) on specific scientific corpora (Biology, Material Science) to improve entity extraction reliability.
- **Self-Correcting Agents**: Implement "Critic" agents that can automatically verify generated citations against the actual text to achieve near-zero hallucination rates.
- **Multimodal Analysis**: Extend ingestion to parse images (charts, plots, molecular structures) within PDFs, not just text.

## 3. Integrations & Data Sources

- **Reference Manager Integration**: Two-way sync with Zotero/Mendeley to automatically export found papers into the user's personal library.
- **Expanded Data Sources**: Integrate PubMed, IEEE Xplore, and Patent databases to support medical and engineering domains more robustly.
- **Lab Notebook Sync**: Connect with Digital Lab Notebooks (Benchling, etc.) to generate hypotheses based on internal experimental data, not just public literature.

## 4. Usability & Deployment

- **Mobile/Tablet Application**: A React Native mobile app for researchers to review daily "Trend Updates" and approve graph nodes on the go.
- **Browser Extension**: A "Clip to VRA" extension allowing users to add the current paper they are reading in a browser directly into a VRA project context.
- **Enterprise Deployment**: Docker/Kubernetes helm charts for on-premise deployment in secure university or pharmaceutical data centers.

## 5. Long-term Research Goals

- **Autonomous Lab Automation**: Connect VRA's hypothesis output directly to cloud labs (e.g., Emerald Cloud Lab) to automatically execute validating experiments.
- **Cross-Disciplinary Discovery**: Specifically optimize graph algorithms to find "hidden links" between disparate fields (e.g., applying a Physics concept to a Biological problem).
