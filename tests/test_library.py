import argparse
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


search = module('search_books')
download = module('download_books')


class LibraryTests(unittest.TestCase):
    def test_catalog_integrity(self):
        data = json.loads((ROOT / '心理学学习研究/catalog.json').read_text(encoding='utf-8'))
        ids = [x['id'] for x in data['items']]
        self.assertEqual(len(ids), len(set(ids)))
        schools = {s['id'] for s in data['schools']}
        for item in data['items']:
            self.assertIn(item['school'], schools)
            self.assertIn(item['kind'], {'book', 'article'})
            self.assertTrue(item['url'].startswith('https://'))
            self.assertNotIn(' ', item['url'])
            self.assertTrue(item['edition'])
            self.assertTrue(item['rights'])
        self.assertEqual(schools, {b['school'] for b in data['items']})

    def test_open_library_keys_and_no_false_download_permission(self):
        for key in ['OL123W', '/works/OL123W']:
            records = list(search.candidates('openlibrary', {'docs': [{'key': key, 'title': 'A Book', 'ebook_access': 'borrowable'}]}, 'author'))
            self.assertEqual(records[0]['url'], 'https://openlibrary.org/works/OL123W')
            self.assertIn('不构成转载授权', records[0]['review_status'])
            self.assertNotIn('download_url', records[0])
        with self.assertRaises(ValueError):
            search.normalize_work_key('https://untrusted.invalid/')

    def test_partial_failure_preserves_previous_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            old = {'id': 'openlibrary:/works/OL1W', 'title': 'Old', 'authors': [], 'url': 'https://openlibrary.org/works/OL1W', 'provider': 'Open Library', 'review_status': 'pending'}
            path = Path(directory) / 'candidates.json'
            path.write_text(json.dumps({'items': [old]}), encoding='utf-8')
            result = {'results': [{'id': 42, 'title': 'New', 'authors': [], 'copyright': False}]}
            with patch.object(search, 'fetch_json', side_effect=[result, TimeoutError('timeout')]), patch.object(search.time, 'sleep'):
                status = search.run(argparse.Namespace(output=directory, max_queries=2))
            data = json.loads(path.read_text())
            self.assertEqual(status, 0)
            self.assertEqual(len(data['items']), 2)
            self.assertEqual(data['new_count'], 1)
            self.assertIn('失败', data['queries'][1]['status'])

    def test_total_failure_returns_nonzero_and_retains_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(search, 'fetch_json', side_effect=TimeoutError('timeout')), patch.object(search.time, 'sleep'):
                status = search.run(argparse.Namespace(output=directory, max_queries=1))
            self.assertEqual(status, 2)
            self.assertEqual(json.loads((Path(directory) / 'candidates.json').read_text())['items'], [])

    def test_duplicate_results_count_once(self):
        with tempfile.TemporaryDirectory() as directory:
            result = {'results': [{'id': 42, 'title': 'Same', 'authors': [], 'copyright': False}]}
            with patch.object(search, 'fetch_json', return_value=result), patch.object(search.time, 'sleep'):
                status = search.run(argparse.Namespace(output=directory, max_queries=2))
            data = json.loads((Path(directory) / 'candidates.json').read_text())
            self.assertEqual(status, 0)
            self.assertEqual(data['new_count'], 1)
            self.assertEqual(len(data['items']), 1)

    def test_download_rejects_html_and_incomplete_epubs(self):
        with self.assertRaises(zipfile.BadZipFile):
            download.validate_epub(b'<html>error response</html>')
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('mimetype', b'application/epub+zip')
        with self.assertRaises(ValueError):
            download.validate_epub(data.getvalue())
        with zipfile.ZipFile(data, 'a') as archive:
            archive.writestr('META-INF/container.xml', '<container/>')
        download.validate_epub(data.getvalue())


if __name__ == '__main__':
    unittest.main()
