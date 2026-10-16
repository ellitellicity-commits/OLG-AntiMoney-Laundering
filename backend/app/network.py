"""Player relationship graph: players are linked when they share a device, payment method or address."""
from __future__ import annotations

import networkx as nx

from backend.app.store import DataStore


class PlayerGraph:
    def __init__(self, store: DataStore):
        self.store = store
        self.g = self._build()

    def _build(self) -> nx.Graph:
        li = self.store.linked
        shared = li[li.groupby(["identifier_type", "identifier_value"])["player_id"].transform("nunique") > 1]
        g = nx.Graph()
        for (itype, ival), grp in shared.groupby(["identifier_type", "identifier_value"]):
            members = sorted(grp["player_id"].unique())
            for i, a in enumerate(members):
                for b in members[i + 1:]:
                    if g.has_edge(a, b):
                        g[a][b]["shared"].append({"type": itype, "value": ival})
                    else:
                        g.add_edge(a, b, shared=[{"type": itype, "value": ival}])
        self._add_opposite_bets(g)
        return g

    def _add_opposite_bets(self, g: nx.Graph):
        if g.number_of_nodes() == 0:
            return
        t = self.store.transactions
        bets = t.loc[(t["type"] == "bet") & t["player_id"].isin(set(g.nodes)) & t["event_id"].notna(),
                     ["player_id", "event_id", "selection"]].astype(str)
        m = bets.merge(bets, on="event_id")
        m = m[(m["player_id_x"] < m["player_id_y"]) & (m["selection_x"] != m["selection_y"])]
        counts = m.groupby(["player_id_x", "player_id_y"]).size()
        for (a, b), n in counts.items():
            if g.has_edge(a, b):
                g[a][b]["opposite_bets"] = int(n)

    def neighbourhood(self, pid: str, hops: int = 2, max_nodes: int = 60) -> dict:
        scores = self.store.scores
        def node(p):
            row = scores.loc[p] if p in scores.index else None
            a = self.store.alert_by_player.get(p)
            return {"id": p, "score": int(row["score"]) if row is not None else 0,
                    "band": row["band"] if row is not None else "Low", "is_focus": p == pid,
                    "alert_id": a["alert_id"] if a else None}

        if pid not in self.g:
            return {"player_id": pid, "nodes": [node(pid)], "edges": [], "cluster_size": 1,
                    "cluster_avg_score": float(scores.loc[pid, "score"]) if pid in scores.index else 0.0,
                    "summary": "No shared devices, payment methods or addresses with other players."}
        reach = nx.single_source_shortest_path_length(self.g, pid, cutoff=hops)
        keep = sorted(reach, key=lambda p: (reach[p], p))[:max_nodes]
        sub = self.g.subgraph(keep)
        component = nx.node_connected_component(self.g, pid)
        nodes = [node(p) for p in keep]
        edges = [{"source": a, "target": b, "shared": d["shared"], "opposite_bets": d.get("opposite_bets", 0)}
                 for a, b, d in sub.edges(data=True)]
        comp_scores = [int(scores.loc[p, "score"]) for p in component if p in scores.index]
        avg = round(sum(comp_scores) / len(comp_scores), 1) if comp_scores else 0.0
        direct = list(self.g.neighbors(pid))
        types = sorted({s["type"].replace("_", " ") for n in direct for s in self.g[pid][n]["shared"]})
        opp = sum(self.g[pid][n].get("opposite_bets", 0) for n in direct)
        flagged = sum(1 for p in component if p != pid and p in scores.index and scores.loc[p, "score"] >= 40)
        summary = (f"Directly linked to {len(direct)} player(s) through shared {', '.join(types)}; "
                   f"cluster of {len(component)} players, {flagged} other(s) also on the alert queue.")
        if opp:
            summary += f" {opp} bet(s) on opposite sides of the same events as linked players."
        return {"player_id": pid, "nodes": nodes, "edges": edges, "cluster_size": len(component),
                "cluster_avg_score": avg, "summary": summary}

    def clusters(self, min_size: int = 3) -> list[dict]:
        scores = self.store.scores
        out = []
        for comp in nx.connected_components(self.g):
            if len(comp) < min_size:
                continue
            members = sorted(comp)
            sc = [int(scores.loc[p, "score"]) for p in members if p in scores.index]
            opp = sum(d.get("opposite_bets", 0) for _, _, d in self.g.subgraph(comp).edges(data=True))
            out.append({"players": members, "size": len(members), "max_score": max(sc) if sc else 0,
                        "avg_score": round(sum(sc) / len(sc), 1) if sc else 0.0, "opposite_bets": opp})
        return sorted(out, key=lambda c: (-c["max_score"], -c["size"]))


def get_graph(store: DataStore) -> PlayerGraph:
    """Build the graph once per store and reuse it."""
    if getattr(store, "_graph", None) is None:
        store._graph = PlayerGraph(store)
    return store._graph
