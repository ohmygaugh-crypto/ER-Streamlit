"""
Main view layout for the recommendation engine application
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any


def render_main_view(orders_df: pd.DataFrame, config: Dict[str, Any]):
    """
    Render the main application view with data processing and visualization
    
    Args:
        orders_df: Processed orders data
        config: Configuration from sidebar
    """
    # Add custom CSS for enhanced quick add interface
    st.markdown("""
    <style>
    /* Style for Quick Add to Cart button to appear cyan */
    div[data-testid="stButton"] > button[kind="primary"] {
        background-color: #00BCD4 !important;
        border-color: #00BCD4 !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #0097A7 !important;
        border-color: #0097A7 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(0, 188, 212, 0.3) !important;
    }
    
    /* Style for Pass button */
    div[data-testid="stButton"] > button[kind="secondary"] {
        background-color: #757575 !important;
        border-color: #757575 !important;
        color: white !important;
        border-radius: 8px !important;
    }
    
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background-color: #616161 !important;
        border-color: #616161 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Add API status widget at top
    from ..components.api_status import render_api_status_widget
    render_api_status_widget()
    
    if orders_df is None or orders_df.empty:
        st.warning("⚠️ No data available. Please check your data source configuration.")
        return
    
    # Process data and build network first
    stats, elements = _process_network_data(orders_df, config)
    
    if stats is None:
        return
    
    # Show processing results
    _render_processing_summary(stats)
    
    # Top section: Orders preview and recommendations table
    _render_top_section(orders_df, stats, config)
    
    # Main layout: Graph visualization and cart simulator
    _render_main_content(elements, stats, config)
    
    # Cart metrics and recommendation insights
    _render_cart_metrics_and_insights()
    
    # Explanation section
    _render_explanation_section()
    
    # Export network section
    _render_export_section(elements)


def _render_top_section(orders_df: pd.DataFrame, stats: Dict[str, Any], config: Dict[str, Any]):
    """Render top section with orders preview and recommendations table"""
    left_col, right_col = st.columns([1, 1])
    
    with left_col:
        st.markdown("### 📊 Orders Preview")
        sample_size = min(10, len(orders_df))
        st.dataframe(orders_df.sample(sample_size).sort_values("order_id"))
    
    with right_col:
        _render_recommendations_table(stats, config)


def _process_network_data(orders_df: pd.DataFrame, config: Dict[str, Any]):
    """Process orders data and build network elements"""
    with st.spinner("🔄 Computing item co‑occurrences and network metrics…"):
        try:
            # Get analyzer from session state
            analyzer = st.session_state.analyzer
            
            # Build network statistics
            stats = analyzer.build_item_stats(orders_df)
            
            # Build graph elements
            elements = analyzer.build_graph_elements(
                stats, 
                config['min_support'], 
                config['min_lift'], 
                config['max_edges']
            )
            
            return stats, elements
            
        except Exception as e:
            st.error(f"❌ Error processing network data: {str(e)}")
            return None, None


def _render_processing_summary(stats: Dict[str, Any]):
    """Display processing results summary"""
    n_orders = stats["n_orders"]
    n_products = len(stats["meta"])
    n_pairs = len(stats["pairs"])
    
    st.success(f"✅ Processed {n_orders} orders • {n_products} products • {n_pairs} pairs")


def _render_main_content(elements: Dict[str, Any], stats: Dict[str, Any], config: Dict[str, Any]):
    """Render main content area with graph and cart simulator"""
    from src.ui.components.graph_viz import render_network_graph
    from src.ui.components.cart_simulator import render_cart_simulator
    
    # Create two-column layout
    left_col, right_col = st.columns([2, 1])
    
    with left_col:
        render_network_graph(elements, config, stats)
    
    with right_col:
        render_cart_simulator(stats, config)


