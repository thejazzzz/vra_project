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
    - In prod, replace with proper auth (JWT/session) and return the authenticated user's id.
    - For local/dev you may allow fallback to 'demo-user' but be cautious about data isolation.
    """
    if not x_user_id:
        # For development, fallback to demo. In production you should raise/require auth.
        # raise HTTPException(status_code=401, detail="Missing X-User-Id header")
        return "demo-user"
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

    # Safely embed JSON into HTML: escape closing tags to avoid XSS issues
    kg_json = json.dumps(knowledge_graph).replace("</", "<\\/")
    cg_json = json.dumps(citation_graph).replace("</", "<\\/")

    # -----------------------------
    # IMPORTANT: SRI Instructions
    # - Pin to a specific D3 version (recommended) and compute the SHA384 hash locally:
    #   curl -sSL -o d3.min.js https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js
    #   openssl dgst -sha384 -binary d3.min.js | openssl base64 -A
    # - Copy the base64 result and set integrity="sha384-<base64>"
    # - Replace the INTEGRITY_HASH_GOES_HERE placeholder below with the computed value.
    # -----------------------------
    # Example pinned CDN URL: https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js

    integrity_placeholder = "INTEGRITY_HASH_GOES_HERE"

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
            text {{ font-size: 12px; fill: #111; }}
            svg {{ border: 1px solid #ddd; margin-top: 20px; background: #fafafa; }}
        </style>

        <!--
            IMPORTANT: Replace the integrity attribute below with the sha384 hash you computed locally.
            Example (after computing hash):
            integrity="sha384-<YOUR_COMPUTED_BASE64_HASH>"
        -->
        <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"
                integrity="{integrity_placeholder}"
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

                // Link elements
                const link = svg.append("g")
                    .selectAll("line")
                    .data(links)
                    .enter()
                    .append("line")
                    .style("stroke", "#aaa")
                    .style("stroke-width", 1.2);

                // Node elements — color by per-node `type` or `group`
                const node = svg.append("g")
                    .selectAll("circle")
                    .data(nodes)
                    .enter()
                    .append("circle")
                    .attr("r", 14)
                    .style("fill", d => {{
                        // Prefer explicit node.type or node.group; fallback to neutral color
                        if (d.type === "paper") return "#ff9f43";
                        if (d.type === "concept") return "#69b3a2";
                        if (d.group === "paper") return "#ff9f43";
                        if (d.group === "concept") return "#69b3a2";
                        return "#9aa";
                    }})
                    .call(drag());  // drag uses closure over `simulation`

                // Labels
                const label = svg.append("g")
                    .selectAll("text")
                    .data(nodes)
                    .enter()
                    .append("text")
                    .text(d => d.id)
                    .attr("dy", -18);

                // Force simulation
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

            // Bind buttons
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
