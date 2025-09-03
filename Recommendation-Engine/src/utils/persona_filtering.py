"""
Persona-based product filtering and scoring utilities
"""
import pandas as pd
from typing import Dict, List, Any, Optional
from .dietary_restrictions import check_diet_exclusions, calculate_diet_compatibility, contains_allergen


def apply_persona_filtering(recs_df: pd.DataFrame, meta: Dict[str, Dict], 
                          customer_persona: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    Apply persona-based filtering to recommendations
    
    Args:
        recs_df: DataFrame with recommendation data
        meta: Product metadata dictionary
        customer_persona: Customer persona data from session state
    
    Returns:
        pd.DataFrame: Filtered and scored recommendations
    """
    if customer_persona is None or recs_df.empty:
        return recs_df
    
    # Extract persona attributes with defaults
    allergies = customer_persona.get('allergies', [])
    diet_preferences = customer_persona.get('diet_preferences', [])
    budget_min = customer_persona.get('budget_min', 0)
    budget_max = customer_persona.get('budget_max', float('inf'))
    income_level = customer_persona.get('income_level', 'middle')
    organic_preference = customer_persona.get('organic_preference', 0.5)
    price_sensitivity = customer_persona.get('price_sensitivity', 0.5)
    
    filtered_recs = []
    
    for _, row in recs_df.iterrows():
        product_id = row['product_id']
        product_name = row['product_name']
        
        # Get product metadata
        product_meta = meta.get(product_id, {})
        category = product_meta.get('category', 'Unknown')
        price = product_meta.get('price', 0)
        
        should_exclude = False
        persona_score = 1.0
        
        # 1. ALLERGY FILTERING (HARD EXCLUSIONS)
        for allergen in allergies:
            if contains_allergen(product_name, category, allergen):
                should_exclude = True
                break
        
        if should_exclude:
            continue  # Skip this product entirely
        
        # 2. DIET PREFERENCE FILTERING (HARD EXCLUSIONS)
        diet_exclusion = check_diet_exclusions(product_name, category, diet_preferences)
        if diet_exclusion:
            should_exclude = True
            continue  # Skip this product entirely
        
        # Apply diet preference scoring for compatible products
        diet_score = calculate_diet_compatibility(product_name, category, diet_preferences)
        persona_score *= diet_score
        
        # 3. BUDGET FILTERING
        if budget_min and budget_max and price > 0:
            if price < budget_min * 0.5 or price > budget_max * 2:  # Allow some flexibility
                persona_score *= 0.3  # Heavily penalize but don't exclude
            elif budget_min <= price <= budget_max:
                persona_score *= 1.2  # Boost items in budget
        
        # 4. INCOME-BASED PREFERENCES
        if income_level:
            income_score = calculate_income_preference_score(
                product_name, category, price, income_level, organic_preference
            )
            persona_score *= income_score
        
        # 5. PRICE SENSITIVITY
        if price > 0 and price_sensitivity:
            price_score = calculate_price_sensitivity_score(price, price_sensitivity)
            persona_score *= price_score
        
        # Calculate combined score
        original_score = row.get('score', 1.0)
        combined_score = original_score * persona_score
        
        # Add persona reason
        persona_reason = generate_persona_reason(row, customer_persona, product_meta)
        
        # Add to filtered results
        filtered_rec = row.copy()
        filtered_rec['persona_score'] = persona_score
        filtered_rec['combined_score'] = combined_score
        filtered_rec['persona_reason'] = persona_reason
        
        filtered_recs.append(filtered_rec)
    
    if not filtered_recs:
        return pd.DataFrame()
    
    # Convert back to DataFrame and sort by combined score
    filtered_df = pd.DataFrame(filtered_recs)
    filtered_df = filtered_df.sort_values('combined_score', ascending=False)
    
    return filtered_df


def calculate_income_preference_score(product_name: str, category: str, price: float, 
                                    income_level: str, organic_preference: float) -> float:
    """
    Calculate score based on income level and associated preferences
    
    Args:
        product_name: Name of the product
        category: Product category
        price: Product price
        income_level: 'high', 'middle', or 'low'
        organic_preference: Float between 0-1 indicating organic preference
    
    Returns:
        float: Income-based preference score multiplier
    """
    text = f"{product_name} {category}".lower()
    score = 1.0
    
    if income_level == 'high':
        # High income: prefer premium, organic, brand names
        if any(premium in text for premium in ['organic', 'premium', 'artisan', 'gourmet']):
            score *= 1.3
        elif 'generic' in text or 'store brand' in text:
            score *= 0.8
        
        # Organic preference for high income
        if 'organic' in text:
            score *= (1 + organic_preference * 0.5)
    
    elif income_level == 'low':
        # Low income: prefer value, generic, bulk
        if any(value in text for value in ['value', 'generic', 'store brand', 'bulk']):
            score *= 1.3
        elif any(premium in text for premium in ['organic', 'premium', 'artisan']):
            score *= 0.7
        
        # Price-conscious scoring
        if price > 0:
            if price < 2.0:  # Very affordable
                score *= 1.2
            elif price > 10.0:  # Expensive
                score *= 0.6
    
    else:  # middle income
        # Middle income: balanced preferences
        if 'organic' in text:
            score *= (1 + organic_preference * 0.3)
        if price > 0:
            if 2.0 <= price <= 8.0:  # Moderate pricing
                score *= 1.1
    
    return score


def calculate_price_sensitivity_score(price: float, sensitivity: float) -> float:
    """
    Calculate score based on price sensitivity
    
    Args:
        price: Product price
        sensitivity: Price sensitivity (0-1, where 1 is very sensitive)
    
    Returns:
        float: Price sensitivity score multiplier
    """
    if price <= 0:
        return 1.0
    
    # Higher sensitivity = prefer lower prices
    if sensitivity > 0.7:  # High sensitivity
        if price < 3.0:
            return 1.3
        elif price > 8.0:
            return 0.5
    elif sensitivity < 0.3:  # Low sensitivity
        if price > 8.0:
            return 1.1  # Slight preference for premium
    
    return 1.0


def generate_persona_reason(row: pd.Series, persona: Dict[str, Any], 
                          product_meta: Dict[str, Any]) -> str:
    """
    Generate a textual explanation for why a recommendation fits the persona
    
    Args:
        row: Recommendation row data
        persona: Customer persona dictionary
        product_meta: Product metadata
    
    Returns:
        str: Human-readable explanation
    """
    reasons = []
    product_name = row.get('product_name', 'Unknown')
    category = product_meta.get('category', 'Unknown')
    price = product_meta.get('price', 0)
    
    # Diet-based reasons
    diet_prefs = persona.get('diet_preferences', [])
    for diet in diet_prefs:
        if diet.lower() in product_name.lower() or diet.lower() in category.lower():
            reasons.append(f"Matches {diet} diet")
    
    # Budget reasons
    budget_min = persona.get('budget_min', 0)
    budget_max = persona.get('budget_max', float('inf'))
    if budget_min <= price <= budget_max:
        reasons.append("Within budget")
    
    # Income-based reasons
    income_level = persona.get('income_level', '')
    if income_level == 'high' and 'organic' in product_name.lower():
        reasons.append("Premium organic choice")
    elif income_level == 'low' and any(value in product_name.lower() for value in ['value', 'generic']):
        reasons.append("Great value option")
    
    # Organic preference
    organic_pref = persona.get('organic_preference', 0.5)
    if organic_pref > 0.7 and 'organic' in product_name.lower():
        reasons.append("Organic preference match")
    
    return "; ".join(reasons) if reasons else "General compatibility"


def validate_persona_data(persona: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize persona data
    
    Args:
        persona: Raw persona data
    
    Returns:
        Dict: Validated and normalized persona data
    """
    validated = {}
    
    # Ensure lists are actually lists
    list_fields = ['allergies', 'diet_preferences']
    for field in list_fields:
        value = persona.get(field, [])
        if isinstance(value, str):
            # Split comma-separated strings
            validated[field] = [item.strip() for item in value.split(',') if item.strip()]
        elif isinstance(value, list):
            validated[field] = value
        else:
            validated[field] = []
    
    # Ensure numeric fields are numeric
    numeric_fields = ['budget_min', 'budget_max', 'organic_preference', 'price_sensitivity']
    for field in numeric_fields:
        value = persona.get(field, 0)
        try:
            validated[field] = float(value) if value else 0
        except (ValueError, TypeError):
            validated[field] = 0
    
    # Ensure string fields
    string_fields = ['customer_id', 'income_level']
    for field in string_fields:
        validated[field] = str(persona.get(field, '')) if persona.get(field) else ''
    
    # Set defaults for missing fields
    defaults = {
        'budget_min': 0,
        'budget_max': 100,
        'organic_preference': 0.5,
        'price_sensitivity': 0.5,
        'income_level': 'middle'
    }
    
    for field, default_value in defaults.items():
        if field not in validated or not validated[field]:
            validated[field] = default_value
    
    return validated
