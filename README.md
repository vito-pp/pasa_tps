# TPs PASA

Use this setup for any TP/project that uses Python notebooks.

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Open the `.ipynb` file in VS Code and select `.venv` as the notebook kernel.

## Adding dependencies

Install the package normally:

```bash
pip install <package>
```

Then update the dependency file if needed:

```bash
pip freeze > requirements.txt
```