"""
Sidebar layout with data source controls and network parameters
"""
import streamlit as st
from typing import Dict, Any
from ...utils import (
    parse_persona_file, 
    parse_grocery_list,
    extract_persona_from_json, 
    normalize_persona_fields
)


def render_sidebar() -> Dict[str, Any]:
    """
    Render sidebar with all configuration options
    
    Returns:
        Dictionary with configuration parameters
    """
    st.sidebar.header("🔧 Configuration")
    
    # Data source section
    st.sidebar.subheader("📊 Data Source")
    use_mock = st.sidebar.toggle(
        "Use Mock Grocery Data", 
        value=True,
        help="Toggle between built-in mock data and uploaded CSV"
    )
    
    uploaded_file = None
    if not use_mock:
        uploaded_file = st.sidebar.file_uploader(
            "Upload Orders CSV",
            type=["csv"],
            help="CSV with columns: order_id, customer_id, order_timestamp, product_id, product_name, category, price, quantity"
        )
    
    st.sidebar.divider()
    
    # Customer persona section
    _render_persona_section()
    
    st.sidebar.divider()
    
    # Grocery list section
    _render_grocery_list_section()
    
    st.sidebar.divider()
    
    # API provider selection
    api_client = _render_api_provider_section()
    
    # LLM settings
    llm_enabled = _render_llm_settings_section()
    
    # Token refresh scheduler
    _render_token_refresh_scheduler()
    
    st.sidebar.divider()
    
    # Network analysis parameters
    st.sidebar.subheader("🕸️ Network Filters")
    min_support = st.sidebar.slider(
        "Min Pair Support",
        min_value=0.0,
        max_value=0.05,
        value=0.005,
        step=0.001,
        format="%.3f",
        help="Minimum fraction of orders containing both items in a pair"
    )
    
    min_lift = st.sidebar.slider(
        "Min Lift",
        min_value=1.0,
        max_value=5.0,
        value=1.2,
        step=0.05,
        help="Minimum lift score (co-occurrence strength relative to independence)"
    )
    
    max_edges = st.sidebar.number_input(
        "Max Edges",
        min_value=100,
        max_value=20000,
        value=2500,
        step=100,
        help="Maximum number of edges to display (for performance)"
    )
    
    st.sidebar.divider()
    
    # Recommendation parameters
    st.sidebar.subheader("🎯 Recommendations")
    rec_k = st.sidebar.slider(
        "Number of Recommendations",
        min_value=1,
        max_value=15,
        value=5,
        help="How many recommendations to show"
    )
    
    margin_pct = st.sidebar.slider(
        "Assumed Margin %",
        min_value=0,
        max_value=90,
        value=35,
        help="Profit margin percentage for revenue uplift calculations"
    )
    
    st.sidebar.divider()
    
    # Visualization parameters
    st.sidebar.subheader("📈 Visualization")
    
    # Only show layout option if st_link_analysis is available
    try:
        from st_link_analysis import st_link_analysis
        layout_choice = st.sidebar.selectbox(
            "Graph Layout",
            options=["cose", "grid", "concentric", "breadthfirst", "circle"],
            index=0,
            help="Layout algorithm for network visualization"
        )
    except ImportError:
        layout_choice = "cose"
        st.sidebar.info("📦 Install st-link-analysis for interactive graph visualization")
    
    show_communities = st.sidebar.checkbox(
        "Show Communities",
        value=True,
        help="Color nodes by detected communities"
    )
    
    st.sidebar.divider()
    
    # Information section
    with st.sidebar.expander("ℹ️ About This Demo", expanded=False):
        st.markdown("""
        **Network Analytics for Retail Recommendations**
        
        This demo showcases how network analysis can power intelligent product recommendations for retail checkout flows.
        
        **Key Features:**
        - Market basket analysis with support, confidence, and lift
        - Interactive product co-purchase network
        - Explainable recommendations with "why" reasoning
        - Revenue uplift estimation
        - Community detection in product relationships
        
        **Use Cases:**
        - E-commerce cart add-ons
        - Grocery store checkout suggestions
        - Cross-selling optimization
        - Inventory planning insights
        """)
    
    return {
        "use_mock": use_mock,
        "uploaded_file": uploaded_file,
        "min_support": min_support,
        "min_lift": min_lift,
        "max_edges": max_edges,
        "rec_k": rec_k,
        "margin_pct": margin_pct,
        "layout_choice": layout_choice,
        "show_communities": show_communities,
        "api_client": api_client,
        "llm_enabled": llm_enabled
    }


