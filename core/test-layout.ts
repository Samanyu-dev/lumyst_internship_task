// core/test-layout.ts
import { readFileSync, writeFileSync } from "fs";
import { join } from "path";
import { GraphFormatService, GraphNode, GraphEdge } from "./graph-format.service";
import { arrangeGraph } from "./graph-arranger.service";
import { toReactFlowNodes, toReactFlowEdges } from "./react-flow.service";

async function main() {
  const dataPath = join(__dirname, "data", "analysis-with-code.json");
  const raw = JSON.parse(readFileSync(dataPath, "utf8"));

  const gfs = new GraphFormatService();

  const graphNodes: GraphNode[] = raw?.analysisData?.graphNodes || [];
  const graphEdges: GraphEdge[] = raw?.analysisData?.graphEdges || [];

  const c1Outputs = raw?.analysisData?.c1Outputs || [];
  const c2Subcategories = raw?.analysisData?.c2Subcategories || [];
  const c2Relationships = raw?.analysisData?.c2Relationships || [];
  const crossC1C2Relationships = raw?.analysisData?.crossC1C2Relationships || [];

  const formatted = gfs.layoutCategoriesWithNodes(
    graphNodes,
    graphEdges,
    c1Outputs,
    c2Subcategories,
    c2Relationships,
    crossC1C2Relationships
  );

  const arranged = arrangeGraph(formatted.graphNodes, formatted.edges);

  const positionedMap = new Map<string, GraphNode>();
  for (const n of arranged) positionedMap.set(n.id, n);

  const positionedGraphNodes = formatted.graphNodes.map((n) => ({ ...n, ...(positionedMap.get(n.id) || {}) }));
  const positionedC1Nodes = formatted.c1Nodes.map((n) => ({ ...n, ...(positionedMap.get(n.id) || {}) }));
  const positionedC2Nodes = formatted.c2Nodes.map((n) => ({ ...n, ...(positionedMap.get(n.id) || {}) }));

  const rfNodes = toReactFlowNodes(positionedGraphNodes, positionedC1Nodes, positionedC2Nodes);
  const rfEdges = toReactFlowEdges(formatted.edges);

  const output = {
    rfNodes,
    rfEdges,
    counts: { nodes: rfNodes.length, edges: rfEdges.length },
    sampleNodes: rfNodes.slice(0, 10).map((n) => ({ id: n.id, pos: n.position })),
  };

  const outPath = join(__dirname, "test-output.json");
  writeFileSync(outPath, JSON.stringify(output, null, 2), "utf8");

  console.log("Wrote", outPath);
  console.log("nodes:", rfNodes.length, "edges:", rfEdges.length);
  console.log("sample nodes:", output.sampleNodes);
}

main().catch((err) => {
  console.error("ERR", err);
  process.exit(1);
});
