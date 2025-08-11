# ER-with-splink
Entity Resolution with splink


## Jupyter Notebook Setup in Cursor

- Create a virtual environment to establish a kernel for the notebook. (helps avoid local dependency conflicts... it's best practice)
```bash
  python3 -m venv .venv
  source .venv/bin/activate      # (or `.venv\Scripts\activate` on Windows)
  pip install ipykernel notebook
```

- ##### You said:
  
  ![Uploaded image](https://files09.oaiusercontent.com/file-MCy6SXVqUKswzM4U5FxSEp?se=2025-06-09T18%3A39%3A28Z&sp=r&sv=2024-08-04&sr=b&rscc=max-age%3D299%2C%20immutable%2C%20private&rscd=attachment%3B%20filename%3D14b34537-e2d3-4910-964b-06555f6122aa.png&sig=aTrCjjO7vWMNKkGd7hnkYyemfiWFQcQmEN93jyq8o/Y%3D)  
  
  

- **Then** open Cursor’s kernel picker → “Python Environments…” → select `./.venv/bin/python`.
- Your notebook will now run completely isolated from Global/Conda packages.
  
  If you don’t create the venv first, you’ll have to switch kernels mid-notebook and potentially re-install dependencies into whatever interpreter you choose. So: **create your venv → install Jupyter support → pick that in VS Code**.



## Initial Environment Setup for splink.ipynb



see environment.yaml for the complete set of packages to install.


```bash
pip install -r environment.yaml
```




## Data Generation

Here is the complete set of commands to get your data generation script working. Please run these in your terminal:


```bash
pip install requests
pip install numpy
pip install nicknames
```

After these packages are installed, you can run the data generation script again:

```bash
python create_fake_data.py --num_profiles 200
```




This should successfully create the fake data, load it into Neo4j, and resolve the errors you were seeing in your notebook.

![image.png](image.png)

