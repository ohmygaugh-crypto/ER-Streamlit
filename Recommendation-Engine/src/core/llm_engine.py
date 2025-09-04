"""
LLM integration for enhanced recommendations and explanations
Features: Smart grocery lists, meal planning, persona enrichment, allergen analysis
"""
import streamlit as st
import json
from typing import Dict, List, Any, Optional


class LLMRecommendationEnhancer:
    """
    LLM-powered enhancements for the recommendation engine
    Implements features 2, 4, 5, and 7:
    - Smart grocery list generation from persona
    - AI meal planning based on cart
    - Intelligent persona enrichment 
    - Advanced allergen safety analysis
    """
    
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self.client = None
        self.setup_client()
    
    def setup_client(self):
        """Setup LLM client based on provider"""
        if self.provider == "openai":
            try:
                import openai
                api_key = st.secrets.get("OPENAI_API_KEY") or st.session_state.get("openai_api_key")
                if api_key:
                    self.client = openai.OpenAI(api_key=api_key)
                else:
                    st.warning("⚠️ OpenAI API key required for AI features")
            except ImportError:
                st.warning("⚠️ OpenAI not installed. Install with: pip install openai")
        
        elif self.provider == "anthropic":
            try:
                import anthropic
                api_key = st.secrets.get("ANTHROPIC_API_KEY") or st.session_state.get("anthropic_api_key")
                if api_key:
                    self.client = anthropic.Anthropic(api_key=api_key)
                else:
                    st.warning("⚠️ Anthropic API key required for AI features")
            except ImportError:
                st.warning("⚠️ Anthropic not installed. Install with: pip install anthropic")
    
    @st.cache_data(ttl=3600, show_spinner=False)
    def generate_grocery_list_from_persona(_self, persona: Dict[str, Any], 
                                         household_size: int = 2, 
                                         meal_count: int = 7) -> List[str]:
        """
        Feature 2: Smart Grocery List Generation from Persona
        Generate complete grocery lists based on customer profile
        """
        if not _self.client:
            return []
            
        prompt = f"""
        Generate a realistic weekly grocery list for:
        
        Customer Profile:
        - Diet: {', '.join(persona.get('diet_preferences', []))}
        - Allergies: {', '.join(persona.get('allergies', []))}
        - Budget: ${persona.get('budget_min', 50)}-${persona.get('budget_max', 150)}
        - Income Level: {persona.get('income_level', 'middle')}
        - Organic Preference: {int(persona.get('organic_preference', 0.5) * 100)}%
        - Household Size: {household_size} people
        - Meals to Plan: {meal_count} days
        
        Requirements:
        1. Include variety across all food groups (produce, dairy, protein, grains)
        2. Respect ALL dietary restrictions and allergies STRICTLY
        3. Stay within budget constraints
        4. Include realistic quantities for household size
        5. Consider income level for product quality choices
        6. Include both staples and variety items
        
        Return ONLY a JSON array of grocery items (max 25 items):
        ["Whole Milk", "Organic Apples", "Gluten-Free Bread", "Greek Yogurt", ...]
        """
        
        try:
            if _self.provider == "openai":
                response = _self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                    temperature=0.7
                )
                content = response.choices[0].message.content.strip()
            else:
                return []  # Fallback for other providers
            
            # Parse JSON response
            if content.startswith('[') and content.endswith(']'):
                grocery_list = json.loads(content)
                return grocery_list[:25]  # Limit to 25 items
            else:
                # Fallback parsing for non-JSON responses
                lines = content.split('\n')
                items = []
                for line in lines:
                    line = line.strip().strip('"').strip("'").strip('-').strip('•').strip()
                    if line and not line.startswith('{') and not line.startswith('['):
                        # Clean up common prefixes
                        if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                            line = line.split('.', 1)[1].strip()
                        items.append(line)
                return items[:25]  # Limit to 25 items
                
        except Exception as e:
            st.error(f"❌ LLM grocery list generation failed: {e}")
            return []
    
    @st.cache_data(ttl=1800, show_spinner=False)  
    def suggest_meal_plans(_self, cart_items: List[str], persona: Dict[str, Any]) -> Dict[str, Any]:
        """
        Feature 4: Predictive Meal Planning
        Suggest complete meal plans based on current cart
        """
        if not _self.client:
            return {"possible_meals": [], "suggested_meals": []}
            
        prompt = f"""
        Analyze this grocery cart and suggest meal plans:
        
        Cart Items: {', '.join(cart_items)}
        Customer Diet: {', '.join(persona.get('diet_preferences', []))}
        Allergies: {', '.join(persona.get('allergies', []))}
        Budget Level: {persona.get('income_level', 'middle')} income
        
        Provide:
        1. 3 complete meals possible with current cart items
        2. Missing ingredients needed to complete each meal
        3. 2 additional meal suggestions with complete shopping lists
        
        Return as valid JSON:
        {{
          "possible_meals": [
            {{"name": "Meal Name", "ingredients_available": ["item1", "item2"], "missing": ["item3"]}}
          ],
          "suggested_meals": [
            {{"name": "New Meal", "full_shopping_list": ["item1", "item2", "item3"]}}
          ]
        }}
        """
        
        try:
            if _self.provider == "openai":
                response = _self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=800,
                    temperature=0.6
                )
                content = response.choices[0].message.content.strip()
                return json.loads(content)
            else:
                return {"possible_meals": [], "suggested_meals": []}
            
        except Exception as e:
            st.error(f"❌ Meal planning failed: {e}")
            return {"possible_meals": [], "suggested_meals": []}
    
    @st.cache_data(ttl=3600, show_spinner=False)
    def enrich_persona_from_patterns(_self, purchase_history: List[str], 
                                   current_persona: Dict[str, Any]) -> Dict[str, Any]:
        """
        Feature 5: Intelligent Persona Enrichment
        Infer additional customer attributes from purchase patterns
        """
        if not _self.client:
            return {}
            
        prompt = f"""
        Analyze purchase patterns to infer customer characteristics:
        
        Recent Purchases: {', '.join(purchase_history[-20:])}
        Current Profile: {current_persona}
        
        Based on purchase patterns, infer customer characteristics.
        Return valid JSON with confidence scores (0-1):
        {{
          "cooking_skill": {{"level": "beginner|intermediate|advanced", "confidence": 0.8}},
          "time_availability": {{"level": "low|medium|high", "confidence": 0.7}},
          "health_consciousness": {{"score": 0.6, "confidence": 0.9}},
          "brand_loyalty": {{"score": 0.4, "confidence": 0.5}},
          "meal_prep_tendency": {{"score": 0.7, "confidence": 0.6}},
          "seasonal_preferences": ["spring_fresh", "comfort_foods"],
          "likely_household_size": 2
        }}
        """
        
        try:
            if _self.provider == "openai":
                response = _self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=400,
                    temperature=0.5
                )
                content = response.choices[0].message.content.strip()
                return json.loads(content)
            else:
                return {}
            
        except Exception as e:
            st.error(f"❌ Persona enrichment failed: {e}")
            return {}
    
    @st.cache_data(ttl=7200, show_spinner=False)
    def intelligent_allergen_analysis(_self, product_name: str, ingredients: str, 
                                    allergens: List[str]) -> Dict[str, Any]:
        """
        Feature 7: Smart Allergy & Substitution Intelligence
        Deep allergen analysis beyond keyword matching
        """
        if not _self.client:
            return {
                "is_safe": False,  # Conservative default
                "risk_level": "unknown",
                "allergen_risks": [],
                "safe_alternatives": [],
                "confidence": 0.0
            }
            
        prompt = f"""
        Perform comprehensive allergen analysis for food safety:
        
        Product: {product_name}
        Ingredients: {ingredients if ingredients else "ingredients not available"}
        Customer Allergies: {', '.join(allergens)}
        
        Analyze for:
        1. Direct allergen presence in product name/ingredients
        2. Cross-contamination risks during manufacturing
        3. Hidden allergen sources (natural flavors, processing aids, etc.)
        4. Safe alternative products if risks exist
        
        Return valid JSON (be conservative - err on side of caution):
        {{
          "is_safe": true/false,
          "risk_level": "none|low|medium|high",
          "allergen_risks": ["specific allergens detected"],
          "risk_explanations": ["explanation for each risk"],
          "safe_alternatives": ["alternative product suggestions"],
          "confidence": 0.95
        }}
        """
        
        try:
            if _self.provider == "openai":
                response = _self.client.chat.completions.create(
                    model="gpt-4",  # Use GPT-4 for critical safety analysis
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=600,
                    temperature=0.2  # Low temperature for consistent safety analysis
                )
                content = response.choices[0].message.content.strip()
                return json.loads(content)
            else:
                return {
                    "is_safe": False,
                    "risk_level": "unknown",
                    "allergen_risks": [],
                    "safe_alternatives": [],
                    "confidence": 0.0
                }
            
        except Exception as e:
            st.error(f"❌ Allergen analysis failed: {e}")
            return {
                "is_safe": False,  # Conservative default for safety
                "risk_level": "unknown",
                "allergen_risks": [],
                "safe_alternatives": [],
                "confidence": 0.0
            }


@st.cache_resource
def get_llm_enhancer() -> LLMRecommendationEnhancer:
    """Get cached LLM enhancer instance"""
    provider = st.session_state.get('llm_provider', 'openai')
    return LLMRecommendationEnhancer(provider)
