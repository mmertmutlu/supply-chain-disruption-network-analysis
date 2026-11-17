"""
Supply chain disruption analysis pipeline (PURE, Sabancı University, Fall 2025-26).

Steps
1. Load nodes/edges robustly (handles rows that are wrapped in quotes).
2. Classify nodes into Willems-style echelons (Part -> Manuf -> Dist -> Retail)
   using product keywords + topology.
3. Remove backward (hierarchy-violating) edges and break remaining cycles (DFS) -> DAG.
4. Re-assign source nodes AFTER cleaning (in-degree 0 => Part) so that nodes left
   without suppliers are not counted as "starved" in every scenario.
5. Weighted Risk Index: 0.5*downstream impact + 0.3*betweenness + 0.2*out-degree (min-max normalised).
6. Supply-starvation simulation: remove each node, count which nodes lose every path to a Part node.
   criticality = how many nodes a failure starves; vulnerability = in how many scenarios a node is starved.
"""
import csv
import io
from pathlib import Path

import networkx as nx
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

STAGE_RANK = {"Part": 1, "Manuf": 2, "Dist": 3, "Retail": 4}
RAW = ['coal', 'ore', 'acid', 'wood', 'limestone', 'uranium', 'sodium', 'raw', 'copper',
       'iron', 'manganese', 'steel', 'alumina', 'slime', 'pyrite']
MANUF = ['part of vehicle', 'assembly', 'engine', 'casting', 'transmission', 'semiconductor',
         'diode', 'transistor', 'led', 'device', 'unit', 'brake', 'system', 'sensor']
RETAIL = ['household', 'food', 'beverage', 'software', 'insurance', 'banking', 'finance',
          'real estate', 'apparel', 'textile', 'publishing', 'broadcasting']


def load_nodes(path):
    """Read the nodes file. Some rows are wrapped in an extra pair of quotes,
    which pandas reads as a single field; unwrap them first."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    rows = []
    for line in lines[1:]:
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1].replace('""', '"')
        rows.append(next(csv.reader([line]))[:3])
    df = pd.DataFrame(rows, columns=["id", "location", "products"])
    df = df.replace({"": None})
    return df


def semantic_stage(desc):
    if desc is None or pd.isna(desc):
        return "Unknown"
    d = str(desc).lower()
    if any(k in d for k in RAW):
        return "Part"
    if any(k in d for k in MANUF):
        return "Manuf"
    if any(k in d for k in RETAIL):
        return "Retail"
    return "Dist"


def build_dag(nodes, edges):
    G = nx.DiGraph()
    for r in nodes.itertuples():
        G.add_node(r.id, desc=r.products, location=r.location, label=semantic_stage(r.products))
    for r in edges.itertuples():
        if r.source in G and r.target in G and r.source != r.target:
            G.add_edge(r.source, r.target)
    stats = {"edges_in_file": len(edges), "edges_loaded": G.number_of_edges()}

    indeg, outdeg = dict(G.in_degree()), dict(G.out_degree())
    stage = {}
    for n in G:
        lab = G.nodes[n]["label"]
        if indeg[n] == 0:
            stage[n] = "Part"
        elif outdeg[n] == 0:
            stage[n] = "Retail"
        else:
            stage[n] = "Dist" if lab == "Unknown" else lab

    backward = [(u, v) for u, v in G.edges() if STAGE_RANK[stage[u]] > STAGE_RANK[stage[v]]]
    G.remove_edges_from(backward)
    cycle_edges = 0
    while True:
        try:
            cyc = nx.find_cycle(G, orientation="original")
        except nx.NetworkXNoCycle:
            break
        G.remove_edge(*cyc[-1][:2])
        cycle_edges += 1

    # Re-assign sources after cleaning: a node with no remaining supplier is an entry point.
    for n in G:
        if G.in_degree(n) == 0:
            stage[n] = "Part"
    nx.set_node_attributes(G, stage, "stage")
    stats.update(removed_backward=len(backward), removed_cycle=cycle_edges,
                 final_edges=G.number_of_edges(), nodes=G.number_of_nodes(),
                 stage_counts=pd.Series(stage).value_counts().to_dict())
    return G, stats


def weighted_risk_index(G, w=(0.5, 0.3, 0.2)):
    ds = {n: len(nx.descendants(G, n)) for n in G}
    bc = nx.betweenness_centrality(G)
    od = dict(G.out_degree())
    m = pd.DataFrame({"id": list(G), "downstream": [ds[n] for n in G],
                      "betweenness": [bc[n] for n in G], "out_degree": [od[n] for n in G]})
    norm = MinMaxScaler().fit_transform(m[["downstream", "betweenness", "out_degree"]])
    m["risk_index"] = norm @ list(w)
    m["stage"] = m["id"].map(nx.get_node_attributes(G, "stage"))
    m["products"] = m["id"].map(nx.get_node_attributes(G, "desc"))
    return m.sort_values("risk_index", ascending=False).reset_index(drop=True)


def starvation_simulation(G):
    parts = [n for n, s in G.nodes(data="stage") if s == "Part"]
    crit, vuln = {n: 0 for n in G}, {n: 0 for n in G}
    for x in G:
        H = G.copy()
        H.remove_node(x)
        reach = set()
        for p in parts:
            if p in H:
                reach.add(p)
                reach |= nx.descendants(H, p)
        starved = set(H) - reach
        crit[x] = len(starved)
        for n in starved:
            vuln[n] += 1
    df = pd.DataFrame({"id": list(G), "criticality": [crit[n] for n in G],
                       "vulnerability": [vuln[n] for n in G]})
    df["stage"] = df["id"].map(nx.get_node_attributes(G, "stage"))
    return df


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", default="data/nodes.csv")
    ap.add_argument("--edges", default="data/edges.csv")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    nodes = load_nodes(a.nodes)
    edges = pd.read_csv(a.edges)
    G, stats = build_dag(nodes, edges)
    print(json.dumps(stats, indent=2))
    Path(a.out).mkdir(exist_ok=True)
    wri = weighted_risk_index(G); wri.to_csv(f"{a.out}/weighted_risk_index.csv", index=False)
    sim = starvation_simulation(G); sim.to_csv(f"{a.out}/starvation_scores.csv", index=False)
    print(wri.head(10)[["id", "stage", "downstream", "risk_index"]].to_string(index=False))
    print(sim.sort_values("criticality", ascending=False).head(10).to_string(index=False))
    print(sim.sort_values("vulnerability", ascending=False).head(10).to_string(index=False))
    print("corr(crit, vuln) =", round(sim.criticality.corr(sim.vulnerability), 3))
