# streamlit run visualize_splink_networks_from_csv.py
import streamlit as st
import pandas as pd
import numpy as np
import jellyfish  # For quick string similarity (Levenshtein, Jaro, etc.)
import io
import uuid

from st_link_analysis import st_link_analysis, NodeStyle, EdgeStyle

# Try to import networkx, fall back to manual implementation if not available
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

# ----------------------
# CONFIG
# ----------------------
DEFAULT_NODE_LABEL = "Record"
DEFAULT_REL_TYPE = "SIMILAR"
DEFAULT_THRESHOLD = 0.80  # default similarity threshold
MAX_REDLINE_PREVIEW = 10  # how many top edges to preview with "red-lining"

st.set_page_config(page_title="CSV ER & Network Graph", layout="wide")
st.title("Entity Resolution on CSV (Network Graph)")

# ----------------------
# SIDEBAR: CSV UPLOAD
# ----------------------
st.sidebar.header("Upload CSV for Entity Resolution")
uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type=["csv"])

similarity_threshold = st.sidebar.slider(
    "Similarity Threshold",
    min_value=0.0,
    max_value=1.0,
    value=DEFAULT_THRESHOLD,
    step=0.01
)

# Choose which columns to compare
st.sidebar.header("Similarity Columns")
# The user can list (or guess) which columns in the CSV are relevant for measuring similarity
# We'll default to common ones from 'create_mock_data_csv.py': first_name, last_name, email_address, phone_number
default_cols = "first_name,last_name,email_address,phone_number"
similarity_cols_raw = st.sidebar.text_input(
    "Columns to compare (comma-separated):",
    value=default_cols
)
similarity_cols = [c.strip() for c in similarity_cols_raw.split(",") if c.strip()]

# If the user wants to see red-lining differences
show_redlining = st.sidebar.checkbox("Show red-lined differences for top pairs", value=True)

# Data and Graph placeholders
df = None
elements = {"nodes": [], "edges": []}


# ----------------------
# UTILITY FUNCTIONS
# ----------------------
def jaro_winkler_score(str1, str2):
    """Simple wrapper around jellyfish.jaro_winkler for string similarity."""
    return jellyfish.jaro_winkler_similarity(str1 or "", str2 or "")

def overall_similarity(row1, row2, cols):
    """
    Compute an average similarity across the provided columns.
    You could weight them or do more sophisticated logic.
    """
    scores = []
    for col in cols:
        val1 = str(row1.get(col, "")).lower()
        val2 = str(row2.get(col, "")).lower()
        if val1 == "" or val2 == "":
            # If one is empty, skip or treat as partial
            continue
        sim = jaro_winkler_score(val1, val2)
        scores.append(sim)
    if len(scores) == 0:
        return 0.0
    return sum(scores) / len(scores)

def redline_text(str1, str2):
    """
    A simplistic "red-lining" of differences:
    We'll highlight mismatched characters in red.
    This helps show how two strings differ.
    """
    # For brevity, let's just do a character-by-character compare:
    #   if they match, we keep them black; if not, we color them red.
    # In practice, you might do a diff algorithm for better results.
    out = []
    max_len = max(len(str1), len(str2))
    for i in range(max_len):
        c1 = str1[i] if i < len(str1) else ""
        c2 = str2[i] if i < len(str2) else ""
        if c1 == c2:
            out.append(c1)  # same char
        else:
            # highlight mismatch
            out.append(f"<span style='color:red'>{c1 or '_'}</span>")
    # If str2 is longer, we won't show it in the same line for now. 
    # You can adapt to show side-by-side. We'll keep it simple.
    return "".join(out)

