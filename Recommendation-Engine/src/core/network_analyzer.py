"""
Network analysis for market basket analysis and co-purchase patterns
"""
import pandas as pd
import numpy as np
import streamlit as st
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any

# Optional networkx import
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


class NetworkAnalyzer:
    """Analyzes co-purchase networks and computes market basket metrics"""
    
    def __init__(self):
        self.color_palette = [
            "#2A629A", "#FF7F3E", "#4CAF50", "#9C27B0", "#FFC107",
            "#00BCD4", "#E91E63", "#8BC34A", "#795548", "#607D8B"
        ]
    
    @st.cache_data(show_spinner=False)
    def build_item_stats(_self, orders_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Build comprehensive item statistics including support, confidence, and lift
        
        Args:
            orders_df: DataFrame with order data
            
        Returns:
            Dictionary containing:
            - n_orders: Total number of orders
            - item_support: Dict of item_id -> support (frequency)
            - pairs: DataFrame of item pairs with metrics
            - meta: Dict of item metadata
        """
        # Ensure correct data types
        orders_df = orders_df.copy()
        orders_df["order_id"] = orders_df["order_id"].astype(str)
        orders_df["product_id"] = orders_df["product_id"].astype(str)
        orders_df["quantity"] = orders_df["quantity"].astype(float)
        
        # Create basket view: order_id -> set of product_ids
        grouped = orders_df.groupby("order_id")["product_id"].apply(
            lambda s: set(s.tolist())
        ).reset_index()
        baskets = grouped["product_id"].tolist()
        
        # Calculate item support (frequency)
        item_counts = Counter()
        for basket in baskets:
            item_counts.update(basket)
        
        n_orders = len(baskets)
        item_support = {item: count / n_orders for item, count in item_counts.items()}
        
        # Calculate co-occurrence counts
        co_counts = defaultdict(int)
        for basket in baskets:
            items_list = sorted(list(basket))
            for i in range(len(items_list)):
                for j in range(i + 1, len(items_list)):
                    co_counts[(items_list[i], items_list[j])] += 1
        
        # Build pairs dataframe with market basket metrics
        pair_rows = []
        for (item_a, item_b), co_count in co_counts.items():
            support_a = item_support.get(item_a, 1e-12)
            support_b = item_support.get(item_b, 1e-12)
            support_ab = co_count / n_orders
            
            # Confidence: P(B|A) and P(A|B)
            confidence_a_to_b = support_ab / max(support_a, 1e-12)
            confidence_b_to_a = support_ab / max(support_b, 1e-12)
            
            # Lift: how much more likely are A and B to be bought together
            # than if they were independent
            lift = support_ab / max(support_a * support_b, 1e-12)
            
            pair_rows.append({
                "item_a": item_a,
                "item_b": item_b,
                "support_ab": support_ab,
                "confidence_a_to_b": confidence_a_to_b,
                "confidence_b_to_a": confidence_b_to_a,
                "lift": lift,
                "co_count": co_count
            })
        
        pairs_df = pd.DataFrame(pair_rows)
        
        # Extract item metadata
        meta = orders_df.drop_duplicates("product_id")[
            ["product_id", "product_name", "category", "price"]
        ].set_index("product_id").to_dict(orient="index")
        
        return {
            "n_orders": n_orders,
            "item_support": item_support,
            "pairs": pairs_df,
            "meta": meta
        }
    
    def build_graph_elements(
        self, 
        item_stats: Dict[str, Any], 
        min_support: float, 
        min_lift: float, 
        max_edges: int = 5000
    ) -> Dict[str, List[Dict]]:
        """
        Build graph elements (nodes and edges) for visualization
        
        Args:
            item_stats: Output from build_item_stats
            min_support: Minimum support threshold
            min_lift: Minimum lift threshold
            max_edges: Maximum number of edges to include
            
        Returns:
            Dictionary with 'nodes' and 'edges' lists
        """
        pairs_df = item_stats["pairs"]
        meta = item_stats["meta"]
        item_support = item_stats["item_support"]
        
        # Filter pairs by thresholds
        filtered_pairs = pairs_df[
            (pairs_df["support_ab"] >= min_support) & 
            (pairs_df["lift"] >= min_lift)
        ].copy()
        
        # Limit edges for performance
        filtered_pairs = filtered_pairs.sort_values("lift", ascending=False).head(max_edges)
        
        # Build nodes
        node_ids = set(filtered_pairs["item_a"]).union(set(filtered_pairs["item_b"]))
        nodes = []
        
        for product_id in node_ids:
            metadata = meta.get(product_id, {
                "product_name": product_id, 
                "category": "", 
                "price": np.nan
            })
            
            nodes.append({
                "data": {
                    "id": product_id,
                    "label": "Product",
                    "name": metadata.get("product_name", product_id),
                    "category": metadata.get("category", ""),
                    "price": metadata.get("price", np.nan),
                    "support": float(item_support.get(product_id, 0.0))
                }
            })
        
        # Build edges
        edges = []
        for _, row in filtered_pairs.iterrows():
            edges.append({
                "data": {
                    "id": f"e_{row.item_a}_{row.item_b}",
                    "source": row.item_a,
                    "target": row.item_b,
                    "label": "CO_PURCHASE",
                    "lift": float(row.lift),
                    "support_ab": float(row.support_ab),
                    "confidence_a_to_b": float(row.confidence_a_to_b),
                    "confidence_b_to_a": float(row.confidence_b_to_a),
                    "co_count": int(row.co_count)
                }
            })
        
        return {"nodes": nodes, "edges": edges}
    
    def detect_communities(self, elements: Dict[str, List[Dict]]) -> Tuple[Dict[str, int], int]:
        """
        Detect communities in the product network
        
        Args:
            elements: Graph elements from build_graph_elements
            
        Returns:
            Tuple of (node_to_community_mapping, num_communities)
        """
        if not HAS_NETWORKX:
            # Fallback: assign all nodes to community 0
            node_mapping = {node["data"]["id"]: 0 for node in elements["nodes"]}
            return node_mapping, 1
        
        # Build NetworkX graph
        G = nx.Graph()
        
        for node in elements["nodes"]:
            G.add_node(node["data"]["id"])
        
        for edge in elements["edges"]:
            G.add_edge(
                edge["data"]["source"], 
                edge["data"]["target"], 
                weight=edge["data"].get("lift", 1.0)
            )
        
        # Use connected components as a simple community detection method
        components = list(nx.connected_components(G))
        
        # Create mapping from node to community ID
        node_mapping = {}
        for community_id, component in enumerate(components):
            for node_id in component:
                node_mapping[node_id] = community_id
        
        return node_mapping, len(components)
    
    def add_community_colors(
        self, 
        elements: Dict[str, List[Dict]], 
        node_to_community: Dict[str, int], 
        num_communities: int
    ) -> Dict[str, List[Dict]]:
        """
        Add community-based colors to graph elements
        
        Args:
            elements: Graph elements
            node_to_community: Node to community mapping
            num_communities: Total number of communities
            
        Returns:
            Updated elements with color information
        """
        # Create color mapping
        community_colors = {
            i: self.color_palette[i % len(self.color_palette)] 
            for i in range(max(1, num_communities))
        }
        
        # Add colors to nodes
        for node in elements["nodes"]:
            node_id = node["data"]["id"]
            community = node_to_community.get(node_id, 0)
            node["data"]["color"] = community_colors.get(community, "#888888")
        
        return elements
