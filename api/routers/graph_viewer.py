# File: api/routers/graph_viewer.py
from html import escape
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse
from services.graph_persistence_service import load_graphs
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def get_user_id(x_user_id: Optional[str] = Header(None)):
    """
    Temporary user-id resolver.
    - Local/dev: fallback to demo-user.
    - Production: require auth and return real user ID.
    """
    if not x_user_id:
        return "demo-user"  # Replace with proper auth later
    return x_user_id


@router.get("/graphs/view/{query}", response_class=HTMLResponse)
def view_graph(query: str, user_id: str = Depends(get_user_id)):
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Invalid query parameter")

    graphs = load_graphs(query, user_id)
    if not graphs:
        raise HTTPException(status_code=404, detail="Graphs not found")

    if "knowledge_graph" not in graphs or "citation_graph" not in graphs:
        raise HTTPException(status_code=500, detail="Corrupt graph data in database")

    knowledge_graph = graphs["knowledge_graph"]
    citation_graph = graphs["citation_graph"]

    # Escape unsafe sequences to prevent HTML/script injection
    kg_json = json.dumps(knowledge_graph).replace("</", "<\\/")
    cg_json = json.dumps(citation_graph).replace("</", "<\\/")

    # Correct SRI hash for cdnjs D3 v7.9.0
    integrity_hash = (
        "sha384-tB6xhxL7sRKqGZo4PMBVXgS5aXoaZySUdkGFUTkOcJCIZy9FHn5Vf3L7hIwrKyYV"
    )

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8" />
    <title>Graph Viewer - {escape(query)}</title>

    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        button {{
            padding: 10px 16px; margin-right: 10px; cursor: pointer;
            background: #0078ff; color: white; border: none; border-radius: 6px;
            font-size: 14px;
        }}
        button.active {{ background: #005fcc; }}
        text {{ font-size: 12px; fill: #111; pointer-events: none; }}
        svg {{ border: 1px solid #ddd; margin-top: 20px; background: #fafafa; }}
    </style>

    <!-- Version-pinned D3.js + Verified SRI Hash -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"
            integrity="{integrity_hash}"
            crossorigin="anonymous"></script>
</head>

<body>
    <h2>Graph Viewer — {escape(query)}</h2>
    <p><small>User: {escape(user_id)}</small></p>

    <button id="btn-kg" class="active">Knowledge Graph</button>
    <button id="btn-cg">Citation Graph</button>

    <svg width="1200" height="700"></svg>

    <script>
        let knowledge = {kg_json};
        let citation = {cg_json};

        const svg = d3.select("svg"),
              width = +svg.attr("width"),
              height = +svg.attr("height");

        let simulation = null;

        function clearGraph() {{
            svg.selectAll("*").remove();
            if (simulation) simulation.stop();
        }}

        function render(graph) {{
            clearGraph();

            const links = graph.links || [];
            const nodes = graph.nodes || [];

            // -----------------------
            // Draw edges
            // -----------------------
            const link = svg.append("g")
                .selectAll("line")
                .data(links)
                .enter()
                .append("line")
                .style("stroke", "#aaa")
                .style("stroke-width", 1.2);

            // -----------------------
            // Draw nodes
            // -----------------------
            const node = svg.append("g")
                .selectAll("circle")
                .data(nodes)
                .enter()
                .append("circle")
                .attr("r", 14)
                .style("fill", d => {{
                    // Colors by node type or fallback group
                    if (d.type === "paper") return "#ff9f43";
                    if (d.type === "concept") return "#69b3a2";
                    if (d.group === "paper") return "#ff9f43";
                    if (d.group === "concept") return "#69b3a2";
                    return "#9aa";  // fallback
                }})
                .call(drag()); // uses closure over `simulation`

            // -----------------------
            // Labels
            // -----------------------
            const label = svg.append("g")
                .selectAll("text")
                .data(nodes)
                .enter()
                .append("text")
                .text(d => d.id)
                .attr("dy", -18);

            // -----------------------
            // Force simulation
            // -----------------------
            simulation = d3.forceSimulation(nodes)
                .force("link", d3.forceLink(links).id(d => d.id).distance(150))
                .force("charge", d3.forceManyBody().strength(-400))
                .force("center", d3.forceCenter(width / 2, height / 2));

            function drag() {{
                function dragstarted(event) {{
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    event.subject.fx = event.subject.x;
                    event.subject.fy = event.subject.y;
                }}
                function dragged(event) {{
                    event.subject.fx = event.x;
                    event.subject.fy = event.y;
                }}
                function dragended(event) {{
                    if (!event.active) simulation.alphaTarget(0);
                    event.subject.fx = null;
                    event.subject.fy = null;
                }}
                return d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended);
            }}

            simulation.on("tick", () => {{
                link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);

                node
                    .attr("cx", d => d.x)
                    .attr("cy", d => d.y);

                label
                    .attr("x", d => d.x)
                    .attr("y", d => d.y);
            }});
        }}

        // -----------------------
        // Bind buttons
        // -----------------------
        document.getElementById("btn-kg").onclick = function() {{
            this.classList.add("active");
            document.getElementById("btn-cg").classList.remove("active");
            render(knowledge);
        }};

        document.getElementById("btn-cg").onclick = function() {{
            this.classList.add("active");
            document.getElementById("btn-kg").classList.remove("active");
            render(citation);
        }};

        // Initial render
        render(knowledge);
    </script>
</body>
</html>
"""
