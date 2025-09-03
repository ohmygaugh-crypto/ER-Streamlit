"""
Network graph visualization component
"""
import streamlit as st
from typing import Dict, List, Any

# Import optional dependencies through centralized checker
from src.utils.imports import HAS_ST_LINK, ST_LINK_ANALYSIS, NODE_STYLE, EDGE_STYLE, check_st_link_analysis


def render_network_graph(elements: Dict[str, List[Dict]], config: Dict[str, Any], stats: Dict[str, Any]):
    """
    Render the interactive network graph visualization with dynamic highlighting
    
    Args:
        elements: Graph elements (nodes and edges)
        config: Configuration from sidebar
        stats: Network statistics
    """
    st.markdown("### 🕸️ Product Co-Purchase Network")
    
    if not elements["nodes"]:
        st.warning("⚠️ No network data to display. Try lowering the support/lift thresholds.")
        return
    
    # Add dynamic highlighting based on cart and recommendations
    elements = _add_dynamic_highlighting(elements)
    
    # Add community detection and coloring if enabled
    if config.get("show_communities", True):
        try:
            from src.core.network_analyzer import NetworkAnalyzer
            analyzer = NetworkAnalyzer()
            node_to_comm, n_comms = analyzer.detect_communities(elements)
            elements = analyzer.add_community_colors(elements, node_to_comm, n_comms)
            
            st.info(f"🏘️ Detected **{n_comms}** product communities")
        except Exception as e:
            st.warning(f"Community detection failed: {e}")
    
    # Show highlighting legend
    _render_highlighting_legend()
    
    # Render interactive graph if available
    if HAS_ST_LINK and ST_LINK_ANALYSIS is not None:
        try:
            ST_LINK_ANALYSIS(
                elements,
                layout=config.get("layout_choice", "cose"),
                node_styles=[
                    NODE_STYLE(label="Product", color="#2A629A", caption="name"),
                    NODE_STYLE(label="CartItem", color="#FF6B6B", caption="name"),  # Red for cart items
                    NODE_STYLE(label="Recommended", color="#4ECDC4", caption="name"),  # Teal for recommendations
                ],
                edge_styles=[
                    EDGE_STYLE("CO_PURCHASE", caption="lift", directed=False),
                    EDGE_STYLE("RECOMMENDATION_EDGE", caption="lift", directed=False, color="#FFD93D"),  # Yellow for recommendation edges
                ],
                key="product_network"
            )
        except Exception as e:
            st.error(f"Graph visualization error: {e}")
            _render_fallback_graph_info(elements, stats)
    else:
        st.warning("📦 Interactive graph not available. Install `st-link-analysis` for full visualization.")
        _render_fallback_graph_info(elements, stats)


def _render_fallback_graph_info(elements: Dict[str, List[Dict]], stats: Dict[str, Any]):
    """Render basic graph information when interactive viz is not available"""
    n_nodes = len(elements["nodes"])
    n_edges = len(elements["edges"])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Products (Nodes)", n_nodes)
    with col2:
        st.metric("Connections (Edges)", n_edges)
    with col3:
        if n_nodes > 0:
            density = (2 * n_edges) / (n_nodes * (n_nodes - 1)) if n_nodes > 1 else 0
            st.metric("Network Density", f"{density:.3f}")
    
    # Show top connections
    if elements["edges"]:
        st.markdown("#### 🔗 Strongest Product Connections")
        
        # Sort edges by lift
        sorted_edges = sorted(
            elements["edges"], 
            key=lambda x: x["data"]["lift"], 
            reverse=True
        )[:10]
        
        connection_data = []
        for edge in sorted_edges:
            source_name = next(
                (n["data"]["name"] for n in elements["nodes"] 
                 if n["data"]["id"] == edge["data"]["source"]), 
                edge["data"]["source"]
            )
            target_name = next(
                (n["data"]["name"] for n in elements["nodes"] 
                 if n["data"]["id"] == edge["data"]["target"]), 
                edge["data"]["target"]
            )
            
            connection_data.append({
                "Product A": source_name,
                "Product B": target_name,
                "Lift": f"{edge['data']['lift']:.2f}",
                "Support": f"{edge['data']['support_ab']:.3f}",
                "Co-purchases": edge["data"]["co_count"]
            })
        
        st.dataframe(connection_data, use_container_width=True)


