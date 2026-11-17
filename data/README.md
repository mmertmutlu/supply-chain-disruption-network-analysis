# Data

The raw data is **not included** in this repository. It comes from the
**IFAC MIM 2025 Data Challenge – Complex Network Analysis track**
(https://conferences.ifac-control.org/mim2025/), and access requires registration with the challenge.

Place the two files below in this folder to reproduce the analysis.

## `nodes.csv`
| column | description |
|---|---|
| `id` | anonymised node id (`n0`, `n1`, …) |
| `location` | country (may be empty) |
| `products` | comma-separated product descriptions (may be empty) |

Note: in the original file some rows are wrapped in an extra pair of quotes. `src/pipeline.py → load_nodes()` handles this.

## `edges.csv`
| column | description |
|---|---|
| `source` | supplier node id |
| `target` | customer node id |

The sample used in this repository has 1,035 nodes and 6,529 directed edges.
