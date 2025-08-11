# Dockerfile for Splink Entity Resolution Project
FROM continuumio/miniconda3:latest

# Set working directory
WORKDIR /app

# Copy environment file first
COPY environment-docker.yaml .

# Create conda environment
RUN conda env create -f environment-docker.yaml

# Make RUN commands use the new environment
SHELL ["conda", "run", "-n", "er_with_splink", "/bin/bash", "-c"]

# Install additional packages if needed
RUN pip install jupyterlab streamlit

# Copy application code
COPY . .

# Expose ports
EXPOSE 8888 8501

# Activate environment and start bash
CMD ["conda", "run", "--no-capture-output", "-n", "er_with_splink", "bash"]