def find_connected_components_manual(nodes, edges):
    """
    Manual implementation of connected components finding.
    Fallback when NetworkX is not available.
    """
    # Build adjacency list
    adj_list = {node: set() for node in nodes}
    for edge in edges:
        source = edge["data"]["source"]
        target = edge["data"]["target"]
        adj_list[source].add(target)
        adj_list[target].add(source)
    
    visited = set()
    components = []
    
    def dfs(node, component):
        if node in visited:
            return
        visited.add(node)
        component.add(node)
        for neighbor in adj_list[node]:
            dfs(neighbor, component)
    
    for node in nodes:
        if node not in visited:
            component = set()
            dfs(node, component)
            if component:  # Only add non-empty components
                components.append(component)
    
    return components


# ----------------------
# LOAD CSV & PROCESS
# ----------------------
if uploaded_file is not None:
    st.markdown("### Preview of Uploaded CSV Data")
    df = pd.read_csv(uploaded_file)
    st.dataframe(df.head(10))

    # Provide a "Run Entity Resolution" button
    if st.button("Run Entity Resolution"):
        # STEP 1: Generate nodes
        # We'll create one node per row, storing all row data as properties
        nodes = []
        for idx, row in df.iterrows():
            node_data = row.to_dict()
            node_data["id"] = str(idx)  # use row index as unique ID
            node_data["label"] = DEFAULT_NODE_LABEL
            # We'll store "name" as a short label for the node
            # e.g. we might use something like first_name + last_name or a subset
            # but for demonstration, let's just do "row index" or any chosen fields
            first_name = row.get("first_name", "")
            last_name = row.get("last_name", "")
            short_label = f"{first_name} {last_name}".strip()
            if not short_label.strip():
                short_label = f"Row-{idx}"
            node_data["name"] = short_label
            nodes.append({"data": node_data})

        # STEP 2: Pairwise similarity for edges
        # We'll do a naive all-pairs approach. For large data, you'd do blocking.
        edges = []
        for i in range(len(df)):
            for j in range(i + 1, len(df)):
                sim = overall_similarity(df.loc[i], df.loc[j], similarity_cols)
                if sim >= similarity_threshold:
                    edge_data = {
                        "id": f"edge_{i}_{j}",
                        "source": str(i),
                        "target": str(j),
                        "label": DEFAULT_REL_TYPE,
                        "similarity": round(sim, 3)
                    }
                    edges.append({"data": edge_data})

        elements = {"nodes": nodes, "edges": edges}
        st.success("Entity Resolution complete! Network graph built.")


        # ------------
        # Visualization
        st.markdown("### Network Graph")
        node_labels = set(node["data"]["label"] for node in elements["nodes"])
        rel_labels = set(edge["data"]["label"] for edge in elements["edges"])

        # Basic styling
        default_colors = ["#2A629A", "#FF7F3E", "#C0C0C0", "#008000", "#800080"]
        node_styles = []
        for i, label in enumerate(sorted(node_labels)):
            color = default_colors[i % len(default_colors)]
            node_styles.append(NodeStyle(label=label, color=color, caption="name"))

        edge_styles = []
        for rel in sorted(rel_labels):
            edge_styles.append(EdgeStyle(rel, caption="similarity", directed=False))

        st_link_analysis(
            elements,
            layout="cose",
            node_styles=node_styles,
            edge_styles=edge_styles
        )

        # ------------
        # Community Detection & CSV Export
        st.markdown("### Community Detection Results")
        
        # Find connected components (communities)
        if HAS_NETWORKX:
            # Use NetworkX if available
            G = nx.Graph()
            for node in elements["nodes"]:
                G.add_node(node["data"]["id"])
            for edge in elements["edges"]:
                G.add_edge(edge["data"]["source"], edge["data"]["target"])
            communities = list(nx.connected_components(G))
        else:
            # Use manual implementation as fallback
            st.info("NetworkX not found. Using manual connected components algorithm. Install NetworkX for better performance: `pip install networkx`")
            node_ids = [node["data"]["id"] for node in elements["nodes"]]
            communities = find_connected_components_manual(node_ids, elements["edges"])
        
        # Create a mapping from node_id to community_id
        node_to_community = {}
        community_uuids = {}
        
        for i, community in enumerate(communities):
            community_uuid = str(uuid.uuid4())
            community_uuids[i] = community_uuid
            for node_id in community:
                node_to_community[node_id] = community_uuid
        
        # Add community IDs to the original dataframe
        df_with_communities = df.copy()
        df_with_communities['community_id'] = [
            node_to_community.get(str(idx), str(uuid.uuid4())) 
            for idx in df_with_communities.index
        ]
        
        st.write(f"**Found {len(communities)} communities:**")
        for i, community in enumerate(communities):
            st.write(f"- Community {i+1}: {len(community)} records (UUID: {community_uuids[i]})")
        
        # Show the results dataframe
        st.markdown("#### Results with Community IDs")
        st.dataframe(df_with_communities)
        
        # CSV Export option
        st.markdown("#### Export Results")
        csv_buffer = io.StringIO()
        df_with_communities.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv_data,
            file_name="entity_resolution_results.csv",
            mime="text/csv"
        )

        # ------------
        # Red-lining (moved to bottom as lower priority)
        if show_redlining and len(edges) > 0:
            st.markdown("### Top Similar Pairs (Red-Lined Differences)")
            
            # Filter out exact matches (similarity == 1.0)
            filtered_edges = [
                edge for edge in edges if edge["data"]["similarity"] < 1.0
            ]
            
            # Sort by highest similarity (closest matches first)
            sorted_edges = sorted(filtered_edges, key=lambda e: e["data"]["similarity"], reverse=True)
            top_edges = sorted_edges[:MAX_REDLINE_PREVIEW]

            if not top_edges:
                st.info("No slightly different pairs found; all matches are exact or none meet the threshold.")
            else:
                for edge_item in top_edges:
                    s_idx = int(edge_item["data"]["source"])
                    t_idx = int(edge_item["data"]["target"])
                    sim_val = edge_item["data"]["similarity"]
                    st.markdown(f"**Pair:** Row {s_idx} ↔ Row {t_idx}, **similarity**={sim_val}")

                    # Highlight differences in selected columns
                    mismatch_cols = []
                    for col in similarity_cols:
                        val1 = str(df.loc[s_idx, col])
                        val2 = str(df.loc[t_idx, col])
                        if val1.lower() != val2.lower():
                            mismatch_cols.append((col, val1, val2))

                    if mismatch_cols:
                        st.write("Differences in the following columns:")
                        for col_name, str1, str2 in mismatch_cols:
                            redlined = redline_text(str1, str2)
                            st.markdown(f"&nbsp;&nbsp;**{col_name}:** {redlined}", unsafe_allow_html=True)
                    else:
                        st.write("No differences in the compared columns.")

                    st.markdown("---")

        # ------------
        # Enterprise Scale Note
        st.markdown("---")
        st.markdown("### 📈 Enterprise Scale Solutions")
        
        if not HAS_NETWORKX:
            st.warning("""
            **Missing NetworkX Dependency** 
            
            For better performance, install NetworkX:
            ```bash
            pip install networkx
            ```
            """)
        
        st.info("""
        **Need help with larger scale deployments?** 
        
        If you need to persist UUIDs from run to run, handle larger datasets, or require more sophisticated 
        entity resolution capabilities, you may need an enterprise-scale solution. Consider:
        
        - **Database Integration**: Store community IDs in a persistent database
        - **Incremental Processing**: Handle new data without re-processing everything
        - **Advanced Blocking**: Use more sophisticated blocking strategies for large datasets
        - **Distributed Computing**: Scale across multiple machines for very large datasets
        - **Custom ML Models**: Train domain-specific models for better accuracy
        
        Contact your data engineering team for guidance on enterprise implementations.
        """)

else:
    st.info("Please upload a CSV file in the sidebar to begin.")