def _render_grocery_list_section():
    """Render grocery list upload and tracking section"""
    st.sidebar.subheader("📝 Grocery List Tracker")
    
    # File upload for grocery list
    uploaded_list = st.sidebar.file_uploader(
        "Upload Grocery List",
        type=["json", "md", "txt"],
        help="Upload a grocery list in JSON, Markdown, or text format",
        key="grocery_list_upload"
    )
    
    # Parse and store grocery list
    if uploaded_list is not None:
        _parse_and_store_grocery_list(uploaded_list)
    
    # Display current grocery list with strikethrough for items in cart
    _display_grocery_list_with_progress()


def _parse_and_store_grocery_list(uploaded_file):
    """Parse uploaded grocery list and store in session state using centralized utils"""
    try:
        grocery_items = parse_grocery_list(uploaded_file)
        
        if grocery_items:
            # Store in session state
            st.session_state.grocery_list = grocery_items
            st.sidebar.success(f"✅ Loaded {len(grocery_items)} items from grocery list!")
        else:
            st.sidebar.error("❌ Could not parse grocery list")
        
    except Exception as e:
        st.sidebar.error(f"❌ Error parsing grocery list: {str(e)}")


def _display_grocery_list_with_progress():
    """Display grocery list with strikethrough for items in cart and green upsells"""
    grocery_list = st.session_state.get("grocery_list", [])
    
    if not grocery_list:
        st.sidebar.info("📋 Upload a grocery list to track your shopping progress!")
        return
    
    # Get current cart items and selected recommendations
    cart_items = st.session_state.get("cart_items", [])
    selected_recs = st.session_state.get("selected_recommendations", [])
    
    # Convert cart items to product names for matching
    cart_product_names = []
    cart_product_names_with_display = []  # Keep both original and display names
    
    for item_display_name in cart_items:
        # Extract product name from display name (e.g., "Apples (Produce) - $0.79" -> "Apples")
        product_name = item_display_name.split(" (")[0].strip()
        cart_product_names.append(product_name.lower())
        cart_product_names_with_display.append({
            'name': product_name,
            'display': item_display_name,
            'lower': product_name.lower()
        })
    
    # Create sets for faster lookup
    grocery_items_lower = {item.strip().lower() for item in grocery_list}
    
    # Display grocery list with progress
    st.sidebar.markdown("**📋 Your Shopping Progress:**")
    
    completed_items = 0
    total_items = len(grocery_list)
    upsell_items = []
    
    # First, show original grocery list items
    for item in grocery_list:
        item_name = item.strip()
        item_lower = item_name.lower()
        
        # Check if this grocery item matches any cart item (fuzzy matching)
        is_in_cart = any(
            item_lower in cart_info['lower'] or cart_info['lower'] in item_lower
            for cart_info in cart_product_names_with_display
        )
        
        if is_in_cart:
            # Strikethrough for items in cart
            st.sidebar.markdown(f"~~{item_name}~~ ✅")
            completed_items += 1
        else:
            # Regular text for items not in cart
            st.sidebar.markdown(f"• {item_name}")
    
    # Now show upsell items (items in cart that weren't on the original grocery list)
    for cart_info in cart_product_names_with_display:
        cart_name = cart_info['name']
        cart_lower = cart_info['lower']
        
        # Check if this cart item was NOT on the original grocery list
        is_original_item = any(
            cart_lower in grocery_lower or grocery_lower in cart_lower
            for grocery_lower in grocery_items_lower
        )
        
        # Check if this was added via recommendation (from selected_recommendations)
        is_recommendation = cart_name in selected_recs
        
        if not is_original_item:
            upsell_items.append({
                'name': cart_name,
                'is_recommendation': is_recommendation
            })
    
    # Display upsell items
    if upsell_items:
        st.sidebar.markdown("**🎯 Smart Upsells:**")
        for upsell in upsell_items:
            if upsell['is_recommendation']:
                # Green text with + for AI-recommended upsells
                st.sidebar.markdown(f":green[+ {upsell['name']} (AI Recommended) 🤖]")
            else:
                # Different color for manual additions
                st.sidebar.markdown(f":blue[+ {upsell['name']} (Manual Add)]")
    
    # Enhanced progress display
    _display_enhanced_progress(completed_items, total_items, len(upsell_items), 
                              sum(1 for u in upsell_items if u['is_recommendation']))