def _add_dynamic_highlighting(elements: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """Add dynamic highlighting to graph elements based on cart and recommendations"""
    # Get cart items and recommendations from session state
    cart_product_ids = st.session_state.get("cart_product_ids", [])
    current_recs = st.session_state.get("current_recommendations")
    
    # Create sets for faster lookup
    cart_ids = set(cart_product_ids)
    recommended_ids = set()
    recommendation_edges = set()
    
    # Extract recommended product IDs and their relationships to cart items
    if current_recs is not None and not current_recs.empty:
        for _, rec in current_recs.iterrows():
            rec_product_id = rec.get("product_id")
            if rec_product_id:
                recommended_ids.add(rec_product_id)
                
                # Find edges between cart items and this recommendation
                why_from = rec.get("why_from")  # The cart item that triggered this recommendation
                if why_from and why_from in cart_ids:
                    recommendation_edges.add((why_from, rec_product_id))
                    recommendation_edges.add((rec_product_id, why_from))  # Bidirectional
    
    # Create a copy of elements to modify
    highlighted_elements = {
        "nodes": [],
        "edges": []
    }
    
    # Update node labels and colors based on their role
    for node in elements["nodes"]:
        node_copy = node.copy()
        node_id = node["data"]["id"]
        
        if node_id in cart_ids:
            # Highlight cart items in red
            node_copy["data"]["label"] = "CartItem"
            node_copy["data"]["color"] = "#FF6B6B"  # Red
        elif node_id in recommended_ids:
            # Highlight recommended items in teal
            node_copy["data"]["label"] = "Recommended" 
            node_copy["data"]["color"] = "#4ECDC4"  # Teal
        else:
            # Keep default styling
            node_copy["data"]["label"] = "Product"
            # Preserve existing community colors if present
            if "color" not in node_copy["data"]:
                node_copy["data"]["color"] = "#2A629A"  # Default blue
        
        highlighted_elements["nodes"].append(node_copy)
    
    # Update edge labels and colors for recommendation relationships
    for edge in elements["edges"]:
        edge_copy = edge.copy()
        source = edge["data"]["source"]
        target = edge["data"]["target"]
        
        # Check if this edge represents a recommendation relationship
        if (source, target) in recommendation_edges or (target, source) in recommendation_edges:
            edge_copy["data"]["label"] = "RECOMMENDATION_EDGE"
            edge_copy["data"]["color"] = "#FFD93D"  # Yellow
            # Make recommendation edges thicker
            edge_copy["data"]["width"] = 4
        else:
            # Keep default edge styling
            edge_copy["data"]["label"] = "CO_PURCHASE"
            # Preserve existing edge properties
        
        highlighted_elements["edges"].append(edge_copy)
    
    return highlighted_elements


def _render_highlighting_legend():
    """Render a legend explaining the graph highlighting"""
    if (st.session_state.get("cart_product_ids") or 
        (st.session_state.get("current_recommendations") is not None and 
         not st.session_state.get("current_recommendations").empty)):
        
        st.markdown("#### 🎨 Graph Highlighting Legend")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            🔴 **Cart Items**  
            Products currently in your cart
            """)
        
        with col2:
            st.markdown("""
            🟢 **Recommended Items**  
            AI-suggested products based on your cart
            """)
        
        with col3:
            st.markdown("""
            🟡 **Recommendation Edges**  
            Relationships driving the recommendations
            """)
        
        st.markdown("---")






