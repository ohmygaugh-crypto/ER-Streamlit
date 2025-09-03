"""
Cart simulator and recommendation display component
"""
import streamlit as st
import pandas as pd
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
    
    # Multi-select for cart items - simplified approach
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
    
    # Store cart metadata for main view metrics
    _store_cart_metadata(selected_products, meta)
    
    # Display current cart (without metrics - moved to main view)
    _display_current_cart_simple(selected_products, meta)
    
    # Generate recommendations (moved to top section, but still need to generate for session state)
    _generate_recommendations_for_state(cart_items, stats, config)
    
    # Quick Add to Cart with enhanced UIUX
    _render_enhanced_quick_add_interface()


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


def _store_cart_metadata(cart_items: List[str], meta: Dict[str, Dict]):
    """Store cart metadata in session state for main view metrics"""
    # Convert display names back to product IDs and calculate total value
    total_value = 0
    product_ids = []
    
    for item_display_name in cart_items:
        # Extract product name from display name
        product_name = item_display_name.split(" (")[0].strip()
        
        # Find matching product ID with improved matching
        for product_id, product_meta in meta.items():
            meta_product_name = product_meta.get("product_name", product_id)
            
            # Try exact match first, then partial matches
            if (meta_product_name.lower() == product_name.lower() or 
                product_name.lower() in meta_product_name.lower() or
                meta_product_name.lower() in product_name.lower()):
                
                product_ids.append(product_id)
                total_value += product_meta.get("price", 0)
                break
    
    # Store in session state
    st.session_state.cart_total_value = total_value
    st.session_state.current_meta = meta
    st.session_state.cart_product_ids = product_ids


def _display_current_cart_simple(cart_items: List[str], meta: Dict[str, Dict]):
    """Display current cart contents (simplified - no metrics)"""
    if not cart_items:
        return
    
    st.markdown("#### 🛍️ Current Cart")
    
    cart_data = []
    
    for item_display_name in cart_items:
        # Parse display name to extract product name, category, and price
        # Format: "Product Name (Category) - $Price" or variations
        
        # Initialize defaults
        product_name = item_display_name
        category = "Unknown"
        price_str = "N/A"
        
        # Extract category if present: "Product Name (Category)"
        if " (" in item_display_name and ")" in item_display_name:
            parts = item_display_name.split(" (", 1)
            product_name = parts[0].strip()
            category_and_price = parts[1]
            
            # Extract category: "(Category) - $Price" or just "(Category)"
            if ") - $" in category_and_price:
                category = category_and_price.split(") - $")[0].strip()
                price_part = category_and_price.split(") - $")[1].strip()
                price_str = f"${price_part}"
            elif ")" in category_and_price:
                category = category_and_price.split(")")[0].strip()
                # Check if there's a price after the category
                remaining = category_and_price.split(")", 1)[1].strip()
                if remaining.startswith(" - $"):
                    price_str = remaining[3:].strip()  # Remove " - $"
                    if price_str:
                        price_str = f"${price_str}"
        
        # If we didn't extract price from display name, try to get it from metadata
        if price_str == "N/A":
            # Find matching product in metadata
            for product_id, metadata in meta.items():
                meta_product_name = metadata.get("product_name", product_id)
                if (meta_product_name.lower() == product_name.lower() or 
                    product_name.lower() in meta_product_name.lower()):
                    price = metadata.get("price", 0)
                    if price > 0:
                        price_str = f"${price:.2f}"
                    if category == "Unknown":
                        category = metadata.get("category", "Unknown")
                    break
        
        cart_data.append({
            "Product": product_name,
            "Category": category,
            "Price": price_str
        })
    
    # Display cart table
    if cart_data:
        cart_df = pd.DataFrame(cart_data)
        st.dataframe(cart_df, use_container_width=True, hide_index=True)
    else:
        st.info("Cart items found but unable to display details.")


def _generate_recommendations_for_state(cart_items: List[str], stats: Dict[str, Any], config: Dict[str, Any]):
    """Generate recommendations and store in session state (display moved to top section)"""
    from src.core.recommender import RecommendationEngine
    
    # Convert display names back to product IDs for recommendation generation
    meta = stats["meta"]
    product_ids = []
    
    for item_display_name in cart_items:
        product_name = item_display_name.split(" (")[0].strip()
        
        # Find matching product ID with improved matching
        for product_id, metadata in meta.items():
            meta_product_name = metadata.get("product_name", product_id)
            
            # Try exact match first, then partial matches
            if (meta_product_name.lower() == product_name.lower() or 
                product_name.lower() in meta_product_name.lower() or
                meta_product_name.lower() in product_name.lower()):
                
                product_ids.append(product_id)
                break
    
    if not product_ids:
        # Store empty recommendations if no valid product IDs found
        st.session_state.current_recommendations = pd.DataFrame()
        return
    
    recommender = RecommendationEngine()
    
    try:
        # Generate recommendations
        recs_df = recommender.compute_recommendations(
            cart_items=product_ids,  # Use product IDs for recommendation generation
            item_stats=stats,
            topk=config["rec_k"],
            exclude_in_cart=True
        )
        
        if recs_df.empty:
            st.session_state.current_recommendations = pd.DataFrame()
            return
        
        # Add revenue uplift estimates
        recs_with_uplift = recommender.estimate_revenue_uplift(
            recs_df, 
            margin_percentage=config["margin_pct"]
        )
        
        # Store recommendations in session state for export and metrics
        old_recs = st.session_state.get("current_recommendations")
        st.session_state.current_recommendations = recs_with_uplift
        
        # Only reset index if recommendations actually changed or if index is out of bounds
        current_index = st.session_state.get("current_rec_index", 0)
        if (old_recs is None or 
            len(old_recs) != len(recs_with_uplift) or 
            current_index >= len(recs_with_uplift)):
            st.session_state.current_rec_index = 0
        
    except Exception as e:
        # Handle any errors in recommendation generation
        st.session_state.current_recommendations = pd.DataFrame()
        print(f"Error generating recommendations: {e}")