def _display_enhanced_progress(completed_items: int, total_items: int, 
                              total_upsells: int, ai_upsells: int):
    """Display enhanced progress with original list completion and upsell metrics"""
    
    # Original grocery list progress
    if total_items > 0:
        progress_pct = (completed_items / total_items) * 100
        st.sidebar.progress(completed_items / total_items)
        st.sidebar.caption(f"Original List: {completed_items}/{total_items} items ({progress_pct:.1f}%)")
        
        # Completion status for original list
        if completed_items == total_items:
            st.sidebar.success("🎉 Grocery list completed!")
        elif completed_items > 0:
            st.sidebar.info(f"🛒 {total_items - completed_items} items remaining")
    
    # Upsell metrics
    if total_upsells > 0:
        st.sidebar.markdown("---")
        
        # Upsell breakdown
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric("🎯 Total Upsells", total_upsells)
        with col2:
            st.metric("🤖 AI Suggested", ai_upsells)
        
        # Calculate upsell value (if we have pricing)
        if ai_upsells > 0:
            ai_percentage = (ai_upsells / total_upsells) * 100
            st.sidebar.caption(f"AI Success Rate: {ai_percentage:.1f}% of upsells")
        
        # Show total impact
        total_cart_items = completed_items + total_upsells
        if total_items > 0:
            basket_growth = (total_upsells / total_items) * 100
            st.sidebar.info(f"📈 Basket Growth: +{basket_growth:.1f}% ({total_upsells} extra items)")
    
    # Overall shopping summary
    if total_items > 0 and total_upsells > 0:
        st.sidebar.markdown("---")
        st.sidebar.markdown("**📊 Shopping Summary:**")
        st.sidebar.markdown(f"• ✅ Original items: {completed_items}")
        st.sidebar.markdown(f"• 🎯 Upsells added: {total_upsells}")
        st.sidebar.markdown(f"• 🤖 AI-driven upsells: {ai_upsells}")
        
        total_cart = completed_items + total_upsells
        st.sidebar.markdown(f"• 🛒 **Total cart: {total_cart} items**")


def _render_persona_section():
    """Render customer persona upload and configuration section"""
    st.sidebar.subheader("👤 Customer Persona")
    
    # Persona upload
    uploaded_persona = st.sidebar.file_uploader(
        "Upload Customer Profile",
        type=["json", "csv"],
        help="JSON from health/shopping apps or CSV with customer profile data",
        key="persona_upload"
    )
    
    # Show format preference hint
    st.sidebar.caption("💡 **Recommended**: JSON format from health/shopping apps (MyFitnessPal, Instacart, etc.)")
    
    # Parse and store persona data
    if uploaded_persona is not None:
        _parse_and_store_persona(uploaded_persona)
    
    # Display current persona summary
    _display_persona_summary()
    
    # Manual persona configuration (fallback/override)
    with st.sidebar.expander("⚙️ Manual Persona Override", expanded=False):
        _render_manual_persona_config()


