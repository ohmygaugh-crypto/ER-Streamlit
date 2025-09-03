"""
Network graph visualization component
"""
import streamlit as st
import json
from typing import Dict, List, Any

# Import optional dependencies through centralized checker
from src.utils.imports import HAS_ST_LINK, ST_LINK_ANALYSIS, NODE_STYLE, EDGE_STYLE, check_st_link_analysis


def render_network_graph(elements: Dict[str, List[Dict]], config: Dict[str, Any], stats: Dict[str, Any]):
    """
    Render the interactive network graph visualization
    
    Args:
        elements: Graph elements (nodes and edges)
        config: Configuration from sidebar
        stats: Network statistics
    """
    st.markdown("### 🕸️ Product Co-Purchase Network")
    
    if not elements["nodes"]:
        st.warning("⚠️ No network data to display. Try lowering the support/lift thresholds.")
        return
    
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
    
    # Render interactive graph if available
    if HAS_ST_LINK and ST_LINK_ANALYSIS is not None:
        try:
            ST_LINK_ANALYSIS(
                elements,
                layout=config.get("layout_choice", "cose"),
                node_styles=[NODE_STYLE(
                    label="Product", 
                    color="#2A629A", 
                    caption="name"
                )],
                edge_styles=[EDGE_STYLE(
                    "CO_PURCHASE", 
                    caption="lift", 
                    directed=False
                )],
                key="product_network"
            )
        except Exception as e:
            st.error(f"Graph visualization error: {e}")
            _render_fallback_graph_info(elements, stats)
    else:
        st.warning("📦 Interactive graph not available. Install `st-link-analysis` for full visualization.")
        _render_fallback_graph_info(elements, stats)
    
    # Network statistics
    _render_network_stats(elements, stats)
    
    # Export functionality
    _render_export_section(elements)


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


def _render_network_stats(elements: Dict[str, List[Dict]], stats: Dict[str, Any]):
    """Render network analysis statistics"""
    st.markdown("#### 📊 Network Metrics")
    
    n_nodes = len(elements["nodes"])
    n_edges = len(elements["edges"])
    n_orders = stats["n_orders"]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Orders", f"{n_orders:,}")
    
    with col2:
        st.metric("Connected Products", n_nodes)
    
    with col3:
        st.metric("Product Pairs", n_edges)
    
    with col4:
        if n_nodes > 1:
            max_edges = n_nodes * (n_nodes - 1) / 2
            density = n_edges / max_edges
            st.metric("Network Density", f"{density:.1%}")


def _render_export_section(elements: Dict[str, List[Dict]]):
    """Render graph export functionality"""
    st.markdown("#### 💾 Export Network")
    
    graph_json = json.dumps(elements, indent=2)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="📄 Download Graph JSON",
            data=graph_json,
            file_name="product_network.json",
            mime="application/json",
            help="Download network data as JSON for external analysis"
        )
    
    with col2:
        # Create simple edge list for analysis tools
        edge_list = []
        for edge in elements["edges"]:
            edge_list.append({
                "source": edge["data"]["source"],
                "target": edge["data"]["target"],
                "lift": edge["data"]["lift"],
                "support": edge["data"]["support_ab"],
                "co_count": edge["data"]["co_count"]
            })
        
        import pandas as pd
        edge_df = pd.DataFrame(edge_list)
        csv_data = edge_df.to_csv(index=False)
        
        st.download_button(
            label="📊 Download Edge List CSV",
            data=csv_data,
            file_name="product_connections.csv",
            mime="text/csv",
            help="Download edge list for network analysis tools"
        )
