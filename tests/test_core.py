import concurrent.futures
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from researchforge.store import Store, Halt, sha
from researchforge.contracts import validate, command, handoff, inside
from researchforge.evaluation import compare, accepts
from researchforge.protocol import to_openai, to_anthropic, anthropic_events
from researchforge.worker import run_once, child_env
from researchforge.export import source_files, bundle


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root=Path(self.tmp.name).resolve()
        self.store=Store(self.root/'state')
        self.budget={'max_calls':10,'max_tokens':10000,'max_seconds':60,'max_inflight':2,'category_tokens':{'planning':1000,'optimization':8000,'evaluation':1000}}
        self.store.configure(self.budget)
        (self.root/'repo').mkdir();(self.root/'work').mkdir()
        (self.root/'repo/eval.py').write_text('print(1)','utf-8')
        self.spec={'backend':'autosota','objective':'Improve a general mechanism, not a case lookup',
                   'repo':'repo','workspace':'work','max_iterations':2,'max_seconds':5,
                   'metric':{'name':'joint','direction':'max','baseline':68,'protocol_sha256':'0'*64,'split':'development'},
                   'protected':{'repo/eval.py':sha(self.root/'repo/eval.py')},'outputs':['FINAL_SUMMARY.md']}
    def tearDown(self):self.tmp.cleanup()


class BudgetTests(Fixture):
    def test_frozen_budget(self):
        self.store.configure(self.budget)
        with self.assertRaises(Halt):self.store.configure({**self.budget,'max_calls':20})
    def test_known_usage_survives_restart(self):
        key=self.store.reserve('planning',{'messages':[]},800);self.store.settle(key,400)
        again=Store(self.root/'state')
        self.assertEqual(again.snapshot()['usage'][0]['tokens_or_reserved'],400)
    def test_category_budget_commits_pause(self):
        with self.assertRaises(Halt):self.store.reserve('planning',{},1001)
        self.assertEqual(Store(self.root/'state').snapshot()['mode'],'paused')
        with self.assertRaises(Halt):self.store.reserve('optimization',{},1)
    def test_unknown_usage_blocks_every_category(self):
        key=self.store.reserve('planning',{},500);self.store.uncertain(key,'timeout')
        self.assertEqual(self.store.snapshot()['usage'][0]['tokens_or_reserved'],500)
        with self.assertRaises(Halt):self.store.reserve('optimization',{},500)
    def test_inflight_backpressure_does_not_pause(self):
        self.store.reserve('optimization',{'id':1},50);self.store.reserve('optimization',{'id':2},50)
        with self.assertRaises(Halt):self.store.reserve('optimization',{'id':3},50)
        self.assertEqual(self.store.snapshot()['mode'],'active')
    def test_recovery_requires_gateway_stop(self):
        self.store.reserve('planning',{},50)
        with self.assertRaises(Halt):self.store.recover(lambda pid:False)
        self.assertEqual(self.store.snapshot()['usage'][0]['state'],'reserved')
        self.assertEqual(len(self.store.recover(lambda pid:False,gateway_stopped=True)),1)
        self.assertEqual(self.store.snapshot()['mode'],'paused')
    def test_overrun_is_not_hidden(self):
        key=self.store.reserve('planning',{},50);self.store.settle(key,60)
        self.assertEqual(self.store.snapshot()['mode'],'paused')
    def test_double_settlement_refused(self):
        key=self.store.reserve('planning',{},50);self.store.settle(key,40)
        with self.assertRaises(Halt):self.store.settle(key,20)


class JobTests(Fixture):
    def test_submit_is_idempotent(self):
        self.assertEqual(self.store.submit(self.spec),self.store.submit(self.spec))
        self.assertEqual(len(self.store.snapshot()['jobs']),1)
    def test_concurrent_claims_have_one_owner(self):
        self.store.submit(self.spec)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda x:self.store.claim(str(x)),range(4)))
        self.assertEqual(sum(result is not None for result in results),1)
    def test_no_automatic_crash_replay(self):
        self.store.submit(self.spec);job=self.store.claim('a')
        self.store.update_job(job['id'],'a',pid=12345)
        self.store.recover(lambda pid:False)
        self.assertEqual(self.store.snapshot()['jobs'][0]['state'],'needs_reconciliation')
        self.assertIsNone(self.store.claim('b'))
    def test_stale_worker_refused(self):
        self.store.submit(self.spec);job=self.store.claim('a')
        with self.assertRaises(Halt):self.store.update_job(job['id'],'b',state='awaiting_review')
    def test_real_child_receipt_and_artifact(self):
        script=self.root/'child.py';script.write_text("from pathlib import Path\nPath('FINAL_SUMMARY.md').write_text('offline fixture')\n",'utf-8')
        self.store.submit(self.spec)
        receipt=run_once(self.store,self.root,{'autosota':[sys.executable,str(script)]},poll_seconds=.01)
        self.assertEqual(receipt['state'],'awaiting_review')
        self.assertIn('FINAL_SUMMARY.md',receipt['outputs'])
    def test_success_exit_without_artifact_is_failure(self):
        script=self.root/'child.py';script.write_text('pass','utf-8');self.store.submit(self.spec)
        receipt=run_once(self.store,self.root,{'autosota':[sys.executable,str(script)]},poll_seconds=.01)
        self.assertEqual(receipt['state'],'needs_reconciliation')
    def test_evaluator_mutation_rejected(self):
        script=self.root/'child.py';script.write_text("from pathlib import Path\nPath('../repo/eval.py').write_text('fake')\nPath('FINAL_SUMMARY.md').write_text('done')\n",'utf-8')
        self.store.submit(self.spec)
        receipt=run_once(self.store,self.root,{'autosota':[sys.executable,str(script)]},poll_seconds=.01)
        self.assertEqual(receipt['state'],'needs_reconciliation')
    def test_timeout_stops_real_child(self):
        script=self.root/'child.py';script.write_text('import time\ntime.sleep(60)','utf-8')
        self.spec['max_seconds']=1;self.store.submit(self.spec)
        receipt=run_once(self.store,self.root,{'autosota':[sys.executable,str(script)]},poll_seconds=.01)
        self.assertEqual(receipt['state'],'needs_reconciliation')


