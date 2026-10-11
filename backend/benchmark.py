import argparse 
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

class ResultHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.rows = []
        self.row = None
        self.cell = None
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag == 'tr':
            self.row = []
        if tag in ('td', 'th') and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)
            if self.cell is not None:
                self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def result_url(result_id):
    result_id = str(result_id)
    if not re.fullmatch(r'[1-9][0-9]*', result_id):
        raise ValueError(f"Invalid GeekBench result ID: {result_id!r}")
    return f'https://browser.geekbench.com/v6/cpu/{result_id}'


def parse_result(html, expected_chip, url):
    page = ResultHTML()
    page.feed(html)
    fields = {}
    for row in page.rows:
        if len(row) >= 2:
            fields.setdefault(row[0], row[1])
    text = ' '.join(' '.join(page.text).split())
    version = re.search(r'Geekbench (6\.\d+\.\d+)(?: Pro)? for macOS AArch64', text)
    if not version:
        raise ValueError(f'{url}: expected a Geekbench 6 macOS CPU result')
    chip = fields.get('Name')
    if chip != expected_chip:
        raise ValueError(f'{url}: expected {expected_chip}, found {chip!r}')
    score = {}
    for key, label in [('singleCore', 'Single-Core Score'), ('multiCore', 'Multi-Core Score')]:
        value = fields.get(label, '').replace(',', '')
        if not re.fullmatch(r'[1-9][0-9]*', value):
            raise ValueError(f'{url}: missing or invalid {label}; page format may have changed')
        score[key] = int(value)
    topology = fields.get('Topology', '')
    cores = re.search(r'(\d+) Cores?\b', topology)
    if not cores:
        raise ValueError(f'{url}: missing CPU core count')
    return {
        'url': url, 'chip': chip, 'version': version.group(1),
        'system': fields.get('Model', 'Unknown'), 'cores': int(cores.group(1)),
        'memory': fields.get('Size', 'Unknown'),
        'operatingSystem': fields.get('Operating System', 'Unknown'),
        **score,
    }


def fetch_result(result_id, expected_chip, html_dir = None):
    url = result_url(result_id)
    print(f'Reading {expected_chip}: {url}', file = sys.stderr)
    if html_dir:
        html = (html_dir / f'{result_id}.html').read_text(encoding = 'utf-8')
    else:
        request = Request(url, headers = {'User-Agent': 'TruthLens-Benchmark-Collector/1.0', 'Accept': 'text/html'})
        with urlopen(request, timeout = 20) as response:
            if response.geturl().rstrip('/') != url:
                raise ValueError(f'{url}: unexpected redirect')
            html = response.read().decode('utf-8')
    return parse_result(html, expected_chip, url)


def make_comparison(entry, current, previous):
    if current['version'] != previous['version']:
        raise ValueError(f"{entry['model']}: GeekBench version differ; choose matching runs")
    current_id = str(entry['currentResult'])
    previous_id = str(entry['previousResult'])
    note = (f"Individual published runs, not generation averages. "
            f"{current['chip']}: {current['cores']} cores, {current['memory']}; "
            f"{previous['chip']}: {previous['cores']} cores, {previous['memory']}. "
            'System configuration and software can affect scores.')
    return {
        'previousGeneration': entry['previousGeneration'],
        'benchmarkName': f"Geekbench {current['version']} · CPU",
        'sources': {'name': 'Geekbench', 'url': 
                    f'https://browser.geekbench.com/v6/cpu/compare/{current_id}?baseline={previous_id}'},
        'note': note,
        'metrics': [
            {'label': label, 'currentScore': current[key],
                'previousScore': previous[key], 'unit': 'score'}
            for key, label in [('singleCore', 'Single-core'), ('multiCore', 'Multi-core')]
        ],
        'results': {'current': current, 'previous': previous},
        'fetchedAt': datetime.now(timezone.utc).isoformat(),
    }


def generate(config, existing, html_dir = None):
    if existing.get('schemaVersion') != 1 or not isinstance(existing.get('models'), dict):
        raise ValueError('Existing output must have schemaVersion 1 and a  models object')
    entries = config.get('comparisons')
    if not isinstance(entries, list) or not entries:
        raise ValueError('Config must contain a nonempty camparisons list')
    updates = {}
    for entry in entries:
        for key in ('model', 'previousGeneration', 'currentResult', 'previousResult'):
            if key not in entry:
                raise ValueError(f'Config entry is missing {key}')
        if entry['model'] in updates:
            raise ValueError(f"Duplicate model: {entry['model']}")
        current = fetch_result(entry['currentResult'], entry['model'], html_dir)
        previous = fetch_result(entry['previousResult'], entry['previousGeneration'], html_dir)
        updates[entry['model']] = make_comparison(entry, current, previous)
    return {**existing, 'models': {**existing['models'], **updates}}


def atomic_write(path, data):
    path.parent.mkdir(parents = True, exist_ok = True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode = 'w', encoding = 'utf-8',dir = path.parent, delete = False) as file:
            temporary = Path(file.name)
            json.dump(data, file, indent = 2, ensure_ascii = False)
            file.write('\n')
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description = __doc__)
    parser.add_argument('--config', type = Path, default = ROOT / 'database/benchmark_sources.json')
    parser.add_argument('--output', type = Path, default = ROOT / 'database/benchmarks.json')
    parser.add_argument('--html-dir', type = Path, help = 'Read saved result-ID.html pages instead of downloading')
    parser.add_argument('--dry-run', action = 'store_true', help = 'Validate and print JSON without writing')
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding = 'utf-8'))
        existing = (json.loads(args.output.read_text(encoding = 'utf-8'))
                    if args.output.exists() else {'schemaVersion': 1, 'models': {}})
        data = generate(config, existing, args.html_dir)
        if args.dry_run:
            print(json.dump(data, indent = 2, ensure_ascii = False))
        else:
            atomic_write(args.output, data)
            print(f'Updated {args.output}')
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Collection failed: {error}\nNo benchmark file was replaced.', file = sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())