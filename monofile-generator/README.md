# Monofile Generator

Consolidates source modules from `src/adpapi/` into a single Jupyter notebook.

## Usage

```bash
uv run generate-monofile.py
```

Generates `monofile.ipynb` with:
- Consolidated imports at the top
- Markdown headers for each module
- Code from each module (without internal imports)

## Configuration

Edit `config.yaml` to specify module order:

```yaml
module_order:
  - logger.py
  - sessions.py
  - client.py
```
