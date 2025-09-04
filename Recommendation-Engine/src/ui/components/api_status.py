"""
API status and token management UI components
"""
import streamlit as st
from datetime import datetime
from ...core.api_client import InstacartAPIClient


def render_api_status_widget():
    """
    Render API status widget with auto-refresh capability
    Shows at top of main view when using real APIs
    """
    # Only show if using real APIs
    active_provider = st.session_state.get('active_grocery_api', 'mock')
    
    if active_provider == 'instacart':
        client = InstacartAPIClient()
        token_status = client.get_token_status()
        
        # Create status indicator container
        status_container = st.container()
        
        with status_container:
            if token_status['status'] == 'valid':
                hours_left = token_status['hours_remaining']
                
                # Color-coded status based on time remaining
                if hours_left > 12:
                    st.success(f"🟢 Instacart API: Active ({hours_left:.1f}h remaining)")
                elif hours_left > 2:
                    st.warning(f"🟡 Instacart API: Expires soon ({hours_left:.1f}h remaining)")
                else:
                    st.error(f"🔴 Instacart API: Expires very soon ({hours_left:.1f}h remaining)")
                    
                    # Urgent auto-refresh button
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        if st.button("🔄 Refresh Now", key="urgent_refresh", type="primary"):
                            result = client.generate_token()
                            if result['success']:
                                st.success("✅ Token refreshed!")
                                st.rerun()
                            else:
                                st.error(f"❌ Refresh failed: {result['error']}")
            
            elif token_status['status'] == 'expired':
                st.error("🔴 Instacart API: Token expired - recommendations may be limited")
                
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button("🚀 Generate Token", key="generate_new_main", type="primary"):
                        result = client.generate_token()
                        if result['success']:
                            st.success("✅ New token generated!")
                            st.rerun()
                        else:
                            st.error(f"❌ {result['error']}")
            
            else:
                st.info("ℹ️ Instacart API: Configure credentials in sidebar to enable real grocery data")
    
    elif active_provider == 'kroger':
        st.info("🛒 Kroger API: Integration coming soon!")
    
    # If using mock data, don't show any status widget


def render_token_health_monitor():
    """
    Render detailed token health monitoring (for sidebar or admin view)
    """
    active_provider = st.session_state.get('active_grocery_api', 'mock')
    
    if active_provider != 'instacart':
        return
    
    st.sidebar.markdown("#### 📊 Token Health Monitor")
    
    client = InstacartAPIClient()
    token_status = client.get_token_status()
    
    if token_status['status'] == 'valid':
        hours_left = token_status['hours_remaining']
        expires_at = token_status['expires_at']
        
        # Health metrics
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            st.metric("Hours Left", f"{hours_left:.1f}")
        
        with col2:
            # Health score based on time remaining
            if hours_left > 12:
                health_score = "Excellent"
                health_color = "🟢"
            elif hours_left > 6:
                health_score = "Good"
                health_color = "🟡"
            elif hours_left > 2:
                health_score = "Warning"
                health_color = "🟠"
            else:
                health_score = "Critical"
                health_color = "🔴"
            
            st.metric("Health", f"{health_color} {health_score}")
        
        # Expiration details
        st.sidebar.caption(f"Expires: {expires_at.strftime('%I:%M %p')}")
        
        # Auto-refresh settings
        auto_refresh = st.session_state.get('auto_refresh_tokens', False)
        threshold = st.session_state.get('auto_refresh_threshold', 4)
        
        if auto_refresh:
            st.sidebar.success(f"✅ Auto-refresh enabled (< {threshold}h)")
        else:
            st.sidebar.info("ℹ️ Manual refresh required")
    
    elif token_status['status'] == 'expired':
        st.sidebar.error("🔴 Token expired")
        
        # Show last expiration time if available
        if 'instacart_token' in st.session_state:
            created_at = st.session_state.instacart_token.get('created_at')
            if created_at:
                created_time = datetime.fromisoformat(created_at)
                st.sidebar.caption(f"Last generated: {created_time.strftime('%I:%M %p')}")
    
    else:
        st.sidebar.info("ℹ️ No token available")


def render_api_connection_test():
    """
    Render API connection testing interface
    """
    active_provider = st.session_state.get('active_grocery_api', 'mock')
    
    if active_provider == 'instacart':
        st.sidebar.markdown("#### 🧪 API Connection Test")
        
        test_query = st.sidebar.text_input(
            "Test Search Query",
            value="milk",
            help="Enter a product name to test the API connection",
            key="api_test_query"
        )
        
        if st.sidebar.button("🔍 Test Search", key="test_search_btn"):
            client = InstacartAPIClient()
            
            with st.sidebar.spinner("Testing API connection..."):
                result = client.search_products(test_query, limit=3)
            
            if result['success']:
                st.sidebar.success("✅ API connection successful!")
                
                # Show sample results if available
                items = result['data'].get('items', [])
                if items:
                    st.sidebar.markdown("**Sample Results:**")
                    for item in items[:3]:
                        name = item.get('name', 'Unknown')
                        price = item.get('price', 0)
                        st.sidebar.caption(f"• {name} - ${price:.2f}")
                else:
                    st.sidebar.info("No results returned (API working)")
            else:
                st.sidebar.error(f"❌ API test failed: {result['error']}")


def check_auto_refresh_needed():
    """
    Check if auto-refresh is needed and perform it silently
    Call this function periodically in the app
    """
    auto_refresh = st.session_state.get('auto_refresh_tokens', False)
    active_provider = st.session_state.get('active_grocery_api', 'mock')
    
    if not auto_refresh or active_provider != 'instacart':
        return False
    
    client = InstacartAPIClient()
    token_status = client.get_token_status()
    threshold = st.session_state.get('auto_refresh_threshold', 4)
    
    if (token_status['status'] == 'valid' and 
        token_status['hours_remaining'] < threshold):
        
        # Perform silent refresh
        result = client.generate_token()
        
        if result['success']:
            # Store notification for user
            st.session_state.auto_refresh_notification = f"✅ API token auto-refreshed ({datetime.now().strftime('%I:%M %p')})"
            return True
        else:
            st.session_state.auto_refresh_notification = f"❌ Auto-refresh failed: {result['error']}"
            return False
    
    return False
