import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch

from researchforge.gateway import make_server
from researchforge.store import Store
from researchforge.protocol import to_openai
from researchforge.results import collect_autosota


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.store=Store(self.tmp.name)
        self.store.configure({'max_calls':1,'max_tokens':5000,'max_seconds':60,'max_inflight':2,'category_tokens':{'planning':5000}})
        self.config={'upstream_key_env':'RF_TEST_REAL_KEY','upstream_base_url':'https://example.invalid/v1',
                     'categories':{'planning':{'model':'model','token_env':'RF_TEST_TOKEN'}}}
        self.environment=patch.dict(os.environ,{'RF_TEST_REAL_KEY':'private-upstream-value','RF_TEST_TOKEN':'x'*32});self.environment.start()
        self.upstream_calls=0
        self.server=make_server(self.store,self.config,0,transport=self.transport)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.environment.stop();self.tmp.cleanup()
    def transport(self,request,timeout):
        self.upstream_calls+=1
        return io.BytesIO(json.dumps({'id':'test','model':'model','choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'observed'}}],
                                     'usage':{'total_tokens':20,'prompt_tokens':15,'completion_tokens':5}}).encode())
    def send(self,path,body,token='x'*32):
        request=urllib.request.Request('http://127.0.0.1:'+str(self.server.server_port)+path,data=json.dumps(body).encode(),
                   headers={'x-api-key':token,'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=5) as response:return response.read()
    def test_real_http_and_budget_stop(self):
        body={'model':'model','messages':[{'role':'user','content':'test'}],'max_tokens':64}
        self.assertEqual(json.loads(self.send('/v1/messages',body))['content'][0]['text'],'observed')
        with self.assertRaises(urllib.error.HTTPError) as exc:self.send('/v1/messages',body)
        self.assertEqual(exc.exception.code,429);self.assertEqual(self.upstream_calls,1)
        self.assertEqual(self.store.snapshot()['mode'],'paused')
    def test_anthropic_sse_actual_http(self):
        body={'model':'model','messages':[{'role':'user','content':'test'}],'max_tokens':64,'stream':True}
        result=self.send('/v1/messages',body).decode()
        self.assertIn('event: message_start',result);self.assertIn('event: message_stop',result)
    def test_anthropic_sdk_beta_query(self):
        body={'model':'model','messages':[{'role':'user','content':'test'}],'max_tokens':64}
        self.assertEqual(json.loads(self.send('/v1/messages?beta=true',body))['content'][0]['text'],'observed')
        self.assertEqual(self.upstream_calls,1)
    def test_unauthorized_no_upstream(self):
        with self.assertRaises(urllib.error.HTTPError):self.send('/v1/messages',{},token='wrong')
        self.assertEqual(self.upstream_calls,0)
    def test_wrong_model_no_upstream(self):
        with self.assertRaises(urllib.error.HTTPError):self.send('/v1/messages',{'model':'other'})
        self.assertEqual(self.upstream_calls,0)
    def test_provider_timeout_pauses_without_retry(self):
        # Separate server with a deliberately failed upstream transport.
        self.server.shutdown();self.server.server_close();self.thread.join()
        def fail(request,timeout):
            self.upstream_calls+=1;raise TimeoutError('simulated')
        self.server=make_server(self.store,self.config,0,transport=fail)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        with self.assertRaises(urllib.error.HTTPError):self.send('/v1/messages',{'model':'model','messages':[],'max_tokens':64})
        self.assertEqual(self.upstream_calls,1);self.assertEqual(self.store.snapshot()['mode'],'paused')
        self.assertEqual(self.store.snapshot()['usage'][0]['state'],'unknown')


class ImportTests(unittest.TestCase):
    def test_import_not_official_score(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root=Path(directory);(root/'scores.jsonl').write_text('{"joint":69}\n','utf-8');(root/'master_prompt.md').write_text('fixture','utf-8')
            result=collect_autosota(root)
            self.assertFalse(result['official_score_verified']);self.assertFalse(result['automatic_promotion'])
            self.assertEqual(len(result['reported_scores']),1)
    def test_extended_thinking_not_silently_ignored(self):
        with self.assertRaises(ValueError):to_openai({'thinking':{'type':'enabled'},'messages':[]},'model')


if __name__=='__main__':unittest.main()
