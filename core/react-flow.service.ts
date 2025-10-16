import { GraphNode, GraphEdge } from "./graph-format.service";

export type RFNode = {
  id: string;
  position: { x: number; y: number };
  data: { label: string };
  type?: string;
  style?: Record<string, any>;
};

export type RFEdge = {
  id: string;
  source: string;
  target: string;
  label?: string;
  animated?: boolean;
  style?: Record<string, any>;
  labelStyle?: Record<string, any>;
};

export function toReactFlowNodes(graphNodes: GraphNode[], c1Nodes?: GraphNode[], c2Nodes?: GraphNode[]): RFNode[] {
  const out: RFNode[] = [];
  for (const n of graphNodes || []) {
    out.push({
      id: n.id,
      position: { x: (n.position?.x ?? n.x ?? 0) as number, y: (n.position?.y ?? n.y ?? 0) as number },
      data: { label: n.label ?? n.id },
      type: "default",
      style: { background: "#dbeafe", border: "2px solid #3b82f6", color: "#1e40af", borderRadius: "6px" },
    });
  }
  for (const n of c1Nodes || []) {
    out.push({
      id: n.id,
      position: { x: (n.position?.x ?? n.x ?? 0) as number, y: (n.position?.y ?? n.y ?? 0) as number },
      data: { label: n.label ?? n.id },
      type: "default",
      style: { background: "#fef2f2", border: "3px solid #dc2626", color: "#991b1b", fontWeight: "bold", borderRadius: "6px" },
    });
  }
  for (const n of c2Nodes || []) {
    out.push({
      id: n.id,
      position: { x: (n.position?.x ?? n.x ?? 0) as number, y: (n.position?.y ?? n.y ?? 0) as number },
      data: { label: n.label ?? n.id },
      type: "default",
      style: { background: "#f0fdf4", border: "2px solid #16a34a", color: "#166534", borderRadius: "6px" },
    });
  }
  return out;
}

export function toReactFlowEdges(edges: GraphEdge[]): RFEdge[] {
  return (edges || []).map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    animated: false,
    style:
      e.label === "contains"
        ? { stroke: "#9ca3af", strokeDasharray: "5,5", strokeWidth: 1 }
        : { stroke: "#374151", strokeWidth: 1 },
    labelStyle: { fill: "#000", fontWeight: 500 },
  }));
}
