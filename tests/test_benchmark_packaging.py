import gzip,tempfile,unittest
from pathlib import Path
from webapp.benchmark_sources import source_hash,source_text
class BenchmarkPackagingTests(unittest.TestCase):
    def test_gzip_and_line_endings_do_not_change_source_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'timings.csv';p.write_bytes(b'model,time\r\nRF,1\r\n')
            original=source_hash(p)
            p.unlink();p.with_suffix('.csv.gz').write_bytes(gzip.compress(b'model,time\nRF,1\n'))
            self.assertEqual(source_hash(p),original)
            self.assertEqual(source_text(p),'model,time\nRF,1\n')
    def test_changed_value_is_still_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'timings.csv';p.write_text('model,time\nRF,1\n');a=source_hash(p)
            p.write_text('model,time\nRF,2\n');self.assertNotEqual(a,source_hash(p))

    def test_builder_works_with_gzip_only_repository(self):
        import json
        from unittest.mock import patch
        from scripts import build_ui_benchmarks
        original=build_ui_benchmarks.ROOT
        expected=json.loads((original/'reports/thesis_audit/ui_benchmarks.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in expected['source_hashes']:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
                content=source_text(original/name).encode('utf-8')
                if name.endswith('.csv'):target.with_suffix('.csv.gz').write_bytes(gzip.compress(content))
                else:target.write_bytes(content)
            with patch.object(build_ui_benchmarks,'ROOT',root):build_ui_benchmarks.main()
            actual=json.loads((root/'reports/thesis_audit/ui_benchmarks.json').read_text(encoding='utf-8'))
            self.assertEqual(expected['source_hashes'],actual['source_hashes'])
            self.assertEqual(expected['SDU']['rows'],actual['SDU']['rows'])
            self.assertEqual(expected['BMS']['rows'],actual['BMS']['rows'])