class ContractTests(Fixture):
    def test_escape_refused(self):
        with self.assertRaises(ValueError):inside(self.root,'../outside')
    def test_protected_hash_checked(self):
        (self.root/'repo/eval.py').write_text('changed','utf-8')
        with self.assertRaises(ValueError):validate(self.spec,self.root)
    def test_target_frozen(self):
        handoff(self.spec,self.root)
        with self.assertRaises(ValueError):handoff({**self.spec,'objective':'other'},self.root)
    def test_cli_does_not_guess_workspace_flag(self):
        argv=command(self.spec,self.root,['autosota'],True)
        self.assertNotIn('--workspace',argv);self.assertIn('--dry-run',argv)
    def test_real_key_not_forwarded(self):
        old=os.environ.get('RF_UPSTREAM_API_KEY');os.environ['RF_UPSTREAM_API_KEY']='private-test-value'
        try:self.assertNotIn('RF_UPSTREAM_API_KEY',child_env())
        finally:
            if old is None:os.environ.pop('RF_UPSTREAM_API_KEY')
            else:os.environ['RF_UPSTREAM_API_KEY']=old


class EvaluationTests(unittest.TestCase):
    def test_paired_wins_and_regressions(self):
        cases=['a','b','c'];base={'denominator':3,'protocol_sha256':'x','rows':[{'case':c,'correct':c=='a'} for c in cases]}
        new={'denominator':3,'protocol_sha256':'x','rows':[{'case':c,'correct':c!='a'} for c in cases]}
        report=compare(base,new,'x',cases)
        self.assertEqual(report['net'],1);self.assertEqual(report['losses'],['a']);self.assertFalse(report['sota_claim'])
    def test_partial_run_cannot_be_full_score(self):
        report={'denominator':2,'protocol_sha256':'x','rows':[{'case':'a','correct':True}]}
        with self.assertRaises(ValueError):compare(report,report,'x',['a','b'])
    def test_guardrail_and_nan(self):
        goal={'primary':'joint','direction':'max','baseline':68,'guardrails':{'tokens':{'max':100}}}
        self.assertTrue(accepts({'joint':69,'tokens':90},goal))
        self.assertFalse(accepts({'joint':69,'tokens':101},goal))
        self.assertFalse(accepts({'joint':float('nan'),'tokens':90},goal))


class ProtocolTests(unittest.TestCase):
    def test_tool_result_order_and_identity(self):
        request=to_openai({'system':'rules','messages':[{'role':'assistant','content':[{'type':'tool_use','id':'abc','name':'read','input':{'path':'x'}}]},
                    {'role':'user','content':[{'type':'tool_result','tool_use_id':'abc','content':'observed'},{'type':'text','text':'continue'}]}]},'model')
        self.assertEqual([row['role'] for row in request['messages']],['system','assistant','tool','user'])
        self.assertEqual(request['messages'][2]['tool_call_id'],'abc')
    def test_unsupported_modalities_fail_closed(self):
        with self.assertRaises(ValueError):to_openai({'messages':[{'role':'user','content':[{'type':'image'}]}]},'model')
    def test_actual_usage_and_stream_end(self):
        response={'id':'id','model':'m','choices':[{'finish_reason':'tool_calls','message':{'tool_calls':[{'id':'t','function':{'name':'read','arguments':'{"path":"x"}'}}]}}],
                  'usage':{'prompt_tokens':10,'completion_tokens':3,'prompt_tokens_details':{'cached_tokens':4}}}
        converted=to_anthropic(response)
        self.assertEqual(converted['usage']['input_tokens'],6)
        self.assertEqual(converted['stop_reason'],'tool_use')
        events=list(anthropic_events(converted));self.assertEqual(events[-1][0],'message_stop')
        self.assertEqual(events[2][1]['delta']['type'],'input_json_delta')


class ExportTests(Fixture):
    def test_private_runtime_excluded(self):
        (self.root/'README.md').write_text('Public','utf-8');(self.root/'.runtime').mkdir();(self.root/'.runtime/private.json').write_text('secret','utf-8')
        self.assertEqual([p.name for p in source_files(self.root)],['README.md'])
    def test_credential_blocks_release(self):
        (self.root/'README.md').write_text('key: '+'sk-'+'z'*25,'utf-8')
        with self.assertRaises(ValueError):source_files(self.root)
    def test_immutable_source_bundle(self):
        (self.root/'README.md').write_text('Public','utf-8');out=self.root/'release.zip';result=bundle(self.root,out)
        self.assertEqual(result['files'],1)
        with self.assertRaises(ValueError):bundle(self.root,out)


if __name__=='__main__':unittest.main()