def _render_explanation_section():
    """Render the explanation/documentation section"""
    st.divider()
    
    with st.expander("📚 How this demo works", expanded=False):
        st.markdown("""
        ### 🔗 Network Definition
        - **Nodes** represent **products**; **edges** connect products frequently bought together
        - **Edge attributes**: 
          - **Support** (fraction of orders containing both items A & B)
          - **Confidence** (P(B|A) - probability of buying B given A is in cart)
          - **Lift** (co-occurrence strength relative to independence)
        - Graph filters by minimum **pair support** and **lift**; edge count capped for performance

        ### 🎯 Recommendation Algorithm
        - For cart items S, each candidate item t gets scored by:
          ```
          score(t) = Σ[s∈S] lift(s,t) × log(1 + co_count(s,t))
          ```
        - We report the strongest contributing edge as the **"why this item"** explanation
        - Recommendations ranked by aggregated score from all cart items

        ### 💰 Revenue Uplift Estimation
        - **Acceptance probability** estimated by normalizing scores (capped at 60% for demo)
        - **Expected margin uplift** = acceptance_prob × item_price × margin_percentage
        - Adjust *Margin %* slider to simulate different business scenarios

        ### 🏘️ Community Detection
        - When NetworkX is available, detects connected components as product communities
        - Communities represent natural product groupings (e.g., breakfast items, cooking essentials)
        - Nodes colored by community membership in visualization

        ### 📊 Data Requirements
        Upload CSV with columns: `order_id, customer_id, order_timestamp, product_id, product_name, category, price, quantity`
        
        The app auto-maps common aliases (e.g., `sku`→`product_id`, `item_name`→`product_name`)
        """)
    
    st.caption("💡 **Tip**: Use threshold sliders to reveal market basket structure, then leverage those insights for targeted cart add‑ons!")


def _render_recommendations_table(stats: Dict[str, Any], config: Dict[str, Any]):
    """Render recommendations table in top section"""
    st.markdown("### 🎯 Recommended Add-Ons")
    
    # Get cart items from session state
    cart_items = st.session_state.get("cart_items", [])
    
    if not cart_items:
        st.info("🛍️ Add items to your cart to see recommendations.")
        return
    
    # Get current recommendations from session state
    current_recs = st.session_state.get("current_recommendations")
    
    if current_recs is not None and not current_recs.empty:
        # Display recommendations with metrics
        display_columns = [
            "product_name", "category", "price", "score", 
            "why_from", "lift", "confidence_a_to_b", "co_count",
            "est_acceptance_prob", "est_margin_uplift"
        ]
        
        # Rename columns for better display
        display_df = current_recs[display_columns].copy()
        display_df.columns = [
            "Product", "Category", "Price ($)", "Score", 
            "Triggered By", "Lift", "Confidence", "Co-purchases",
            "Accept Prob", "Est. Margin ($)"
        ]
        
        # Format numeric columns
        display_df["Price ($)"] = display_df["Price ($)"].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A")
        display_df["Score"] = display_df["Score"].apply(lambda x: f"{x:.2f}")
        display_df["Lift"] = display_df["Lift"].apply(lambda x: f"{x:.2f}")
        display_df["Confidence"] = display_df["Confidence"].apply(lambda x: f"{x:.1%}")
        display_df["Accept Prob"] = display_df["Accept Prob"].apply(lambda x: f"{x:.1%}")
        display_df["Est. Margin ($)"] = display_df["Est. Margin ($)"].apply(lambda x: f"{x:.2f}")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("⚠️ No recommendations available. Try lowering the minimum support or lift values.")





def _render_cart_metrics_and_insights():
    """Render cart metrics and recommendation insights"""
    # Get cart items from session state
    cart_items = st.session_state.get("cart_items", [])
    current_recs = st.session_state.get("current_recommendations")
    selected_recs = st.session_state.get("selected_recommendations", [])
    
    if not cart_items:
        st.info("🎯 Add items to your cart to see metrics and insights.")
        return
    
    st.divider()
    
    # Calculate cart metrics
    cart_value = _calculate_cart_value(cart_items)
    items_in_cart = len(cart_items)
    
    # Calculate recommendation metrics
    recommended_add_ons_selected = len(selected_recs)
    upselling_percentage = _calculate_upselling_percentage(cart_value, selected_recs)
    
    # Display cart success message if available (moved from callback to prevent page jump)
    if "cart_success_message" in st.session_state:
        st.success(st.session_state.cart_success_message)
        # Clear the message after displaying
        del st.session_state.cart_success_message
    
    # Display cart metrics
    st.markdown("### 🛍️ Cart & Upselling Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Items in Cart", items_in_cart)
    
    with col2:
        st.metric("Cart Value", f"${cart_value:.2f}")
    
    with col3:
        st.metric("Recommended Add-ons Selected", recommended_add_ons_selected)
    
    with col4:
        st.metric("% Increase in Upselling", f"{upselling_percentage:.1f}%")
    
    # Display recommendation insights if available
    if current_recs is not None and not current_recs.empty:
        st.markdown("### 💡 Recommendation Insights")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_lift = current_recs["lift"].mean()
            st.metric("Avg Lift", f"{avg_lift:.2f}")
        
        with col2:
            total_uplift = current_recs["est_margin_uplift"].sum()
            st.metric("Total Est. Uplift", f"${total_uplift:.2f}")
        
        with col3:
            avg_confidence = current_recs["confidence_a_to_b"].mean()
            st.metric("Avg Confidence", f"{avg_confidence:.1%}")
        
        with col4:
            top_category = current_recs["category"].mode().iloc[0] if not current_recs["category"].empty else "N/A"
            st.metric("Top Category", top_category)


