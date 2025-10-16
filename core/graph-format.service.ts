import * as dagre from "dagre";

export interface GraphNode {
  [k: string]: any;
  id: string;
  label?: string;
  x?: number;
  y?: number;
  position?: { x: number; y: number };
}

export interface GraphEdge {
  [k: string]: any;
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface C1Output {
  [k: string]: any;
  id: string;
  label?: string;
}

export interface C2Subcategory {
  [k: string]: any;
  id: string;
  label?: string;
  c1CategoryId: string;
  nodeIds: string[];
}

export interface C2Relationship {
  id: string;
  fromC2: string;
  toC2: string;
  label?: string;
}

export interface CrossC1C2Relationship {
  id: string;
  fromC2: string;
  toC2: string;
  label?: string;
}

function notNull<T>(v: T | null | undefined): v is T {
  return v !== null && v !== undefined;
}

export class GraphFormatService {
  layoutCategoriesWithNodes(
    graphNodes: GraphNode[] = [],
    graphEdges: GraphEdge[] = [],
    c1Outputs: C1Output[] = [],
    c2Subcategories: C2Subcategory[] = [],
    c2Relationships: C2Relationship[] = [],
    crossC1C2Relationships: CrossC1C2Relationship[] = []
  ) {
    const nameToC2Id = new Map<string, string>();
    for (const c2 of c2Subcategories || []) {
      const key = (c2 as any).c2Name ?? c2.label ?? c2.id;
      nameToC2Id.set(key, c2.id);
    }

    const dag = new dagre.graphlib.Graph();
    dag.setDefaultEdgeLabel(() => ({}));
    dag.setGraph({ rankdir: "TB", nodesep: 80, ranksep: 120, marginx: 20, marginy: 20 });

    const allNodes: GraphNode[] = [
      ...(graphNodes || []),
      ...((c1Outputs || []).map((c1) => ({ ...c1, __type: "c1" }) as GraphNode)),
      ...((c2Subcategories || []).map((c2) => ({ ...c2, __type: "c2" }) as GraphNode)),
    ];

    for (const n of allNodes) {
      try {
        dag.setNode(n.id, { width: 150, height: 50 });
      } catch {}
    }

    const edgesFromC2ContainsNodes: GraphEdge[] = (c2Subcategories || []).flatMap((c2) =>
      (c2.nodeIds || []).map<GraphEdge>((nodeId) => ({
        id: `c2-${c2.id}-to-node-${nodeId}`,
        source: c2.id,
        target: nodeId,
        label: "contains",
      }))
    );

    const edgesFromC1ToC2: GraphEdge[] = (c2Subcategories || []).map((c2) => ({
      id: `c1-${c2.c1CategoryId}-to-c2-${c2.id}`,
      source: c2.c1CategoryId,
      target: c2.id,
      label: "contains",
    }));

    const c2RelEdges: GraphEdge[] = (c2Relationships || [])
      .map((rel) => {
        const sourceId = nameToC2Id.get(rel.fromC2) ?? rel.fromC2;
        const targetId = nameToC2Id.get(rel.toC2) ?? rel.toC2;
        if (!sourceId || !targetId) return null;
        return { id: rel.id, source: sourceId, target: targetId, label: rel.label };
      })
      .filter(notNull);

    const crossRelEdges: GraphEdge[] = (crossC1C2Relationships || [])
      .map((rel) => {
        const sourceId = nameToC2Id.get(rel.fromC2) ?? rel.fromC2;
        const targetId = nameToC2Id.get(rel.toC2) ?? rel.toC2;
        if (!sourceId || !targetId) return null;
        return { id: rel.id, source: sourceId, target: targetId, label: rel.label };
      })
      .filter(notNull);

    const allEdges: GraphEdge[] = [
      ...(graphEdges || []),
      ...edgesFromC1ToC2,
      ...edgesFromC2ContainsNodes,
      ...c2RelEdges,
      ...crossRelEdges,
    ];

    for (const e of allEdges) {
      if (e && e.source && e.target) {
        try {
          dag.setEdge(e.source, e.target);
        } catch {}
      }
    }

    dagre.layout(dag);

    const positionedGraphNodes: GraphNode[] = (graphNodes || []).map((node) => {
      const nd = dag.node(node.id) as { x: number; y: number; width?: number; height?: number } | undefined;
      if (!nd) {
        const pos = node.position ?? { x: node.x ?? 0, y: node.y ?? 0 };
        return { ...node, position: pos };
      }
      return {
        ...node,
        position: { x: nd.x - ((nd.width ?? 150) / 2), y: nd.y - ((nd.height ?? 50) / 2) },
        x: nd.x,
        y: nd.y,
      };
    });

    const positionedC1Nodes: GraphNode[] = (c1Outputs || []).map((node) => {
      const nd = dag.node(node.id) as { x: number; y: number; width?: number; height?: number } | undefined;
      if (!nd) return { ...node, position: node.position ?? { x: node.x ?? 0, y: node.y ?? 0 } };
      return { ...node, position: { x: nd.x - ((nd.width ?? 150) / 2), y: nd.y - ((nd.height ?? 50) / 2) }, x: nd.x, y: nd.y };
    });

    const positionedC2Nodes: GraphNode[] = (c2Subcategories || []).map((node) => {
      const nd = dag.node(node.id) as { x: number; y: number; width?: number; height?: number } | undefined;
      if (!nd) return { ...node, position: node.position ?? { x: node.x ?? 0, y: node.y ?? 0 } };
      return { ...node, position: { x: nd.x - ((nd.width ?? 150) / 2), y: nd.y - ((nd.height ?? 50) / 2) }, x: nd.x, y: nd.y };
    });

    return {
      graphNodes: positionedGraphNodes,
      c1Nodes: positionedC1Nodes,
      c2Nodes: positionedC2Nodes,
      edges: allEdges,
    };
  }
}
