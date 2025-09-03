"""
Cart simulator and recommendation display component
"""
import streamlit as st
import pandas as pd
import io
from typing import Dict, List, Any


def render_cart_simulator(stats: Dict[str, Any], config: Dict[str, Any]):
    """
    Render the cart simulator and recommendation interface
    
    Args:
        stats: Network statistics from analyzer
        config: Configuration from sidebar
    """
    st.markdown("### 🛒 Cart Simulator & Recommendations")
    
    meta = stats["meta"]
    
    # Create product selection interface
    product_options = _create_product_options(meta)
    
    # Multi-select for cart items
    selected_products = st.multiselect(
        "🛍️ Select items currently in cart:",
        options=list(product_options.keys()),
        help="Start typing to search for products",
        key="cart_items"
    )
    
    # Convert display names back to product IDs
    cart_items = [product_options[name] for name in selected_products]
    
    if not cart_items:
        st.info("🎯 Add at least one item to the cart to see recommendations.")
        return
    
    # Display current cart
    _display_current_cart(cart_items, meta)
    
    # Generate and display recommendations
    _display_recommendations(cart_items, stats, config)


def _create_product_options(meta: Dict[str, Dict]) -> Dict[str, str]:
    """Create display name to product ID mapping for selection"""
    options = {}
    for product_id, metadata in meta.items():
        display_name = metadata.get("product_name", product_id)
        category = metadata.get("category", "")
        price = metadata.get("price", 0)
        
        # Create descriptive display name
        if category and price > 0:
            full_name = f"{display_name} ({category}) - ${price:.2f}"
        elif category:
            full_name = f"{display_name} ({category})"
        elif price > 0:
            full_name = f"{display_name} - ${price:.2f}"
        else:
            full_name = display_name
        
        options[full_name] = product_id
    
    return dict(sorted(options.items()))


def _display_current_cart(cart_items: List[str], meta: Dict[str, Dict]):
    """Display current cart contents"""
    if not cart_items:
        return
    
    st.markdown("#### 🛍️ Current Cart")
    
    cart_data = []
    total_value = 0
    
    for product_id in cart_items:
        metadata = meta.get(product_id, {})
        name = metadata.get("product_name", product_id)
        category = metadata.get("category", "Unknown")
        price = metadata.get("price", 0)
        
        cart_data.append({
            "Product": name,
            "Category": category,
            "Price": f"${price:.2f}" if price > 0 else "N/A"
        })
        total_value += price
    
    # Display cart table
    cart_df = pd.DataFrame(cart_data)
    st.dataframe(cart_df, use_container_width=True, hide_index=True)
    
    # Show cart summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Items in Cart", len(cart_items))
    with col2:
        st.metric("Cart Value", f"${total_value:.2f}")


def _display_recommendations(cart_items: List[str], stats: Dict[str, Any], config: Dict[str, Any]):
    """Generate and display recommendations"""
    from src.core.recommender import RecommendationEngine
    
    recommender = RecommendationEngine()
    
    # Generate recommendations
    recs_df = recommender.compute_recommendations(
        cart_items=cart_items,
        item_stats=stats,
        topk=config["rec_k"],
        exclude_in_cart=True
    )
    
    if recs_df.empty:
        st.warning("⚠️ No recommendations available with current network thresholds. Try lowering the minimum support or lift values.")
        return
    
    # Add revenue uplift estimates
    recs_with_uplift = recommender.estimate_revenue_uplift(
        recs_df, 
        margin_percentage=config["margin_pct"]
    )
    
    st.markdown("#### 🎯 Recommended Add-Ons")
    
    # Display recommendations with metrics
    display_columns = [
        "product_name", "category", "price", "score", 
        "why_from", "lift", "confidence_a_to_b", "co_count",
        "est_acceptance_prob", "est_margin_uplift"
    ]
    
    # Rename columns for better display
    display_df = recs_with_uplift[display_columns].copy()
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
    
    # Show recommendation insights
    _display_recommendation_insights(recs_with_uplift, config)
    
    # Quick add to cart functionality
    _render_quick_add_interface(recs_with_uplift)
    
    # Export recommendations
    _render_recommendation_export(recs_with_uplift)


def _display_recommendation_insights(recs_df: pd.DataFrame, config: Dict[str, Any]):
    """Display insights about the recommendations"""
    if recs_df.empty:
        return
    
    st.markdown("#### 💡 Recommendation Insights")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_lift = recs_df["lift"].mean()
        st.metric("Avg Lift", f"{avg_lift:.2f}")
    
    with col2:
        total_uplift = recs_df["est_margin_uplift"].sum()
        st.metric("Total Est. Uplift", f"${total_uplift:.2f}")
    
    with col3:
        avg_confidence = recs_df["confidence_a_to_b"].mean()
        st.metric("Avg Confidence", f"{avg_confidence:.1%}")
    
    with col4:
        top_category = recs_df["category"].mode().iloc[0] if not recs_df["category"].empty else "N/A"
        st.metric("Top Category", top_category)


def _render_quick_add_interface(recs_df: pd.DataFrame):
    """Render quick add to cart interface"""
    if recs_df.empty:
        return
    
    st.markdown("#### ⚡ Quick Add to Cart")
    
    # Create selection dropdown
    rec_options = ["Select a recommendation..."] + recs_df["product_name"].tolist()
    
    selected_rec = st.selectbox(
        "Choose a recommendation to add:",
        options=rec_options,
        key="quick_add_select"
    )
    
    if selected_rec != "Select a recommendation...":
        if st.button("➕ Add to Cart", key="add_to_cart_btn"):
            # Find the product in the current cart items and add it
            current_cart = st.session_state.get("cart_items", [])
            
            # Convert product name back to display format for multiselect
            selected_row = recs_df[recs_df["product_name"] == selected_rec].iloc[0]
            category = selected_row["category"]
            price = selected_row["price"]
            
            if category and price > 0:
                display_name = f"{selected_rec} ({category}) - ${price:.2f}"
            elif category:
                display_name = f"{selected_rec} ({category})"
            elif price > 0:
                display_name = f"{selected_rec} - ${price:.2f}"
            else:
                display_name = selected_rec
            
            if display_name not in current_cart:
                current_cart.append(display_name)
                st.session_state["cart_items"] = current_cart
                st.success(f"✅ Added {selected_rec} to cart!")
                st.rerun()


def _render_recommendation_export(recs_df: pd.DataFrame):
    """Render recommendation export functionality"""
    if recs_df.empty:
        return
    
    st.markdown("#### 💾 Export Recommendations")
    
    # Prepare data for export
    export_df = recs_df.copy()
    
    # Create CSV buffer
    csv_buffer = io.StringIO()
    export_df.to_csv(csv_buffer, index=False)
    csv_data = csv_buffer.getvalue()
    
    st.download_button(
        label="📊 Download Recommendations CSV",
        data=csv_data,
        file_name="cart_recommendations.csv",
        mime="text/csv",
        help="Download detailed recommendations with all metrics"
    )
