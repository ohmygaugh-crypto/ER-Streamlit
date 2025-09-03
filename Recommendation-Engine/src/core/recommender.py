"""
Recommendation engine using network-based collaborative filtering
"""
import pandas as pd
import numpy as np
import math
from collections import defaultdict
from typing import List, Dict, Any, Optional


class RecommendationEngine:
    """Network-based recommendation engine for cart add-ons"""
    
    def __init__(self, default_topk: int = 5):
        self.default_topk = default_topk
    
    def compute_recommendations(
        self,
        cart_items: List[str],
        item_stats: Dict[str, Any],
        topk: int = None,
        exclude_in_cart: bool = True,
        alpha: float = 1.0
    ) -> pd.DataFrame:
        """
        Generate recommendations based on current cart items
        
        Algorithm:
        For each candidate item t, score = Σ[s∈cart] lift(s,t) × log(1 + co_count(s,t))
        
        Args:
            cart_items: List of product IDs currently in cart
            item_stats: Output from NetworkAnalyzer.build_item_stats
            topk: Number of recommendations to return
            exclude_in_cart: Whether to exclude items already in cart
            alpha: Weight parameter for co-occurrence count
            
        Returns:
            DataFrame with recommendations and explanations
        """
        if topk is None:
            topk = self.default_topk
            
        pairs_df = item_stats["pairs"]
        meta = item_stats["meta"]
        
        if pairs_df.empty or not cart_items:
            return pd.DataFrame()
        
        # Build bidirectional lookup for pair metrics
        pair_index = defaultdict(dict)
        for _, row in pairs_df.iterrows():
            # Store both directions for symmetric access
            pair_index[row.item_a][row.item_b] = row
            pair_index[row.item_b][row.item_a] = row
        
        # Score candidate items
        candidate_scores = defaultdict(lambda: {"score": 0.0, "explanations": []})
        
        for cart_item in cart_items:
            if cart_item not in pair_index:
                continue
                
            neighbors = pair_index[cart_item]
            for candidate_item, pair_data in neighbors.items():
                if exclude_in_cart and candidate_item in cart_items:
                    continue
                
                # Calculate weighted score: lift × log(1 + co_count)
                lift_score = float(pair_data.lift)
                count_weight = math.log1p(float(pair_data.co_count)) ** alpha
                item_score = lift_score * count_weight
                
                candidate_scores[candidate_item]["score"] += item_score
                candidate_scores[candidate_item]["explanations"].append({
                    "from_item": cart_item,
                    "lift": float(pair_data.lift),
                    "support_ab": float(pair_data.support_ab),
                    "confidence_a_to_b": float(pair_data.confidence_a_to_b),
                    "co_count": int(pair_data.co_count),
                    "contribution": item_score
                })
        
        # Rank candidates by score
        ranked_items = sorted(
            candidate_scores.items(), 
            key=lambda x: x[1]["score"], 
            reverse=True
        )[:topk]
        
        # Build recommendation dataframe
        recommendations = []
        for product_id, score_info in ranked_items:
            metadata = meta.get(product_id, {
                "product_name": product_id, 
                "category": "", 
                "price": np.nan
            })
            
            # Find the strongest contributing explanation
            best_explanation = max(
                score_info["explanations"], 
                key=lambda x: x["lift"]
            )
            
            recommendations.append({
                "product_id": product_id,
                "product_name": metadata.get("product_name", product_id),
                "category": metadata.get("category", ""),
                "price": metadata.get("price", np.nan),
                "score": score_info["score"],
                "why_from": best_explanation["from_item"],
                "lift": best_explanation["lift"],
                "support_ab": best_explanation["support_ab"],
                "confidence_a_to_b": best_explanation["confidence_a_to_b"],
                "co_count": best_explanation["co_count"],
            })
        
        return pd.DataFrame(recommendations)
    
    def estimate_revenue_uplift(
        self,
        recommendations_df: pd.DataFrame,
        margin_percentage: float = 35.0,
        max_acceptance_rate: float = 0.6
    ) -> pd.DataFrame:
        """
        Estimate potential revenue uplift from recommendations
        
        Args:
            recommendations_df: Output from compute_recommendations
            margin_percentage: Assumed profit margin percentage
            max_acceptance_rate: Maximum acceptance probability cap
            
        Returns:
            DataFrame with uplift estimates added
        """
        if recommendations_df.empty:
            return recommendations_df
        
        df = recommendations_df.copy()
        
        # Normalize scores to create acceptance probabilities
        scores = df["score"].values
        if len(scores) > 0 and scores.max() > 0:
            # Normalize to [0, max_acceptance_rate]
            normalized_probs = (scores / scores.max()) * max_acceptance_rate
        else:
            normalized_probs = np.zeros_like(scores)
        
        # Calculate potential margin uplift
        prices = df["price"].fillna(0).values
        margins = prices * (margin_percentage / 100.0)
        expected_uplift = normalized_probs * margins
        
        # Add columns
        df["est_acceptance_prob"] = normalized_probs
        df["est_margin_per_item"] = margins
        df["est_margin_uplift"] = expected_uplift
        
        return df
    
    def explain_recommendation(
        self,
        product_id: str,
        cart_items: List[str],
        item_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Provide detailed explanation for why an item is recommended
        
        Args:
            product_id: The recommended product
            cart_items: Current cart items
            item_stats: Item statistics
            
        Returns:
            Dictionary with detailed explanation
        """
        pairs_df = item_stats["pairs"]
        meta = item_stats["meta"]
        
        # Find all connections between recommended item and cart items
        connections = []
        for cart_item in cart_items:
            # Check both directions
            pair_forward = pairs_df[
                (pairs_df["item_a"] == cart_item) & 
                (pairs_df["item_b"] == product_id)
            ]
            pair_backward = pairs_df[
                (pairs_df["item_a"] == product_id) & 
                (pairs_df["item_b"] == cart_item)
            ]
            
            if not pair_forward.empty:
                row = pair_forward.iloc[0]
                connections.append({
                    "cart_item": cart_item,
                    "cart_item_name": meta.get(cart_item, {}).get("product_name", cart_item),
                    "lift": float(row.lift),
                    "confidence": float(row.confidence_a_to_b),
                    "support": float(row.support_ab),
                    "co_count": int(row.co_count)
                })
            elif not pair_backward.empty:
                row = pair_backward.iloc[0]
                connections.append({
                    "cart_item": cart_item,
                    "cart_item_name": meta.get(cart_item, {}).get("product_name", cart_item),
                    "lift": float(row.lift),
                    "confidence": float(row.confidence_b_to_a),
                    "support": float(row.support_ab),
                    "co_count": int(row.co_count)
                })
        
        product_meta = meta.get(product_id, {})
        
        return {
            "product_id": product_id,
            "product_name": product_meta.get("product_name", product_id),
            "category": product_meta.get("category", ""),
            "price": product_meta.get("price", np.nan),
            "connections": connections,
            "total_connections": len(connections)
        }
