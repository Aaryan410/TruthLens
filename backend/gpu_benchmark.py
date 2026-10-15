import argparse 
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from benchmark import ResultHTML, atomic_write

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_APIS = ('Vulkan', 'OpenCL', 'Metal')


def result_url(result_id):
    result_id = str(result_id)
    if not re.fullmatch(r'[1-9][0-9]*', result_id):
        raise ValueError(f'Invalid GPU result ID: {result_id!r}')
    return f'https://browser.geekbench.com/v6/compute/{result_id}'


def parse_gpu_result(html, expected_device, api, url):
    if api not in SUPPORTED_APIS:
        raise ValueError(f'Unsupported GPU API: {api}')
    page = ResultHTML()
    page.feed(html)
    fields = {}
    for row in page.rows:
        if len(row) >= 2:
            if row[0] in fields and fields[row[0]] != row[1]:
                if row[0] in ('Device Name', f'{api} Score'):
                    raise ValueError(f'{url}: ambigious device or score')
            fields.setdefault(row[0], row[1])
    text = ' '.join(' '.join(page.text).split())
    version = re.search(r'Geekbench (6\.\d+\.\d+)(?: Pro)? for (macOS|Windows|Linux) (AArch64|AVX2|SSE2|AVX)\b', text)
    if not version:
        raise ValueError(f'{url}: expected a supported GeekBench 6 GPU result')
    if re.search(r'\bInvalid\b', text, re.IGNORECASE):
        raise ValueError(f'{url}: GeekBench marks this result invalid')
    device = fields.get('Device Name')
    if device != expected_device:
        raise ValueError(f'{url}: expected {expected_device!r}, found {device!r}')
    score = fields.get(f'{api} Score', '').replace(',', '')
    if not re.fullmatch(r'[1-9][0-9]*', score):
        raise ValueError(f'{url}: missing or invalid {api} Score')
    return {
        'url': url, 'device': device, 'api': api, 'score': int(score),
        'version': version.group(1), 'platform': version.group(2),
        'architecture': version.group(3),
        'system': fields.get('Model', 'Unknown'),
        'cpu': fields.get('Name', 'Unknown'),
        'systemMemory': fields.get('Size', 'Unknown'),
        'operatingSystem': fields.get('Operating System', 'Unknown'),
        'uploadDate': fields.get('Upload Date', 'Unknown'),
    }


def fetch_gpu_result(result_id, device, api, html_dir = None):
    url = result_url(result_id)
    if html_dir is not None:
        path = html_dir / f'{result_id}.html'
        print(f'Reading saved GPU page: {path}', file = sys.stderr)
        html = path.read_text(encoding = 'utf-8')
    else:
        print(f'Downloading GPU page: {url}', file = sys.stderr)
        request = Request(url, headers = {'User-Agent': 'TruthLens-Benchmark-Collector/1.0', 'Accept': 'text/html',})
        with urlopen(request, timeout = 20) as response:
            if response.geturl().rstrip('/') != url:
                raise ValueError(f'{url}: unexpected redirect')
            html = response.read().decode('utf-8')
    return parse_gpu_result(html, device, api, url)


def make_gpu_comparison(entry, current, previous):
    for key in ('version', 'api', 'platform', 'architecture'):
        if current[key] != previous[key]:
            raise ValueError(f"{entry['model']}: GPU runs have different {key} values")
    return {
        'previousGeneration': entry['previousGeneration'],
        'benchmarkName': f"Geekbench {current['version']} · GPU compute · {current['api']}",
        'source': {
            'name': 'Geekbench',
            'url': (
                f"https://browser.geekbench.com/v6/compute/compare/{entry['currentResult']}"
                f"?baseline={entry['previousResult']}"
            ),
        },
        'note': (
            'Individual published runs, not generation averages. '
            f"Current text system: {current['cpu']}, {current['systemMemory']} system RAM. "
            f"Previous text system: {previous['cpu']}, {previous['systemMemory']} system RAM. "
            'This is a GPU compute score, not gaming FPS. '
            'Drivers, power settings and system configuration can affect scores.'
        ),
        'metrics': [{
            'label': f"{current['api']} compute", 'currentScore': current['score'],
            'previousScore': previous['score'], 'unit': 'score',
        }],
        'results': {'current': current, 'previous': previous},
        'fetchedAt': datetime.now(timezone.utc).isoformat(),
    }


def generate_gpu(config, existing, html_dir = None):
    if existing.get('schemaVersion') != 1 or not isinstance(existing.get('models'), dict):
        raise ValueError('Output must have schemaVersion 1 and a models object')
    entries = config.get('comparisons')
    if not isinstance(entries, list) or not entries:
        raise ValueError('GPU config needs a nonempty comparisons list')
    updates = {}
    for entry in entries:
        for key in ('model', 'previousGeneration', 'currentResult', 'previousResult', 'api'):
            if key not in entry:
                raise ValueError(f'GPU config entry is missing {key}')
        if entry['model'] in updates:
            raise ValueError(f"Duplicate GPU model: {entry['model']}")
        current = fetch_gpu_result(entry['currentResult'], entry.get('currentDevice', entry['model']), entry['api'], html_dir)
        previous = fetch_gpu_result(entry['previousResult'], entry.get('previousDevice', entry['previousGeneration']), entry['api'], html_dir)
        updates[entry['model']] = make_gpu_comparison(entry, current, previous)
    return {**existing, 'models': {**existing['models'], **updates,},}


def main():
    parser = argparse.ArgumentParser(description = __doc__)
    parser.add_argument('--config', type = Path, default = ROOT / 'database/benchmark/gpu_benchmark_sources.json')
    parser.add_argument('--output', type = Path, default = ROOT / 'database/benchmarks.json')
    parser.add_argument('--html-dir', type = Path, help = 'Read saved GPU result-ID.html pages')
    parser.add_argument('--dry-run', action = 'store_true', help = 'Print JSON without replacing the output')
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding = 'utf-8'))
        existing = json.loads(args.output.read_text(encoding = 'utf-8'))
        data = generate_gpu(config, existing, args.html_dir)
        if args.dry_run:
            print(json.dumps(data, indent = 2, ensure_ascii = False))
        else:
            atomic_write(args.output, data)
            print(f'Updated {args.output}')
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'GPU collection failed: {error}\nNo benchmark file was replaced.', file = sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