def _parse_and_store_persona(uploaded_file):
    """Parse uploaded persona JSON/CSV and store in session state using centralized utils"""
    try:
        persona = parse_persona_file(uploaded_file)
        
        if persona:
            # Store in session state
            st.session_state.customer_persona = persona
            customer_name = persona.get('name', persona.get('customer_id', 'Unknown'))
            st.sidebar.success(f"✅ Loaded profile for: {customer_name}")
            
            # Show data source if available
            data_source = persona.get('data_source', 'Unknown')
            if data_source != 'Unknown':
                st.sidebar.info(f"📱 Data from: {data_source}")
        else:
            st.sidebar.error("❌ Could not parse persona data")
        
    except Exception as e:
        st.sidebar.error(f"❌ Error parsing profile data: {str(e)}")
        st.sidebar.info("💡 Try JSON format from health/shopping apps, or CSV with required columns")


# ============================================================================
# REFACTORED: Persona parsing functions moved to utils/
# ============================================================================
# 
# The following functions have been moved to centralized utilities:
# 
# OLD LOCATION -> NEW LOCATION:
# - _extract_persona_from_json -> utils.persona_parser.extract_persona_from_json
# - _normalize_persona_fields -> utils.persona_parser.normalize_persona_fields
# - _parse_and_store_grocery_list -> uses utils.persona_parser.parse_grocery_list
# - _parse_and_store_persona -> uses utils.persona_parser.parse_persona_file
#
# This provides better code organization, reusability, and testing capabilities.
# ============================================================================

# All deprecated functions removed - now using centralized utils


def _display_persona_summary():
    """Display current persona summary"""
    persona = st.session_state.get("customer_persona")
    
    if not persona:
        st.sidebar.info("👤 Upload persona data or configure manually to enable personalized recommendations")
        return
    
    st.sidebar.markdown("**👤 Active Customer Profile:**")
    
    # Customer ID and basic info
    customer_id = persona.get('customer_id', 'Unknown')
    st.sidebar.markdown(f"**ID:** {customer_id}")
    
    # Diet and allergies
    allergies = persona.get('allergies', [])
    diet_prefs = persona.get('diet_preferences', [])
    
    if allergies:
        st.sidebar.markdown(f"🚫 **Allergies:** {', '.join(allergies)}")
    if diet_prefs:
        st.sidebar.markdown(f"🥗 **Diet:** {', '.join(diet_prefs)}")
    
    # Budget info
    budget_min = persona.get('budget_min')
    budget_max = persona.get('budget_max')
    if budget_min and budget_max:
        st.sidebar.markdown(f"💰 **Budget:** ${budget_min}-${budget_max}")
    
    # Lifestyle indicators
    income_level = persona.get('income_level')
    organic_pref = persona.get('organic_preference')
    
    if income_level:
        st.sidebar.markdown(f"📊 **Income:** {income_level}")
    if organic_pref:
        organic_pct = float(organic_pref) * 100
        st.sidebar.markdown(f"🌱 **Organic Preference:** {organic_pct:.0f}%")


def _render_manual_persona_config():
    """Render manual persona configuration as fallback/override"""
    st.markdown("**Quick Persona Setup:**")
    
    # Diet preferences
    diet_options = st.multiselect(
        "Diet Preferences",
        options=["Vegetarian", "Vegan", "Gluten-Free", "Keto", "Paleo", "Low-Sodium", "Diabetic-Friendly"],
        key="manual_diet_prefs"
    )
    
    # Allergies
    allergy_options = st.multiselect(
        "Allergies",
        options=["Nuts", "Dairy", "Gluten", "Eggs", "Soy", "Shellfish", "Fish"],
        key="manual_allergies"
    )
    
    # Budget range
    budget_range = st.slider(
        "Budget Range ($)",
        min_value=20,
        max_value=300,
        value=(50, 150),
        key="manual_budget"
    )
    
    # Income level
    income_level = st.selectbox(
        "Income Level",
        options=["low", "middle", "high"],
        key="manual_income"
    )
    
    # Preferences
    organic_pref = st.slider(
        "Organic Preference",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        help="0 = No preference, 1 = Strongly prefer organic",
        key="manual_organic"
    )
    
    price_sensitivity = st.slider(
        "Price Sensitivity", 
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        help="0 = Price insensitive, 1 = Very price sensitive",
        key="manual_price_sens"
    )
    
    # Apply manual configuration
    if st.button("Apply Manual Persona", key="apply_manual_persona"):
        manual_persona = {
            'customer_id': 'manual_config',
            'allergies': allergy_options,
            'diet_preferences': diet_options,
            'budget_min': budget_range[0],
            'budget_max': budget_range[1],
            'income_level': income_level,
            'organic_preference': organic_pref,
            'price_sensitivity': price_sensitivity
        }
        
        st.session_state.customer_persona = manual_persona
        st.success("✅ Manual persona applied!")
        st.rerun()


