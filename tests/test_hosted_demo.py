import importlib.util
import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hosted', ROOT / 'scripts/build_hosted_demo.py')
hosted = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hosted)


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        self.urls += [v for k, v in attrs if k in ('href', 'src') and v]


class HostedDemoTests(unittest.TestCase):
    def test_static_release_is_complete_and_scoped(self):
        (ROOT / 'outputs').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'outputs') as directory:
            base = Path(directory)
            manifest = hosted.build(base)
            self.assertEqual(manifest['mode'], 'historical_static_demo')
            for page in base.glob('*.html'):
                parser = References()
                parser.feed(page.read_text(encoding='utf-8'))
                for url in parser.urls:
                    parsed = urlsplit(url)
                    if not parsed.scheme and parsed.path and not parsed.path.startswith('/'):
                        self.assertTrue((base / parsed.path).exists(), (page.name, url))
            for script in base.glob('*.js'):
                self.assertNotIn('/api/', script.read_text(encoding='utf-8'))
            self.assertFalse((base / 'qa').exists())
            self.assertIn('Closer to the land.', (base / 'index.html').read_text(encoding='utf-8'))
            self.assertIn('id="import-open"', (base / 'workspace.html').read_text(encoding='utf-8'))
            for name in ('reports.html', 'field-review.html'):
                self.assertIn('href="workspace.html"', (base / name).read_text(encoding='utf-8'))
            self.assertNotIn('/api/', (base / 'index.html').read_text(encoding='utf-8'))
            self.assertEqual(json.loads((base / 'data/scouting.json').read_text())['independent_field_outcomes'], 0)
            with self.assertRaises(ValueError):
                hosted.build(base)


if __name__ == '__main__':
    unittest.main()
