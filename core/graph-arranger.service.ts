import * as dagre from "dagre";
import { GraphNode, GraphEdge } from "./graph-format.service";

type ArrangeOptions = {
  dagreOptions?: { rankdir?: string; nodesep?: number; ranksep?: number };
};

export function arrangeGraph(nodes: GraphNode[], edges: GraphEdge[], options?: ArrangeOptions): GraphNode[] {
  if (!nodes || nodes.length === 0) return [];

  const dagreOptions = {
    rankdir: options?.dagreOptions?.rankdir ?? "TB",
    nodesep: options?.dagreOptions?.nodesep ?? 80,
    ranksep: options?.dagreOptions?.ranksep ?? 120,
  };

  const g = new dagre.graphlib.Graph();
  g.setGraph(dagreOptions);
  g.setDefaultEdgeLabel(() => ({}));

  const NODE_W = 180;
  const NODE_H = 60;

  for (const n of nodes) {
    try {
      g.setNode(n.id, { width: NODE_W, height: NODE_H });
    } catch {}
  }

  for (const e of edges) {
    if (!e || !e.source || !e.target) continue;
    try {
      g.setEdge(e.source, e.target);
    } catch {}
  }

  dagre.layout(g);

  const arranged = nodes.map((n) => {
    const nd = g.node(n.id) as { x: number; y: number; width?: number; height?: number } | undefined;
    const x = nd?.x ?? (n.x ?? Math.random() * 800);
    const y = nd?.y ?? (n.y ?? Math.random() * 800);
    return { ...n, x, y, position: { x: x - (nd?.width ?? NODE_W) / 2, y: y - (nd?.height ?? NODE_H) / 2 } };
  });

  const out = arranged.map((n) => ({ ...n, position: { ...n.position } }));
  const MIN = 60;
  for (let i = 0; i < out.length; i++) {
    for (let j = i + 1; j < out.length; j++) {
      const a = out[i].position;
      const b = out[j].position;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const d = Math.sqrt(dx * dx + dy * dy) || 0.001;
      if (d < MIN) {
        const push = (MIN - d) / 2;
        const nx = (dx / d) * push;
        const ny = (dy / d) * push;
        out[j].position.x += nx;
        out[j].position.y += ny;
        out[i].position.x -= nx;
        out[i].position.y -= ny;
      }
    }
  }

  return out;
}
