"""
Setup script for the Recommendation Engine
"""
from setuptools import setup, find_packages

setup(
    name="recommendation-engine",
    version="1.0.0",
    description="Network Analytics for Retail Recommendations",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "streamlit>=1.28.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "networkx>=3.1.0",
        "plotly>=5.15.0",
        "scikit-learn>=1.3.0",
        "tqdm>=4.65.0",
    ],
    extras_require={
        "viz": ["st-link-analysis>=0.1.0"],
        "dev": ["pytest>=7.0.0"],
    },
)
