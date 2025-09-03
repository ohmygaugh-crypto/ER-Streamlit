"""
Persona data parsing utilities for various input formats
"""
import json
import pandas as pd
from typing import Dict, Any, List, Optional, Union
from .persona_filtering import validate_persona_data


def parse_persona_file(uploaded_file) -> Optional[Dict[str, Any]]:
    """
    Parse persona data from uploaded file (JSON or CSV)
    
    Args:
        uploaded_file: Streamlit uploaded file object
    
    Returns:
        Dict: Parsed and normalized persona data, or None if parsing fails
    """
    if not uploaded_file:
        return None
    
    try:
        file_type = uploaded_file.name.split('.')[-1].lower()
        
        if file_type == 'json':
            return parse_persona_json(uploaded_file)
        elif file_type == 'csv':
            return parse_persona_csv(uploaded_file)
        else:
            # Try JSON first, then CSV as fallback
            try:
                return parse_persona_json(uploaded_file)
            except:
                return parse_persona_csv(uploaded_file)
    
    except Exception as e:
        print(f"Error parsing persona file: {e}")
        return None


def parse_persona_json(uploaded_file) -> Optional[Dict[str, Any]]:
    """
    Parse persona data from JSON file
    
    Args:
        uploaded_file: Streamlit uploaded file object
    
    Returns:
        Dict: Parsed persona data
    """
    try:
        content = uploaded_file.read().decode('utf-8')
        data = json.loads(content)
        persona = extract_persona_from_json(data)
        return validate_persona_data(persona)
    
    except Exception as e:
        print(f"Error parsing JSON persona: {e}")
        return None


def parse_persona_csv(uploaded_file) -> Optional[Dict[str, Any]]:
    """
    Parse persona data from CSV file
    
    Args:
        uploaded_file: Streamlit uploaded file object
    
    Returns:
        Dict: Parsed persona data
    """
    try:
        persona_df = pd.read_csv(uploaded_file)
        
        if persona_df.empty:
            return None
        
        # Take first row as persona data
        row = persona_df.iloc[0]
        persona = {}
        
        # Map CSV columns to persona fields
        column_mapping = {
            'customer_id': ['customer_id', 'user_id', 'id'],
            'allergies': ['allergies', 'allergens'],
            'diet_preferences': ['diet_preferences', 'diet', 'dietary_restrictions'],
            'budget_min': ['budget_min', 'min_budget'],
            'budget_max': ['budget_max', 'max_budget'],
            'income_level': ['income_level', 'income'],
            'organic_preference': ['organic_preference', 'organic_pref'],
            'price_sensitivity': ['price_sensitivity', 'price_sens']
        }
        
        for persona_field, possible_columns in column_mapping.items():
            for col in possible_columns:
                if col in row.index and pd.notna(row[col]):
                    value = row[col]
                    
                    # Handle list fields (allergies, diet_preferences)
                    if persona_field in ['allergies', 'diet_preferences'] and isinstance(value, str):
                        # Parse comma-separated or bracket-enclosed lists
                        if value.startswith('[') and value.endswith(']'):
                            value = value[1:-1]  # Remove brackets
                        persona[persona_field] = [item.strip().strip('"\'') for item in value.split(',') if item.strip()]
                    else:
                        persona[persona_field] = value
                    break
        
        return validate_persona_data(persona)
    
    except Exception as e:
        print(f"Error parsing CSV persona: {e}")
        return None


def extract_persona_from_json(data: Union[Dict, List]) -> Dict[str, Any]:
    """
    Extract persona data from various JSON structures
    
    Args:
        data: JSON data (dict or list)
    
    Returns:
        Dict: Extracted persona data
    """
    if isinstance(data, list):
        # If it's a list, take the first item
        data = data[0] if data else {}
    
    if not isinstance(data, dict):
        return {}
    
    persona = {}
    
    # Try different JSON structures
    possible_roots = [
        'customer_profile', 'user_profile', 'profile', 
        'customer', 'user', 'persona', 'preferences'
    ]
    
    # First, try to find nested profile data
    profile_data = data
    for root in possible_roots:
        if root in data:
            profile_data = data[root]
            break
    
    # Extract fields with flexible mapping
    field_mappings = {
        'customer_id': ['customer_id', 'user_id', 'id', 'userId', 'customerId'],
        'allergies': ['allergies', 'allergens', 'food_allergies', 'dietary_restrictions'],
        'diet_preferences': ['diet_preferences', 'dietary_preferences', 'diet', 'diets', 'eating_style'],
        'budget_min': ['budget_min', 'min_budget', 'budget_range_min'],
        'budget_max': ['budget_max', 'max_budget', 'budget_range_max'],
        'income_level': ['income_level', 'income', 'income_bracket'],
        'organic_preference': ['organic_preference', 'organic_pref', 'prefers_organic'],
        'price_sensitivity': ['price_sensitivity', 'price_conscious', 'budget_conscious']
    }
    
    for persona_field, json_keys in field_mappings.items():
        for key in json_keys:
            if key in profile_data:
                value = profile_data[key]
                
                # Handle nested budget objects
                if persona_field in ['budget_min', 'budget_max'] and isinstance(value, dict):
                    if persona_field == 'budget_min' and 'min' in value:
                        persona[persona_field] = value['min']
                    elif persona_field == 'budget_max' and 'max' in value:
                        persona[persona_field] = value['max']
                else:
                    persona[persona_field] = value
                break
    
    # Handle special cases for nested structures
    if 'budget' in profile_data and isinstance(profile_data['budget'], dict):
        budget = profile_data['budget']
        if 'min' in budget:
            persona['budget_min'] = budget['min']
        if 'max' in budget:
            persona['budget_max'] = budget['max']
        if 'range' in budget and isinstance(budget['range'], list) and len(budget['range']) >= 2:
            persona['budget_min'] = budget['range'][0]
            persona['budget_max'] = budget['range'][1]
    
    if 'preferences' in profile_data and isinstance(profile_data['preferences'], dict):
        prefs = profile_data['preferences']
        if 'organic' in prefs:
            persona['organic_preference'] = prefs['organic']
        if 'price_sensitivity' in prefs:
            persona['price_sensitivity'] = prefs['price_sensitivity']
    
    return normalize_persona_fields(persona)


