# PathLex

PathLex is a browser-based tool for creating branching English stories with vocabulary practice along each path. This repository contains the PathLex application, automated tests, and a reproducible comparison of repair strategies.

## Requirements

- Python 3.11 or newer.
- A modern web browser.
- Matplotlib for benchmark analysis. The web server uses only the Python standard library.
- An OpenAI-compatible API endpoint and key for live story authoring.

## Install

From the repository root on macOS or Linux:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate the environment with `.venv\Scripts\Activate.ps1` in PowerShell.

## Configure and run

Copy `.env.example` to `.env`. Edit the local file and set `PATHLEX_LLM_BASE_URL`, `PATHLEX_LLM_MODEL`, and `PATHLEX_LLM_API_KEY` for your provider. The template also defines the local bind address, database directory, graph limits, request timeouts, and repair budgets. The server reads these settings from the environment.

```bash
cp .env.example .env
```

After editing `.env`, load the configuration and start the local server:

```bash
set -a
. ./.env
set +a
python -m pathlex
```

Open <http://127.0.0.1:8080>. The interface and `/api/health` can be accessed without an API key. Live story authoring requires a configured model provider. Store credentials in environment variables or an untracked local configuration file.

1. In **Teacher studio**, enter a title such as *The Lighthouse Route* and select B1. Add *navigate* as a target verb with the meaning *to find or plan a route*. Set the contexts and practice requirements.
2. Compile the unit and inspect the path audit. Publish the unit once the system reports it as verified.
3. In **Story library**, open the published unit and follow a branch through the story.

## Check the system

```bash
python -m unittest discover -s tests -v
```

The tests cover graph planning, path auditing, repair, persistence, and the HTTP interface. All tests can run without a model API key.

## Reproduce the benchmark evaluation

Run the following commands from the repository root. The generated outputs are written to `method_validation/`. Keep a separate working copy if you wish to compare the reproduced results with the distributed files.

```bash
python method_validation/data/build_dataset.py
python method_validation/analysis/run_methods.py
python method_validation/analysis/analyze_results.py
python method_validation/analysis/validate_artifacts.py
```

The first command is optional when using the bundled benchmark specifications.

The evaluation compares GLOBAL-REPAIR, MEAN-PATH, and PathLex-MINIMAX across 240 benchmark specifications. For each specification, all three methods use the same graph, candidate materials, verifier outputs, and repair budget.

The result tables and figures are available in `method_validation/results/`.

An additional 24 specifications are used to evaluate performance under boundary conditions.

After installation, the complete benchmark evaluation can be reproduced without network access or a model API key.

## Repository layout

| Path | Contents |
| --- | --- |
| `pathlex/` | Web application, story planning, generation, verification, and repair |
| `openai_messages_client.py` | Model API client used by the application |
| `tests/` | System and HTTP tests |
| `method_validation/data/` | Benchmark specification builder, vocabulary bank, evaluation inputs, and reference records |
| `method_validation/analysis/` | Repair strategy evaluation, statistical analysis, visualization, and result validation |
| `method_validation/predictions/` | Saved verifier outputs and repair strategy results |
| `method_validation/results/` | Benchmark result tables and figures |
| `MANIFEST.json` | SHA-256 checksums for the packaged files |
