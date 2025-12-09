#File: api/routers/graph_viewer.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from services.graph_persistence_service import load_graphs
import json  # <-- Add this!

router = APIRouter()
USER_ID = "demo-user"


@router.get("/graphs/view/{query}", response_class=HTMLResponse)
def view_graph(query: str):
    graphs = load_graphs(query, USER_ID)
    if not graphs:
        raise HTTPException(status_code=404, detail="Graphs not found")

    knowledge_graph = graphs["knowledge_graph"]
    citation_graph = graphs["citation_graph"]

    return f"""
    <html>
    <head>
    <style>
        body {{ font-family: Arial; }}
        button {{
            padding: 10px 16px;
            margin-right: 10px;
            cursor: pointer;
            background: #0078ff;
            color: white;
            border: none;
            border-radius: 6px;
        }}
        button.active {{
            background: #005fcc;
        }}
        text {{
            font-size: 12px;
            fill: #111;
        }}
    </style>
    </head>
    <body>
    <h2>Graph Viewer - {query}</h2>
    <button id="btn-kg" class="active">Knowledge Graph</button>
    <button id="btn-cg">Citation Graph</button>

    <svg width="1200" height="700"></svg>

    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        let knowledge = {json.dumps(knowledge_graph)};
        let citation = {json.dumps(citation_graph)};
        let activeGraph = "kg";

        const svg = d3.select("svg"),
              width = +svg.attr("width"),
              height = +svg.attr("height");

        let simulation;

        function clearGraph() {{
            svg.selectAll("*").remove();
            if (simulation) simulation.stop();
        }}

        function render(graph) {{
            clearGraph();

            const link = svg.append("g")
                .selectAll("line")
                .data(graph.links || [])
                .enter().append("line")
                .style("stroke", "#aaa")
                .style("stroke-width", 1.2);

            const node = svg.append("g")
                .selectAll("circle")
                .data(graph.nodes)
                .enter().append("circle")
                .attr("r", 14)
                .style("fill", d => graph.links ? "#69b3a2" : "#ff9f43")
                .call(drag(sim));

            const label = svg.append("g")
                .selectAll("text")
                .data(graph.nodes)
                .enter().append("text")
                .text(d => d.id)
                .attr("dy", -20);

            function sim(alpha) {{
                return d3.forceSimulation(graph.nodes)
                    .force("link", d3.forceLink(graph.links || []).id(d => d.id).distance(150))
                    .force("charge", d3.forceManyBody().strength(-400))
                    .force("center", d3.forceCenter(width / 2, height / 2));
            }}

            simulation = sim();

            function drag(simulation) {{
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

        document.getElementById("btn-kg").onclick = function() {{
            this.classList.add("active");
            document.getElementById("btn-cg").classList.remove("active");
            activeGraph = "kg";
            render(knowledge);
        }};

        document.getElementById("btn-cg").onclick = function() {{
            this.classList.add("active");
            document.getElementById("btn-kg").classList.remove("active");
            activeGraph = "cg";
            render(citation);
        }};

        // initial load
        render(knowledge);
    </script>
    </body>
    </html>
    """
