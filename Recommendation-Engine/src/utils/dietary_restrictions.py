"""
Dietary restrictions and compatibility utilities for product filtering
"""
from typing import List, Dict, Any


def check_diet_exclusions(product_name: str, category: str, diet_preferences: List[str]) -> bool:
    """
    Check if product should be HARD EXCLUDED based on strict dietary restrictions
    
    Args:
        product_name: Name of the product
        category: Product category
        diet_preferences: List of dietary restrictions (e.g., ['gluten-free', 'vegan'])
    
    Returns:
        bool: True if product should be excluded, False if safe
    """
    if not diet_preferences:
        return False
    
    text = f"{product_name} {category}".lower()
    
    for diet in diet_preferences:
        diet_lower = diet.lower()
        
        if diet_lower == 'gluten-free':
            # HARD EXCLUSION for gluten-containing products
            gluten_keywords = ['wheat', 'bread', 'pasta', 'flour', 'barley', 'rye', 'malt', 'cereal']
            if any(gluten_word in text for gluten_word in gluten_keywords):
                return True  # EXCLUDE this product completely
        
        elif diet_lower == 'vegan':
            # HARD EXCLUSION for animal products
            animal_products = ['beef', 'chicken', 'pork', 'fish', 'meat', 'dairy', 'milk', 'cheese', 'butter', 'egg', 'honey']
            if any(animal in text for animal in animal_products):
                return True  # EXCLUDE this product completely
        
        elif diet_lower == 'vegetarian':
            # HARD EXCLUSION for meat products
            meat_products = ['beef', 'chicken', 'pork', 'fish', 'meat', 'bacon', 'ham', 'sausage']
            if any(meat in text for meat in meat_products):
                return True  # EXCLUDE this product completely
        
        elif diet_lower == 'keto':
            # HARD EXCLUSION for high-carb products
            high_carb_products = ['bread', 'pasta', 'rice', 'potato', 'sugar', 'flour', 'cereal', 'oats']
            if any(carb in text for carb in high_carb_products):
                return True  # EXCLUDE this product completely
        
        elif diet_lower in ['diabetic-friendly', 'low-sugar']:
            # HARD EXCLUSION for high-sugar products
            high_sugar_products = ['sugar', 'candy', 'chocolate', 'cake', 'cookie', 'soda', 'juice']
            if any(sugar_item in text for sugar_item in high_sugar_products):
                return True  # EXCLUDE this product completely
    
    return False  # Product is safe for all dietary restrictions


def calculate_diet_compatibility(product_name: str, category: str, diet_preferences: List[str]) -> float:
    """
    Calculate positive scoring for diet-compatible products (exclusions handled separately)
    
    Args:
        product_name: Name of the product
        category: Product category
        diet_preferences: List of dietary preferences
    
    Returns:
        float: Compatibility score multiplier (1.0 = neutral, >1.0 = boost, <1.0 = penalty)
    """
    if not diet_preferences:
        return 1.0
    
    text = f"{product_name} {category}".lower()
    score = 1.0
    
    for diet in diet_preferences:
        diet_lower = diet.lower()
        
        if diet_lower == 'vegetarian':
            # Boost vegetarian-friendly products
            if 'vegetarian' in text or category in ['produce', 'dairy']:
                score *= 1.3
            elif any(plant in text for plant in ['plant', 'veggie', 'bean', 'lentil']):
                score *= 1.2
        
        elif diet_lower == 'vegan':
            # Boost vegan-friendly products
            if 'vegan' in text or category == 'produce':
                score *= 1.5
            elif any(plant in text for plant in ['plant', 'almond', 'soy', 'coconut', 'oat']):
                score *= 1.3
        
        elif diet_lower == 'gluten-free':
            # Boost gluten-free products
            if 'gluten-free' in text:
                score *= 1.4
            elif category in ['produce', 'meat', 'dairy'] and 'bread' not in text:
                score *= 1.1  # Naturally gluten-free categories
        
        elif diet_lower == 'keto':
            # Boost keto-friendly products
            if any(keto in text for keto in ['keto', 'low-carb']):
                score *= 1.4
            elif any(keto_food in text for keto_food in ['cheese', 'butter', 'oil', 'avocado']):
                score *= 1.3
            elif category in ['meat', 'dairy'] and 'sugar' not in text:
                score *= 1.2
        
        elif diet_lower in ['diabetic-friendly', 'low-sugar']:
            # Boost low-sugar products
            if any(low_sugar in text for low_sugar in ['sugar-free', 'no-sugar', 'diabetic']):
                score *= 1.4
            elif category in ['produce', 'meat'] and 'sweet' not in text:
                score *= 1.2
    
    return score


