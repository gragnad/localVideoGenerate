import copy
import importlib.util
from pathlib import Path
import unittest
from unittest import mock
import h3_research_resolution as resolution
import h3_direction_research as research

BASE = Path(__file__).resolve().parents[1] / 'trainAssets/research_01_04'
def module(name, file):
    spec = importlib.util.spec_from_file_location(name, BASE / 'scripts' / file)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
E = module('pilot_evaluate', 'evaluate.py')
P = module('pilot_submission', 'pilot_submission.py')

class GateTests(unittest.TestCase):
    def good(self, sid='B04_03'):
        c=E.load_criteria(); s=next(x for x in c['segments'] if x['segment_id']==sid)
        return c, dict(segment_id=sid, scores={k:4 for k in s['applicable']},
            timed_evidence={k:[dict(t=1,obs='visible evidence')] for k in s['applicable']},
            confidence=.8,critical_failures=[],measured_video={'duration_seconds':s['duration_seconds']},
            cut_measurements=[dict(target_seconds=t,actual_seconds=t,uncertainty_seconds=0,evidence='frame PTS') for t in s['cut_targets_seconds']],
            visual_checks={k:dict(passed=True,evidence='reviewed frames') for k in s['required_visual_checks']})
    def test_measured_candidate_can_pass(self):
        c,r=self.good(); self.assertTrue(E.judge(r,c)['pass'])
    def test_both_long_candidates_fail(self):
        c,r=self.good(); r['measured_video']['duration_seconds']=6.583333
        self.assertIn('duration_out_of_tolerance', E.judge(r,c)['failures'])
    def test_missing_cut_is_pending(self):
        c,r=self.good('B04_01');r['cut_measurements']=[]
        self.assertEqual('needs_measurement', E.judge(r,c)['status'])
    def test_early_cut_fails(self):
        c,r=self.good('B04_01');r['cut_measurements'][0]['actual_seconds']=2.2
        self.assertFalse(E.judge(r,c)['pass'])
    def test_wrong_grip_overrides_high_scores(self):
        c,r=self.good();r['visual_checks']['grip_target_correct']['passed']=False
        self.assertFalse(E.judge(r,c)['pass'])
    def test_burst_occlusion_required(self):
        c,r=self.good('B04_02');r['visual_checks']={}
        self.assertFalse(E.judge(r,c)['pass'])
    def test_bad_evidence_rejected(self):
        c,r=self.good();r['timed_evidence']['붙잡기']=[{'t':99,'obs':'outside clip'}]
        self.assertFalse(E.judge(r,c)['pass'])
    def test_graph_mismatch_and_unknown_links_rejected(self):
        graph={'1':{'class_type':'MiniMaxH3ReferenceToVideo','inputs':{'width':['2',0],'height':352}},'2':{'class_type':'easy int','inputs':{'value':608}}}
        self.assertEqual(608,resolution.verify_workflow_resolution(graph,608,352)['width'])
        graph['2']['inputs']['value']=832
        with self.assertRaises(ValueError):resolution.verify_workflow_resolution(graph,608,352)
        graph['2']['class_type']='UnknownMath'
        with self.assertRaises(ValueError):resolution.verify_workflow_resolution(graph,608,352)
    def test_old_request_rejected_before_compile(self):
        with mock.patch.object(P.h3_queue,'_compile_workflow') as compile:
            with self.assertRaises(ValueError):P.preflight({'width':832,'height':480})
            compile.assert_not_called()
    def test_resolution_blocks_runner_acceptance(self):
        r={'critical_failures':[],'confidence':1,'scores':{d:5 for d in research.DIMENSIONS},'duration_ok':True,'resolution_ok':False}
        self.assertFalse(research.passed(r,{'min_confidence':.75,'threshold':4}))

if __name__=='__main__':unittest.main()
