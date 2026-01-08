# SyncroHuntressAPITools

A CLI tool to compare agents between Syncro and Huntress platforms.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ASpur/SyncroHuntressAPITools.git
cd SyncroHuntressAPITools
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure your API credentials:

Run the tool once to generate a `settings.json` template:
```bash
python main.py
```

Then edit `settings.json` with your credentials:
```json
{
    "SyncroAPIKey": "your-syncro-api-key",
    "SyncroSubDomain": "your-subdomain",
    "HuntressAPIKey": "your-huntress-api-key",
    "huntressApiSecretKey": "your-huntress-secret-key",
    "debug": false
}
```

## Usage

Compare Syncro and Huntress agents:
```bash
python main.py --compare
```

### Options

| Flag | Description |
|------|-------------|
| `-c`, `--compare` | Compare Syncro and Huntress agents |
| `-o FILE`, `--output FILE` | Output results to a file |
| `-f FORMAT`, `--format FORMAT` | Output format: `csv` or `ascii` (default: csv) |
| `--no-color` | Disable colored output |

### Examples

Output comparison to CSV file:
```bash
python main.py --compare --output results.csv
```

Display as ASCII table:
```bash
python main.py --compare --format ascii
```

## Running Tests

```bash
pytest
```