def _render_api_provider_section():
    """Render API provider selection and configuration"""
    st.sidebar.subheader("🔌 Grocery Data Source")
    
    # Provider selection
    provider_options = {
        'mock': '🎭 Enhanced Mock Data',
        'instacart': '🥕 Instacart Connect API',
        'kroger': '🛒 Kroger API (Coming Soon)'
    }
    
    selected_provider = st.sidebar.selectbox(
        "Data Provider",
        options=list(provider_options.keys()),
        format_func=lambda x: provider_options[x],
        index=0,
        key="api_provider_select"
    )
    
    # Store selection in session state
    st.session_state.active_grocery_api = selected_provider
    
    # Provider-specific configuration
    if selected_provider == 'instacart':
        return _render_instacart_token_manager()
    
    elif selected_provider == 'kroger':
        st.sidebar.info("🚧 Kroger API integration coming soon!")
        st.sidebar.markdown("**Alternative**: Use mock data or Instacart for now")
        return None
    
    else:  # mock
        st.sidebar.success("✅ Using enhanced mock grocery data")
        st.sidebar.info("💡 Switch to real APIs when credentials are available")
        return None


def _render_instacart_token_manager():
    """Render Instacart API token management interface"""
    from ...core.api_client import InstacartAPIClient
    
    st.sidebar.markdown("#### 🥕 Instacart API Settings")
    
    client = InstacartAPIClient()
    
    # Configuration section
    with st.sidebar.expander("🔧 API Configuration", expanded=False):
        base_url = st.text_input(
            "Development Server URL",
            placeholder="https://your-instacart-dev-domain.com",
            help="Your assigned Instacart development server URL",
            key="instacart_base_url"
        )
        
        client_id = st.text_input(
            "Client ID",
            type="password",
            help="Your Instacart Connect client ID",
            key="instacart_client_id"
        )
        
        client_secret = st.text_input(
            "Client Secret", 
            type="password",
            help="Your Instacart Connect client secret",
            key="instacart_client_secret"
        )
        
        if st.button("💾 Save Configuration", key="save_instacart_config"):
            if all([base_url, client_id, client_secret]):
                client.configure_credentials(base_url, client_id, client_secret)
                st.success("✅ Configuration saved!")
                st.rerun()
            else:
                st.error("❌ Please fill in all fields")
    
    # Token status and management
    token_status = client.get_token_status()
    
    if token_status['status'] == 'valid':
        st.sidebar.success(f"✅ {token_status['message']}")
        
        # Show refresh button if token expires soon (< 2 hours)
        if token_status['hours_remaining'] < 2:
            st.sidebar.warning("⚠️ Token expires soon!")
            if st.sidebar.button("🔄 Refresh Token", key="refresh_token_soon"):
                result = client.generate_token()
                if result['success']:
                    st.sidebar.success("✅ Token refreshed!")
                    st.rerun()
                else:
                    st.sidebar.error(f"❌ {result['error']}")
    
    elif token_status['status'] == 'expired':
        st.sidebar.warning("⚠️ Token has expired")
        if st.sidebar.button("🔄 Generate New Token", key="generate_new_token"):
            result = client.generate_token()
            if result['success']:
                st.sidebar.success("✅ New token generated!")
                st.rerun()
            else:
                st.sidebar.error(f"❌ {result['error']}")
    
    else:  # no_token
        st.sidebar.info("ℹ️ Configure API credentials above")
        if st.sidebar.button("🚀 Generate Token", key="generate_first_token"):
            result = client.generate_token()
            if result['success']:
                st.sidebar.success("✅ Token generated!")
                st.rerun()
            else:
                st.sidebar.error(f"❌ {result['error']}")
    
    return client


