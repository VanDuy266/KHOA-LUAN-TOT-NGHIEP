import os,types,unittest
from unittest.mock import patch,Mock
from scripts.start_render import main
from webapp.server import app
class WindowsStartupTests(unittest.TestCase):
    def test_waitress_limit_matches_application(self):
        serve=Mock()
        with patch('scripts.start_render.sys.platform','win32'),patch.dict('sys.modules',{'waitress':types.SimpleNamespace(serve=serve)}),patch.dict(os.environ,{'PORT':'8501'}):
            main()
        self.assertEqual(serve.call_args.kwargs['port'],8501)
        self.assertEqual(serve.call_args.kwargs['max_request_body_size'],app.config['MAX_CONTENT_LENGTH'])
