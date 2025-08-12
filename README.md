---
title: Entity Resolution Network Analysis
emoji: 🕸️
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: 1.48.0
app_file: visualize_ER_networks_from_csv.py
pinned: false
license: mit
---

# Entity Resolution Network Analysis

A Streamlit application for entity resolution and network analysis of CSV data using similarity algorithms and interactive graph visualization.

## Features

- **CSV Upload & Processing**: Upload CSV files for entity resolution
- **Similarity Matching**: Configurable similarity thresholds using Jaro-Winkler algorithm
- **Interactive Network Graphs**: Powered by st-link-analysis and Cytoscape.js
- **Community Detection**: Automatic clustering of similar entities
- **Export Results**: Download processed data with community IDs
- **Red-line Comparison**: Visual diff of similar but not identical records

## Usage

1. Upload a CSV file using the sidebar
2. Configure similarity columns and threshold
3. Click "Run Entity Resolution" to process
4. Explore the interactive network graph
5. Download results with community assignments

## Technology Stack

- **Streamlit**: Web application framework
- **NetworkX**: Graph analysis and community detection
- **st-link-analysis**: Interactive network visualization
- **Jellyfish**: String similarity algorithms
- **Pandas/NumPy**: Data processing

## Demo Data

The app includes mock data generation for testing and demonstration purposes.