def _render_llm_settings_section():
    """Render LLM configuration in sidebar"""
    st.sidebar.subheader("🤖 AI Enhancement Settings")
    
    enable_llm = st.sidebar.toggle(
        "Enable AI Features",
        value=st.session_state.get('enable_llm', False),
        help="Use LLM for smart grocery lists, meal planning, and safety analysis",
        key="enable_llm_toggle"
    )
    
    st.session_state.enable_llm = enable_llm
    
    if enable_llm:
        # LLM Provider selection
        provider = st.sidebar.selectbox(
            "AI Provider",
            options=["openai", "anthropic", "local"],
            format_func=lambda x: {
                "openai": "🔥 OpenAI GPT",
                "anthropic": "🧠 Anthropic Claude", 
                "local": "🏠 Local Model"
            }[x],
            key="llm_provider_select"
        )
        
        st.session_state.llm_provider = provider
        
        # Feature toggles
        st.sidebar.markdown("**🎯 AI Features:**")
        
        features = {
            'smart_grocery_lists': st.sidebar.checkbox("🛒 Smart Grocery Lists", value=True, key="feat_grocery"),
            'meal_planning': st.sidebar.checkbox("🍽️ AI Meal Planning", value=True, key="feat_meals"),
            'persona_enrichment': st.sidebar.checkbox("🧠 Persona Intelligence", value=True, key="feat_persona"),
            'allergen_analysis': st.sidebar.checkbox("🛡️ Allergy Safety", value=True, key="feat_allergen")
        }
        
        st.session_state.llm_features = features
        
        # API key configuration
        if provider == "openai":
            api_key = st.sidebar.text_input(
                "OpenAI API Key",
                type="password",
                help="Your OpenAI API key for GPT models",
                key="openai_api_key_input"
            )
            if api_key:
                st.session_state.openai_api_key = api_key
        
        elif provider == "anthropic":
            api_key = st.sidebar.text_input(
                "Anthropic API Key",
                type="password", 
                help="Your Anthropic API key for Claude models",
                key="anthropic_api_key_input"
            )
            if api_key:
                st.session_state.anthropic_api_key = api_key
        
        return True
    
    return False


def _render_token_refresh_scheduler():
    """Render automatic token refresh scheduler"""
    active_provider = st.session_state.get('active_grocery_api', 'mock')
    
    if active_provider == 'instacart':
        st.sidebar.markdown("#### ⏰ Auto-Refresh Settings")
        
        auto_refresh = st.sidebar.toggle(
            "Auto-refresh tokens",
            value=st.session_state.get('auto_refresh_tokens', False),
            help="Automatically refresh API tokens before they expire",
            key="auto_refresh_toggle"
        )
        
        if auto_refresh:
            refresh_hours = st.sidebar.slider(
                "Refresh when < X hours remain",
                min_value=1,
                max_value=12, 
                value=4,
                help="Automatically refresh token when this many hours remain",
                key="auto_refresh_threshold_slider"
            )
            
            st.session_state.auto_refresh_tokens = True
            st.session_state.auto_refresh_threshold = refresh_hours
            
            # Check if auto-refresh needed
            from ...core.api_client import InstacartAPIClient
            client = InstacartAPIClient()
            token_status = client.get_token_status()
            
            if (token_status['status'] == 'valid' and 
                token_status['hours_remaining'] < refresh_hours):
                
                with st.sidebar.spinner("🔄 Auto-refreshing token..."):
                    result = client.generate_token()
                    if result['success']:
                        st.sidebar.success("✅ Auto-refreshed!")
                        st.rerun()
                    else:
                        st.sidebar.error("❌ Auto-refresh failed")
        
        else:
            st.session_state.auto_refresh_tokens = False