def normalize_persona_fields(persona: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize and clean persona field values
    
    Args:
        persona: Raw persona data
    
    Returns:
        Dict: Normalized persona data
    """
    normalized = persona.copy()
    
    # Normalize list fields
    list_fields = ['allergies', 'diet_preferences']
    for field in list_fields:
        if field in normalized:
            value = normalized[field]
            if isinstance(value, str):
                # Handle comma-separated strings
                normalized[field] = [item.strip() for item in value.split(',') if item.strip()]
            elif not isinstance(value, list):
                normalized[field] = [str(value)] if value else []
    
    # Normalize boolean-like fields to float (0-1 scale)
    boolean_fields = ['organic_preference', 'price_sensitivity']
    for field in boolean_fields:
        if field in normalized:
            value = normalized[field]
            if isinstance(value, bool):
                normalized[field] = 1.0 if value else 0.0
            elif isinstance(value, str):
                if value.lower() in ['true', 'yes', 'high']:
                    normalized[field] = 1.0
                elif value.lower() in ['false', 'no', 'low']:
                    normalized[field] = 0.0
                elif value.lower() == 'medium':
                    normalized[field] = 0.5
                else:
                    try:
                        normalized[field] = float(value)
                    except:
                        normalized[field] = 0.5
    
    # Normalize income level
    if 'income_level' in normalized:
        income = str(normalized['income_level']).lower()
        if income in ['high', 'upper', 'wealthy', 'rich']:
            normalized['income_level'] = 'high'
        elif income in ['low', 'lower', 'poor', 'budget']:
            normalized['income_level'] = 'low'
        else:
            normalized['income_level'] = 'middle'
    
    # Ensure numeric fields are numeric
    numeric_fields = ['budget_min', 'budget_max']
    for field in numeric_fields:
        if field in normalized:
            try:
                normalized[field] = float(normalized[field])
            except:
                normalized[field] = 0
    
    return normalized


def parse_grocery_list(uploaded_file) -> Optional[List[str]]:
    """
    Parse grocery list from uploaded file (JSON, Markdown, or Text)
    
    Args:
        uploaded_file: Streamlit uploaded file object
    
    Returns:
        List[str]: List of grocery items, or None if parsing fails
    """
    if not uploaded_file:
        return None
    
    try:
        content = uploaded_file.read().decode('utf-8')
        file_type = uploaded_file.name.split('.')[-1].lower()
        
        if file_type == 'json':
            data = json.loads(content)
            if isinstance(data, list):
                return [str(item).strip() for item in data if item]
            elif isinstance(data, dict) and 'items' in data:
                return [str(item).strip() for item in data['items'] if item]
            else:
                return []
        
        else:  # Markdown or text
            lines = content.split('\n')
            items = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Remove markdown list markers
                if line.startswith('- '):
                    line = line[2:].strip()
                elif line.startswith('* '):
                    line = line[2:].strip()
                elif line.startswith('+ '):
                    line = line[2:].strip()
                elif line.startswith(tuple(f"{i}." for i in range(1, 100))):
                    # Remove numbered list markers
                    line = line.split('.', 1)[1].strip()
                
                if line:
                    items.append(line)
            
            return items
    
    except Exception as e:
        print(f"Error parsing grocery list: {e}")
        return None


def create_sample_persona(persona_type: str = 'balanced') -> Dict[str, Any]:
    """
    Create a sample persona for testing
    
    Args:
        persona_type: Type of persona ('balanced', 'vegan', 'keto', 'budget', 'premium')
    
    Returns:
        Dict: Sample persona data
    """
    personas = {
        'balanced': {
            'customer_id': 'sample_001',
            'allergies': [],
            'diet_preferences': [],
            'budget_min': 5,
            'budget_max': 50,
            'income_level': 'middle',
            'organic_preference': 0.5,
            'price_sensitivity': 0.5
        },
        'vegan': {
            'customer_id': 'vegan_001',
            'allergies': ['dairy'],
            'diet_preferences': ['vegan'],
            'budget_min': 10,
            'budget_max': 80,
            'income_level': 'middle',
            'organic_preference': 0.8,
            'price_sensitivity': 0.3
        },
        'keto': {
            'customer_id': 'keto_001',
            'allergies': [],
            'diet_preferences': ['keto'],
            'budget_min': 15,
            'budget_max': 100,
            'income_level': 'high',
            'organic_preference': 0.6,
            'price_sensitivity': 0.2
        },
        'budget': {
            'customer_id': 'budget_001',
            'allergies': [],
            'diet_preferences': [],
            'budget_min': 2,
            'budget_max': 25,
            'income_level': 'low',
            'organic_preference': 0.2,
            'price_sensitivity': 0.9
        },
        'premium': {
            'customer_id': 'premium_001',
            'allergies': ['gluten'],
            'diet_preferences': ['gluten-free'],
            'budget_min': 20,
            'budget_max': 200,
            'income_level': 'high',
            'organic_preference': 0.9,
            'price_sensitivity': 0.1
        }
    }
    
    return personas.get(persona_type, personas['balanced'])