def _render_enhanced_quick_add_interface():
    """Render enhanced Quick Add to Cart with top recommendation as cyan rectangle"""
    current_recs = st.session_state.get("current_recommendations")
    
    if current_recs is None or current_recs.empty:
        return
    
    st.markdown("#### ⚡ Quick Add to Cart")
    
    # Initialize session state for recommendation index
    if "current_rec_index" not in st.session_state:
        st.session_state.current_rec_index = 0
    
    # Get current recommendation index
    rec_index = st.session_state.current_rec_index
    
    # Reset index if it exceeds available recommendations
    if rec_index >= len(current_recs):
        st.session_state.current_rec_index = 0
        rec_index = 0
    
    # Get the current top recommendation
    current_rec = current_recs.iloc[rec_index]
    product_name = current_rec["product_name"]
    category = current_rec["category"]
    price = current_rec["price"]
    confidence = current_rec["confidence_a_to_b"]
    
    # Create display name for cart
    if category and price > 0:
        display_name = f"{product_name} ({category}) - ${price:.2f}"
    elif category:
        display_name = f"{product_name} ({category})"
    elif price > 0:
        display_name = f"{product_name} - ${price:.2f}"
    else:
        display_name = product_name
    
    # Display recommendation info
    st.write(f"**Top Recommendation #{rec_index + 1}** (Confidence: {confidence:.1%})")
    
    # Create columns for the cyan rectangle and pass button
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Cyan clickable rectangle for the recommendation
        # Use callback-based approach for more reliable state management
        st.button(
            f"🛒 Add {product_name} to Cart",
            key=f"add_quick_{rec_index}_{len(current_recs)}",
            help=f"Add {product_name} ({category}) - ${price:.2f} to your cart",
            use_container_width=True,
            type="primary",
            on_click=_add_recommendation_callback
        )
    
    with col2:
        # Pass/Skip button
        st.button(
            "⏭️ Pass",
            key=f"pass_quick_{rec_index}_{len(current_recs)}",
            help="Skip this recommendation and see the next one",
            use_container_width=True,
            type="secondary",
            on_click=_skip_recommendation_callback
        )
    
    # Show progress
    total_recs = len(current_recs)
    st.progress((rec_index + 1) / total_recs, text=f"Recommendation {rec_index + 1} of {total_recs}")


def _add_recommendation_callback():
    """Callback function to add recommendation to cart"""
    # Get the recommendation details from session state
    current_recs = st.session_state.get("current_recommendations")
    if current_recs is None or current_recs.empty:
        return
    
    rec_index = st.session_state.get("current_rec_index", 0)
    if rec_index >= len(current_recs):
        return
    
    current_rec = current_recs.iloc[rec_index]
    product_name = current_rec["product_name"]
    category = current_rec["category"]
    price = current_rec["price"]
    
    # Create display name
    if category and price > 0:
        display_name = f"{product_name} ({category}) - ${price:.2f}"
    elif category:
        display_name = f"{product_name} ({category})"
    elif price > 0:
        display_name = f"{product_name} - ${price:.2f}"
    else:
        display_name = product_name
    
    # Get current cart
    current_cart = st.session_state.get("cart_items", [])
    
    if display_name not in current_cart:
        # Update cart
        st.session_state.cart_items = current_cart + [display_name]
        
        # Track selected recommendations
        selected_recs = st.session_state.get("selected_recommendations", [])
        selected_recs.append(product_name)
        st.session_state.selected_recommendations = selected_recs
        
        # Move to next recommendation
        st.session_state.current_rec_index += 1
        
        # Store success message to display in main view (prevents page jump)
        st.session_state.cart_success_message = f"✅ Added {product_name} to cart!"


def _add_recommendation_to_cart(display_name: str, product_name: str):
    """Legacy function - now just calls the callback"""
    _add_recommendation_callback()


def _skip_recommendation_callback():
    """Callback function to skip current recommendation"""
    current_recs = st.session_state.get("current_recommendations")
    
    if current_recs is not None and not current_recs.empty:
        st.session_state.current_rec_index += 1
        
        # If we've gone through all recommendations, reset to start
        if st.session_state.current_rec_index >= len(current_recs):
            st.session_state.current_rec_index = 0


def _skip_to_next_recommendation():
    """Legacy function - now just calls the callback"""
    _skip_recommendation_callback()









