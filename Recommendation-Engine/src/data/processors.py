"""
Data processing and validation utilities
"""
import pandas as pd
import streamlit as st
from typing import Dict, List, Optional


class DataProcessor:
    """Handles CSV data validation and column mapping"""
    
    # Required columns for the recommendation engine
    REQUIRED_COLUMNS = [
        "order_id", "customer_id", "order_timestamp",
        "product_id", "product_name", "category", "price", "quantity"
    ]
    
    # Column aliases for flexible CSV mapping
    COLUMN_ALIASES = {
        "order_id": ["orderid", "order id", "txn_id", "basket_id", "transaction_id"],
        "customer_id": ["customerid", "customer id", "user_id", "account_id", "cust_id"],
        "order_timestamp": ["timestamp", "order_date", "datetime", "date", "order_time"],
        "product_id": ["sku", "item_id", "product code", "product_code", "item_code"],
        "product_name": ["item_name", "name", "title", "product", "item"],
        "category": ["dept", "department", "aisle", "product_category", "cat"],
        "price": ["unit_price", "item_price", "amount", "cost", "product_price"],
        "quantity": ["qty", "count", "units", "amount_purchased", "num_items"]
    }
    
    def validate_and_process(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Validate uploaded CSV and map columns to required schema
        
        Args:
            df: Raw uploaded DataFrame
            
        Returns:
            Processed DataFrame or None if validation fails
        """
        try:
            # Attempt column mapping
            column_mapping = self._map_columns(df)
            
            # Check if all required columns were mapped
            missing_columns = [col for col, mapped in column_mapping.items() if mapped is None]
            
            if missing_columns:
                st.warning(
                    f"⚠️ Could not map required columns: {', '.join(missing_columns)}. "
                    "Using mock data instead."
                )
                return None
            
            # Apply column mapping
            mapped_df = df.rename(columns={
                mapped: required for required, mapped in column_mapping.items() 
                if mapped is not None
            })
            
            # Select only required columns
            processed_df = mapped_df[self.REQUIRED_COLUMNS].copy()
            
            # Data type conversions and cleaning
            processed_df = self._clean_data(processed_df)
            
            # Validation checks
            if not self._validate_data(processed_df):
                return None
            
            return processed_df
            
        except Exception as e:
            st.error(f"❌ Error processing data: {str(e)}")
            return None
    
    def _map_columns(self, df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """Map CSV columns to required schema using aliases"""
        column_mapping = {}
        
        # Create lowercase lookup for case-insensitive matching
        lowercase_columns = {col.lower().strip(): col for col in df.columns}
        
        for required_col in self.REQUIRED_COLUMNS:
            mapped_col = None
            
            # First, try exact match
            if required_col in df.columns:
                mapped_col = required_col
            else:
                # Try aliases
                for alias in self.COLUMN_ALIASES.get(required_col, []):
                    if alias.lower() in lowercase_columns:
                        mapped_col = lowercase_columns[alias.lower()]
                        break
            
            column_mapping[required_col] = mapped_col
        
        return column_mapping
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and convert data types"""
        df = df.copy()
        
        # Convert data types
        df["order_id"] = df["order_id"].astype(str)
        df["customer_id"] = df["customer_id"].astype(str)
        df["product_id"] = df["product_id"].astype(str)
        df["product_name"] = df["product_name"].astype(str)
        df["category"] = df["category"].fillna("Unknown").astype(str)
        
        # Convert numeric columns
        df["price"] = pd.to_numeric(df["price"], errors='coerce').fillna(0)
        df["quantity"] = pd.to_numeric(df["quantity"], errors='coerce').fillna(1)
        
        # Convert timestamp
        df["order_timestamp"] = pd.to_datetime(df["order_timestamp"], errors='coerce')
        
        # Remove rows with invalid data
        df = df.dropna(subset=["order_id", "product_id", "product_name"])
        
        return df
    
    def _validate_data(self, df: pd.DataFrame) -> bool:
        """Validate processed data quality"""
        if df.empty:
            st.error("❌ No valid data rows after processing")
            return False
        
        # Check minimum data requirements
        n_orders = df["order_id"].nunique()
        n_products = df["product_id"].nunique()
        
        if n_orders < 2:
            st.error("❌ Need at least 2 orders for analysis")
            return False
        
        if n_products < 2:
            st.error("❌ Need at least 2 products for analysis")
            return False
        
        # Check for reasonable price values
        if df["price"].max() <= 0:
            st.warning("⚠️ All prices are zero or negative")
        
        return True
    
    def get_data_summary(self, df: pd.DataFrame) -> Dict[str, any]:
        """Generate summary statistics for processed data"""
        return {
            "total_rows": len(df),
            "unique_orders": df["order_id"].nunique(),
            "unique_customers": df["customer_id"].nunique(),
            "unique_products": df["product_id"].nunique(),
            "unique_categories": df["category"].nunique(),
            "date_range": {
                "start": df["order_timestamp"].min(),
                "end": df["order_timestamp"].max()
            },
            "price_range": {
                "min": df["price"].min(),
                "max": df["price"].max(),
                "avg": df["price"].mean()
            },
            "avg_basket_size": df.groupby("order_id").size().mean()
        }
