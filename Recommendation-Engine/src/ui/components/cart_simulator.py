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
    
    # Multi-select for cart items with Quick Add bypass support
    # Handle Quick Add updates by temporarily managing the widget state
    if "_temp_cart_update" in st.session_state:
        # Temporarily clear the cart_items key to allow us to set a new default
        if "cart_items" in st.session_state:
            del st.session_state.cart_items
        
        # Get the updated cart from temporary state
        updated_cart = st.session_state._temp_cart_update
        del st.session_state._temp_cart_update
        
        # Create multiselect with the updated default
        selected_products = st.multiselect(
            "🛍️ Select items currently in cart:",
            options=list(product_options.keys()),
            default=updated_cart,
            help="Start typing to search for products",
            key="cart_items"
        )
    else:
        # Normal multiselect behavior
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
    _store_cart_metadata(cart_items, meta)
    
    # Display current cart (without metrics - moved to main view)
    _display_current_cart_simple(cart_items, meta)
    
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
        # Extract product name from display name (format: "Product Name (Category) - $Price")
        product_name = item_display_name.split(" (")[0].strip()
        
        # Find matching product metadata with improved matching
        matched = False
        for product_id, metadata in meta.items():
            meta_product_name = metadata.get("product_name", product_id)
            
            # Try exact match first, then partial matches
            if (meta_product_name.lower() == product_name.lower() or 
                product_name.lower() in meta_product_name.lower() or
                meta_product_name.lower() in product_name.lower()):
                
                category = metadata.get("category", "Unknown")
                price = metadata.get("price", 0)
                
                cart_data.append({
                    "Product": meta_product_name,
                    "Category": category,
                    "Price": f"${price:.2f}" if price > 0 else "N/A"
                })
                matched = True
                break
        
        # If no match found, show the extracted name anyway
        if not matched:
            cart_data.append({
                "Product": product_name,
                "Category": "Unknown",
                "Price": "N/A"
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
        st.session_state.current_recommendations = recs_with_uplift
        
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
        if st.button(
            f"🛒 Add {product_name} to Cart",
            key=f"add_rec_{rec_index}",
            help=f"Add {product_name} ({category}) - ${price:.2f} to your cart",
            use_container_width=True,
            type="primary"
        ):
            _add_recommendation_to_cart(display_name, product_name)
    
    with col2:
        # Pass/Skip button
        if st.button(
            "⏭️ Pass",
            key=f"pass_rec_{rec_index}",
            help="Skip this recommendation and see the next one",
            use_container_width=True,
            type="secondary"
        ):
            _skip_to_next_recommendation()
    
    # Show progress
    total_recs = len(current_recs)
    st.progress((rec_index + 1) / total_recs, text=f"Recommendation {rec_index + 1} of {total_recs}")


def _add_recommendation_to_cart(display_name: str, product_name: str):
    """Add the recommended item to cart by programmatically selecting it in the dropdown"""
    # Get current cart items from the multiselect widget
    current_cart = st.session_state.get("cart_items", [])
    selected_recs = st.session_state.get("selected_recommendations", [])
    
    if display_name not in current_cart:
        # UIUX Bypass: Programmatically add to the multiselect by updating its state
        # This approach works with Streamlit's widget management
        updated_cart = current_cart.copy()
        updated_cart.append(display_name)
        
        # Store the updated cart in a temporary state that will be used to set the multiselect default
        st.session_state._temp_cart_update = updated_cart
        
        # Track selected recommendations
        selected_recs.append(product_name)
        st.session_state.selected_recommendations = selected_recs
        
        # Move to next recommendation
        st.session_state.current_rec_index += 1
        
        st.success(f"✅ Added {product_name} to cart!")
        st.rerun()
    else:
        st.warning(f"⚠️ {product_name} is already in your cart!")


def _skip_to_next_recommendation():
    """Skip current recommendation and move to the next one"""
    current_recs = st.session_state.get("current_recommendations")
    
    if current_recs is not None and not current_recs.empty:
        st.session_state.current_rec_index += 1
        
        # If we've gone through all recommendations, reset to start
        if st.session_state.current_rec_index >= len(current_recs):
            st.session_state.current_rec_index = 0
            st.info("🔄 Cycled back to first recommendation")
        
        st.rerun()