def contains_allergen(product_name: str, category: str, allergen: str) -> bool:
    """
    Check if product contains a specific allergen
    
    Args:
        product_name: Name of the product
        category: Product category
        allergen: Allergen to check for (e.g., 'nuts', 'dairy', 'eggs')
    
    Returns:
        bool: True if allergen is detected, False otherwise
    """
    allergen_keywords = {
        'nuts': ['nuts', 'peanut', 'almond', 'walnut', 'cashew', 'pecan', 'hazelnut'],
        'dairy': ['milk', 'cheese', 'butter', 'cream', 'yogurt', 'dairy'],
        'eggs': ['egg', 'eggs'],
        'soy': ['soy', 'soybean', 'tofu'],
        'fish': ['fish', 'salmon', 'tuna', 'cod'],
        'shellfish': ['shrimp', 'crab', 'lobster', 'shellfish'],
        'sesame': ['sesame', 'tahini'],
        'gluten': ['wheat', 'barley', 'rye', 'gluten']
    }
    
    allergen_lower = allergen.lower()
    keywords = allergen_keywords.get(allergen_lower, [allergen_lower])
    text_to_check = f"{product_name} {category}".lower()
    
    return any(keyword in text_to_check for keyword in keywords)


# Dietary restriction categories and their associated keywords
DIETARY_RESTRICTIONS = {
    'gluten-free': {
        'exclusions': ['wheat', 'bread', 'pasta', 'flour', 'barley', 'rye', 'malt', 'cereal'],
        'boosts': ['gluten-free'],
        'naturally_safe_categories': ['produce', 'meat', 'dairy']
    },
    'vegan': {
        'exclusions': ['beef', 'chicken', 'pork', 'fish', 'meat', 'dairy', 'milk', 'cheese', 'butter', 'egg', 'honey'],
        'boosts': ['vegan', 'plant', 'almond', 'soy', 'coconut', 'oat'],
        'naturally_safe_categories': ['produce']
    },
    'vegetarian': {
        'exclusions': ['beef', 'chicken', 'pork', 'fish', 'meat', 'bacon', 'ham', 'sausage'],
        'boosts': ['vegetarian', 'plant', 'veggie', 'bean', 'lentil'],
        'naturally_safe_categories': ['produce', 'dairy']
    },
    'keto': {
        'exclusions': ['bread', 'pasta', 'rice', 'potato', 'sugar', 'flour', 'cereal', 'oats'],
        'boosts': ['keto', 'low-carb', 'cheese', 'butter', 'oil', 'avocado'],
        'naturally_safe_categories': ['meat', 'dairy']
    },
    'diabetic-friendly': {
        'exclusions': ['sugar', 'candy', 'chocolate', 'cake', 'cookie', 'soda', 'juice'],
        'boosts': ['sugar-free', 'no-sugar', 'diabetic'],
        'naturally_safe_categories': ['produce', 'meat']
    }
}


def get_dietary_info(diet_type: str) -> Dict[str, Any]:
    """
    Get dietary restriction information for a specific diet type
    
    Args:
        diet_type: Type of diet (e.g., 'gluten-free', 'vegan')
    
    Returns:
        Dict containing exclusions, boosts, and safe categories
    """
    return DIETARY_RESTRICTIONS.get(diet_type.lower(), {})
