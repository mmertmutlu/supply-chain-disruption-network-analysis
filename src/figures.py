"""Figures for the README / notebook. Static PNGs (matplotlib)."""
import matplotlib.pyplot as plt
import networkx as nx

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e6e5e0"
ACCENT = "#2a78d6"      # single hue for magnitude
CRITICAL = "#d03b3b"    # highlight for the critical node(s)
STAGE_COLORS = {"Part": "#2a78d6", "Manuf": "#eb6834", "Dist": "#1baf7a", "Retail": "#eda100"}
STAGE_ORDER = ["Part", "Manuf", "Dist", "Retail"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "text.color": INK, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
})


def top_criticality_bar(sim, path, n=15):
    top = sim.sort_values("criticality", ascending=False).head(n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh([f"{i} ({s})" for i, s in zip(top.id, top.stage)], top.criticality,
            color=ACCENT, height=0.6)
    for y, v in enumerate(top.criticality):
        ax.text(v + 0.8, y, str(v), va="center", color=INK_2, fontsize=9)
    ax.set_xlabel("Firms cut off from every raw-material source if this node fails")
    ax.set_title(f"Top {n} critical nodes (single-node failure simulation)", loc="left", fontsize=12)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def risk_index_by_stage(wri, path, n=10):
    top = wri.head(n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(top.id, top.risk_index, color=[STAGE_COLORS[s] for s in top.stage], height=0.6)
    for y, (v, s) in enumerate(zip(top.risk_index, top.stage)):
        ax.text(v + 0.01, y, f"{v:.2f}  {s}", va="center", color=INK_2, fontsize=9)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Weighted Risk Index (0.5 downstream + 0.3 betweenness + 0.2 out-degree)")
    ax.set_title(f"Top {n} nodes by Weighted Risk Index, coloured by echelon", loc="left", fontsize=12)
    present = [s for s in STAGE_ORDER if s in set(top.stage)]
    handles = [plt.Rectangle((0, 0), 1, 1, color=STAGE_COLORS[s]) for s in present]
    ax.legend(handles, present, frameon=False, loc="lower right", title="Echelon")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def critical_node_neighbourhood(G, node, path):
    nbrs = set(G.predecessors(node)) | set(G.successors(node)) | {node}
    H = G.subgraph(nbrs)
    cols = {s: [] for s in STAGE_ORDER}
    for n in H:
        cols[H.nodes[n]["stage"]].append(n)
    pos = {}
    for x, s in enumerate(STAGE_ORDER):
        members = sorted(cols[s])
        for k, n in enumerate(members):
            pos[n] = (x, (k + 1) / (len(members) + 1))
    fig, ax = plt.subplots(figsize=(10, 6))
    nx.draw_networkx_edges(H, pos, ax=ax, edge_color=GRID, width=0.8, arrows=True, arrowsize=6)
    for s in STAGE_ORDER:
        ns = [n for n in cols[s] if n != node]
        nx.draw_networkx_nodes(H, pos, nodelist=ns, node_color=STAGE_COLORS[s], node_size=60,
                               edgecolors=SURFACE, linewidths=1, ax=ax, label=s)
    nx.draw_networkx_nodes(H, pos, nodelist=[node], node_color=CRITICAL, node_size=400,
                           edgecolors=SURFACE, linewidths=2, ax=ax, label=f"{node} (critical)")
    for x, s in enumerate(STAGE_ORDER):
        ax.text(x, 1.04, s, ha="center", color=INK_2, fontsize=11, transform=ax.transData)
    ax.set_ylim(-0.02, 1.1)
    ax.axis("off")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=5)
    ax.set_title(f"Direct suppliers and customers of the most critical node ({node})",
                 loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