def _calculate_cart_value(cart_items):
    """Calculate total value of items in cart"""
    # This is a simplified calculation - in a real app, you'd get this from session state or database
    # For now, we'll use a placeholder calculation
    if hasattr(st.session_state, 'cart_total_value'):
        return st.session_state.cart_total_value
    
    # Fallback calculation if not stored in session state
    total = 0
    meta = st.session_state.get('current_meta', {})
    
    for item_display_name in cart_items:
        # Extract product_id from display name (this is a simplified approach)
        for product_id, product_meta in meta.items():
            product_name = product_meta.get("product_name", product_id)
            if product_name in item_display_name:
                total += product_meta.get("price", 0)
                break
    
    return total


def _calculate_upselling_percentage(original_cart_value, selected_recommendations):
    """Calculate percentage increase due to selected recommendations"""
    if original_cart_value == 0 or not selected_recommendations:
        return 0.0
    
    # Calculate value of selected recommendations
    selected_value = 0
    current_recs = st.session_state.get("current_recommendations")
    
    if current_recs is not None and not current_recs.empty:
        for rec_name in selected_recommendations:
            matching_recs = current_recs[current_recs["product_name"] == rec_name]
            if not matching_recs.empty:
                selected_value += matching_recs.iloc[0]["price"]
    
    if selected_value == 0:
        return 0.0
    
    return (selected_value / original_cart_value) * 100


def _render_export_section(elements: Dict[str, Any]):
    """Render export functionality for both network and recommendations"""
    import json
    import io
    
    st.markdown("### 💾 Export Data")
    
    # Create tabs for different export types
    tab1, tab2 = st.tabs(["🕸️ Network Data", "🎯 Recommendations"])
    
    with tab1:
        st.markdown("#### Export Network")
        
        if not elements or not elements.get("nodes"):
            st.info("No network data available to export.")
        else:
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
                for edge in elements.get("edges", []):
                    edge_list.append({
                        "source": edge["data"]["source"],
                        "target": edge["data"]["target"],
                        "lift": edge["data"]["lift"],
                        "support": edge["data"]["support_ab"],
                        "co_count": edge["data"]["co_count"]
                    })
                
                if edge_list:
                    edge_df = pd.DataFrame(edge_list)
                    csv_data = edge_df.to_csv(index=False)
                    
                    st.download_button(
                        label="📊 Download Edge List CSV",
                        data=csv_data,
                        file_name="product_connections.csv",
                        mime="text/csv",
                        help="Download edge list for network analysis tools"
                    )
                else:
                    st.info("No network connections to export.")
    
    with tab2:
        st.markdown("#### Export Recommendations")
        
        # Check if recommendations are available in session state
        current_recs = st.session_state.get("current_recommendations")
        
        if current_recs is not None and not current_recs.empty:
            # Prepare data for export
            export_df = current_recs.copy()
            
            # Create CSV buffer
            csv_buffer = io.StringIO()
            export_df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label="📊 Download Recommendations CSV",
                    data=csv_data,
                    file_name="cart_recommendations.csv",
                    mime="text/csv",
                    help="Download detailed recommendations with all metrics"
                )
            
            with col2:
                # Show summary of what will be exported
                st.info(f"📋 Ready to export {len(current_recs)} recommendations with metrics including lift, confidence, and revenue uplift estimates.")
                
        else:
            st.info("🎯 No recommendations available to export. Add items to your cart to generate recommendations first.")
