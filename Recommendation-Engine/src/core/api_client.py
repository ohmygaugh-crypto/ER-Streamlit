"""
Instacart Connect API client with automatic token management
Based on: https://docs.instacart.com/connect/recommendations_guide/tutorials/get_a_client_access_token/
"""
import streamlit as st
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class InstacartAPIClient:
    """
    Instacart Connect API client with automatic token management
    Token is valid for 24 hours and auto-refreshes as needed
    """
    
    def __init__(self):
        self.base_url = None
        self.client_id = None
        self.client_secret = None
        self.access_token = None
        self.token_expires_at = None
        
    def configure_credentials(self, base_url: str, client_id: str, client_secret: str):
        """Configure API credentials and store in session state"""
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        
        # Store in session state for persistence
        st.session_state.instacart_config = {
            'base_url': base_url,
            'client_id': client_id,
            'client_secret': client_secret
        }
    
    def generate_token(self) -> Dict[str, Any]:
        """
        Generate a new access token using client credentials
        Token is valid for 24 hours as per Instacart documentation
        """
        if not all([self.base_url, self.client_id, self.client_secret]):
            return {'success': False, 'error': 'API credentials not configured'}
        
        token_url = f"{self.base_url}/v2/oauth/token"
        
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": "connect:recommendations"
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(token_url, json=payload, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Store token and expiration time
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 86400)  # Default 24 hours
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            # Store in session state for persistence
            st.session_state.instacart_token = {
                'access_token': self.access_token,
                'expires_at': self.token_expires_at.isoformat(),
                'created_at': datetime.now().isoformat()
            }
            
            return {
                'success': True,
                'access_token': self.access_token,
                'expires_at': self.token_expires_at,
                'expires_in_hours': expires_in / 3600
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f"Token generation failed: {str(e)}"
            }
    
    def is_token_valid(self) -> bool:
        """Check if current token is still valid (with 5-minute buffer)"""
        if not self.access_token or not self.token_expires_at:
            return False
        
        # Add 5-minute buffer to avoid edge cases
        return datetime.now() < (self.token_expires_at - timedelta(minutes=5))
    
    def ensure_valid_token(self) -> bool:
        """Ensure we have a valid token, refresh if necessary"""
        # Try to restore from session state first
        self._restore_from_session_state()
        
        if not self.is_token_valid():
            result = self.generate_token()
            return result['success']
        
        return True
    
    def _restore_from_session_state(self):
        """Restore token and config from session state"""
        # Restore config
        if 'instacart_config' in st.session_state:
            config = st.session_state.instacart_config
            self.base_url = config['base_url']
            self.client_id = config['client_id']
            self.client_secret = config['client_secret']
        
        # Restore token
        if 'instacart_token' in st.session_state:
            token_data = st.session_state.instacart_token
            self.access_token = token_data['access_token']
            self.token_expires_at = datetime.fromisoformat(token_data['expires_at'])
    
    def get_complementary_items(self, product_ids: List[str], limit: int = 10) -> Dict[str, Any]:
        """
        Get complementary items from Instacart API
        Endpoint: /v2/recommendations/complementary_items
        """
        if not self.ensure_valid_token():
            return {'success': False, 'error': 'Failed to obtain valid token'}
        
        url = f"{self.base_url}/v2/recommendations/complementary_items"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        payload = {
            "product_ids": product_ids,
            "limit": limit
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            return {
                'success': True,
                'data': response.json()
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f"API request failed: {str(e)}"
            }
    
    def search_products(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """Search for products in Instacart catalog"""
        if not self.ensure_valid_token():
            return {'success': False, 'error': 'Failed to obtain valid token'}
        
        url = f"{self.base_url}/v2/products/search"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        
        params = {
            "query": query,
            "limit": limit
        }
        
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            return {
                'success': True,
                'data': response.json()
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f"Product search failed: {str(e)}"
            }
    
    def get_token_status(self) -> Dict[str, Any]:
        """Get current token status for UI display"""
        self._restore_from_session_state()
        
        if not self.access_token:
            return {
                'status': 'no_token',
                'message': 'No token available'
            }
        
        if self.is_token_valid():
            time_remaining = self.token_expires_at - datetime.now()
            hours_remaining = time_remaining.total_seconds() / 3600
            
            return {
                'status': 'valid',
                'message': f'Token valid for {hours_remaining:.1f} hours',
                'expires_at': self.token_expires_at,
                'hours_remaining': hours_remaining
            }
        else:
            return {
                'status': 'expired',
                'message': 'Token has expired'
            }


class GroceryAPIManager:
    """
    Unified interface for multiple grocery APIs with fallbacks
    Supports Instacart, Kroger (future), and enhanced mock data
    """
    
    def __init__(self):
        self.providers = {
            'instacart': InstacartAPIClient(),
            'kroger': None,  # TODO: Implement when API access available
            'mock': self._get_mock_provider()
        }
        self.active_provider = 'mock'  # Default fallback
    
    def _get_mock_provider(self):
        """Enhanced mock provider with realistic grocery data"""
        class MockProvider:
            def get_complementary_items(self, product_ids: List[str], limit: int = 10):
                # Enhanced mock recommendations based on common grocery patterns
                mock_recommendations = [
                    {'id': 'butter', 'name': 'Butter', 'category': 'Dairy', 'price': 4.49},
                    {'id': 'jam_strw', 'name': 'Strawberry Jam', 'category': 'Pantry', 'price': 3.29},
                    {'id': 'cheddar', 'name': 'Cheddar Cheese', 'category': 'Deli', 'price': 5.99},
                    {'id': 'yogurt', 'name': 'Greek Yogurt', 'category': 'Dairy', 'price': 1.29},
                    {'id': 'avocado', 'name': 'Avocado', 'category': 'Produce', 'price': 1.19},
                    {'id': 'sauce', 'name': 'Tomato Sauce', 'category': 'Pantry', 'price': 2.49},
                    {'id': 'salsa', 'name': 'Salsa', 'category': 'Snacks', 'price': 2.99}
                ]
                
                return {
                    'success': True,
                    'data': {
                        'items': mock_recommendations[:limit]
                    }
                }
            
            def search_products(self, query: str, limit: int = 20):
                return {'success': True, 'data': {'items': []}}
        
        return MockProvider()
    
    def set_active_provider(self, provider: str):
        """Switch active API provider"""
        if provider in self.providers:
            self.active_provider = provider
            st.session_state.active_grocery_api = provider
    
    def get_recommendations(self, cart_items: List[str], persona: Dict[str, Any], limit: int = 10) -> List[Dict]:
        """Get recommendations from active provider with persona filtering"""
        provider = self.providers[self.active_provider]
        
        if not provider:
            return []
        
        result = provider.get_complementary_items(cart_items, limit)
        
        if not result['success']:
            # Fallback to mock provider
            if self.active_provider != 'mock':
                st.warning(f"⚠️ {self.active_provider} API failed, using mock data")
                return self._get_mock_provider().get_complementary_items(cart_items, limit)['data']['items']
            return []
        
        return result['data'].get('items', [])
    
    def search_products(self, query: str, limit: int = 20) -> List[Dict]:
        """Search products across providers"""
        provider = self.providers[self.active_provider]
        
        if not provider:
            return []
        
        result = provider.search_products(query, limit)
        
        if result['success']:
            return result['data'].get('items', [])
        
        return []


@st.cache_resource
def get_api_manager() -> GroceryAPIManager:
    """Get cached API manager instance"""
    return GroceryAPIManager()
