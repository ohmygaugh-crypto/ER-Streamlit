"""
Mock grocery data generator for demonstration purposes
"""
import pandas as pd
import numpy as np
import streamlit as st
from typing import Optional

@st.cache_data(show_spinner=False)
def generate_mock_orders(n_customers: int = 500, n_orders: int = 2500, seed: int = 7) -> pd.DataFrame:
    """
    Generate realistic mock grocery order data with intentional co-purchase patterns
    
    Args:
        n_customers: Number of unique customers
        n_orders: Total number of orders to generate
        seed: Random seed for reproducibility
        
    Returns:
        DataFrame with columns: order_id, customer_id, order_timestamp, 
                               product_id, product_name, category, price, quantity
    """
    rng = np.random.default_rng(seed)
    
    # Product catalog with realistic grocery items
    catalog = pd.DataFrame([
        # product_id, product_name, category, price
        ("milk_whole", "Whole Milk", "Dairy", 3.49),
        ("milk_almd", "Almond Milk", "Dairy", 3.99),
        ("bread_wht", "White Bread", "Bakery", 2.49),
        ("bread_whl", "Whole Wheat Bread", "Bakery", 2.99),
        ("eggs_dzn", "Eggs (Dozen)", "Dairy", 2.99),
        ("butter", "Butter", "Dairy", 4.49),
        ("cheddar", "Cheddar Cheese", "Deli", 5.99),
        ("yogurt", "Greek Yogurt", "Dairy", 1.29),
        ("bananas", "Bananas", "Produce", 0.49),
        ("apples", "Apples", "Produce", 0.79),
        ("pb_smoo", "Peanut Butter", "Pantry", 3.79),
        ("jam_strw", "Strawberry Jam", "Pantry", 3.29),
        ("cereal", "Cereal", "Pantry", 4.49),
        ("oats", "Rolled Oats", "Pantry", 3.19),
        ("chicken", "Chicken Breast", "Meat", 6.99),
        ("beef_min", "Ground Beef", "Meat", 5.99),
        ("pasta", "Pasta", "Pantry", 1.49),
        ("sauce", "Tomato Sauce", "Pantry", 2.49),
        ("lettuce", "Lettuce", "Produce", 1.29),
        ("tomato", "Tomatoes", "Produce", 1.59),
        ("chips", "Potato Chips", "Snacks", 3.29),
        ("salsa", "Salsa", "Snacks", 2.99),
        ("tortillas", "Tortillas", "Bakery", 2.49),
        ("avocado", "Avocado", "Produce", 1.19),
        ("coffee", "Ground Coffee", "Beverage", 7.99),
        ("tea", "Black Tea", "Beverage", 3.49),
        ("sugar", "Sugar", "Pantry", 2.19),
        ("flour", "Flour", "Pantry", 2.49),
        ("oil_olv", "Olive Oil", "Pantry", 8.99),
        ("butter_alt", "Plant Butter", "Dairy", 4.99),
    ], columns=["product_id", "product_name", "category", "price"])
    
    # Generate customer IDs
    cust_ids = [f"C{str(i).zfill(5)}" for i in range(n_customers)]
    
    rows = []
    order_counter = 100000
    
    for _ in range(n_orders):
        cust = rng.choice(cust_ids)
        order_id = f"O{order_counter}"
        order_counter += 1
        
        # Simulate weekday vs weekend shopping patterns
        weekday = rng.random() < 0.7
        base_size = rng.integers(3, 7) if weekday else rng.integers(5, 10)
        
        # Build basket with intentional co-purchase patterns
        items = []
        
        # Start with anchor items
        anchors = rng.choice([
            "milk_whole", "bread_whl", "eggs_dzn", "bananas", 
            "pasta", "chips", "coffee"
        ], size=2, replace=False)
        items.extend(anchors.tolist())
        
        # Add complementary items based on anchors (creates co-purchase patterns)
        if "pasta" in anchors:
            items.append("sauce")  # Pasta + sauce
        if "bread_whl" in anchors and rng.random() < 0.5:
            items.append("butter")  # Bread + butter
        if "chips" in anchors and rng.random() < 0.5:
            items.append("salsa")  # Chips + salsa
        if "milk_whole" in anchors and rng.random() < 0.5:
            items.append("cereal")  # Milk + cereal
        
        # Add probabilistic combinations
        if rng.random() < 0.3:
            items.append("pb_smoo")
            if rng.random() < 0.6:
                items.append("jam_strw")  # PB + jam
        if rng.random() < 0.25:
            items.append("yogurt")
        if rng.random() < 0.2:
            items.extend(["lettuce", "tomato"])  # Salad ingredients
        if rng.random() < 0.18:
            items.extend(["tortillas", "salsa"])  # Mexican cooking
        if rng.random() < 0.15:
            items.append("avocado")
        if rng.random() < 0.12:
            items.append("oats")
        if rng.random() < 0.15:
            items.append("oil_olv")
        
        # Fill to target basket size with random items
        while len(set(items)) < base_size:
            items.append(rng.choice(catalog.product_id))
        
        # Remove duplicates
        items = list(set(items))
        
        # Generate order rows with quantities
        order_timestamp = pd.Timestamp("2024-07-01") + pd.Timedelta(
            days=int(rng.integers(0, 60))
        )
        
        for pid in items:
            prod = catalog[catalog.product_id == pid].iloc[0]
            qty = int(max(1, rng.poisson(1)))  # Poisson distribution for quantities
            
            rows.append({
                "order_id": order_id,
                "customer_id": cust,
                "order_timestamp": order_timestamp,
                "product_id": pid,
                "product_name": prod.product_name,
                "category": prod.category,
                "price": float(prod.price),
                "quantity": qty,
            })
    
    return pd.DataFrame(rows)
