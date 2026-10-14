from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import h3_direction_research as research
import h3_prompt_contract
from job_queue import atomic_write_json
from test_h3_prompt_contract import valid_spec


def plan():
    return {"source_analysis": "The camera follows a thrust.", "start_state": "Lua braces.",
        "end_state": "Lua faces right.", "hypothesis": "Show contact from the side.",
        "prompt": h3_prompt_contract.render_prompt(valid_spec())}


def review(score=4.5):
    return {"scores": {k: score for k in research.DIMENSIONS},
        "evidence": {k: [{"source_time": 1, "candidate_time": 1, "observation": "Contact is visible on both."}] for k in research.DIMENSIONS},
        "confidence": .9, "critical_failures": [], "revision_instruction": "Keep camera lower.",
        "actual_end_state": "Lua faces right.", "duration_ok": True, "resolution_ok": True}


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.mp4'
        self.source.write_bytes(b'video')
        self.picture = self.root / 'lua.png'
        self.picture.write_bytes(b'image')
        self.data = {"source_path": str(self.source), "start": 0, "end": 8,
            "boundaries": [0, 4, 8], "project_id": "dragon", "clip_id": "clip1",
            "adapter_id": "r2v", "character_mapping": "attacker=Lua, defender=jellyfish"}
        self.clip = {"generation_mode": "r2v", "video_prompt": plan()["prompt"],
            "references": [{"picture_index": 1, "role": "identity"}]}

    def create(self, **overrides):
        with mock.patch.object(research, 'probe', return_value=30), mock.patch.object(
            research.h3_prompt_projects, 'load_clip', return_value=self.clip), mock.patch.object(
            research.h3_prompt_projects, 'picture_path', return_value=self.picture):
            return research.create(self.root, {**self.data, **overrides})

    def write(self, state):
        atomic_write_json(research.directory(self.root, state['experiment_id']) / 'experiment.json', state)

    def test_create_has_no_generation_and_snapshots_references(self):
        state = self.create()
        self.assertEqual('draft', state['status'])
        self.assertEqual(2, len(state['segments']))
        self.assertEqual(0, state['generation_count'])
        self.picture.write_bytes(b'changed')
        self.assertEqual(b'image', Path(state['references'][0]['upload_path']).read_bytes())
        self.assertFalse((self.root / 'runtime/h3/jobs').exists())

    def test_invalid_boundaries_and_numbers(self):
        for overrides in ({'boundaries': [0, 5, 4, 8]}, {'boundaries': [1, 8]},
                          {'max_generations': float('nan')}, {'candidate_count': 2.5}, {'start': True}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.create(**overrides)

    def test_auto_windows_cover_source_without_short_tail(self):
        state = self.create(end=21, boundaries=None)
        self.assertEqual([7, 7, 7], [s['end']-s['start'] for s in state['segments']])
        self.assertEqual('provisional_equal_windows', state['boundary_method'])

    def test_reference_selection_preserves_requested_order(self):
        self.clip['references'].append({'picture_index': 2, 'role': 'background'})
        state = self.create(picture_indices=[2, 1])
        self.assertEqual(['background', 'identity'], [r['role'] for r in state['references']])
        self.assertEqual([1, 2], [r['picture_index'] for r in state['references']])

    def test_changed_source_blocks_resume(self):
        state = self.create()
        self.source.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, '변경'):
            research.control(self.root, state['experiment_id'], 'start')

    def test_draft_tick_does_not_call_model(self):
        state = self.create()
        caller = mock.Mock()
        research.tick(self.root, state['experiment_id'], call=caller)
        caller.assert_not_called()

    def test_plan_requires_real_reference_bindings(self):
        research.validate_plan(plan(), 4, 1)
        with self.assertRaisesRegex(ValueError, 'Picture'):
            research.validate_plan(plan(), 4, 2)
        wrong = plan()
        wrong['prompt'] = wrong['prompt'].replace('[Shot 1]', '[Shot 1] At 00:00.000,')
        with self.assertRaises(ValueError):
            research.validate_plan(wrong, 4, 1)

    def test_review_requires_finite_complete_timed_evidence(self):
        research.validate_review(review(), 4)
        for change in ('nan', 'missing', 'untimed', 'outside'):
            r = review()
            if change == 'nan': r['scores']['impact'] = float('nan')
            if change == 'missing': del r['scores']['camera']
            if change == 'untimed': r['evidence']['impact'] = []
            if change == 'outside': r['evidence']['impact'][0]['source_time'] = 500
            with self.subTest(change=change), self.assertRaises((ValueError, TypeError)):
                research.validate_review(r, 4)

    def test_critical_failure_and_timing_override_high_scores(self):
        state = self.create()
        r = review(5)
        self.assertTrue(research.passed(r, state['config']))
        r['critical_failures'] = ['missed contact']
        self.assertFalse(research.passed(r, state['config']))
        r['critical_failures'] = []
        r['duration_ok'] = False
        self.assertFalse(research.passed(r, state['config']))

    def ready(self):
        state = self.create()
        state['status'] = 'running'
        for segment in state['segments']:
            segment.update(status='ready', plan=plan())
        self.write(state)
        return state

    def test_generation_limit_prevents_submission(self):
        state = self.ready()
        state['config']['max_generations'] = 1
        self.write(state)
        enqueue = mock.Mock()
        result = research.tick(self.root, state['experiment_id'], enqueue_fn=enqueue)
        self.assertEqual('budget_reached', result['status'])
        enqueue.assert_not_called()

    def test_queue_is_local_and_round_is_immutable(self):
        state = self.ready()
        enqueue = mock.Mock(return_value={'candidate_set_id': 'set1', 'candidate_job_ids': ['j1', 'j2']})
        result = research.tick(self.root, state['experiment_id'], enqueue_fn=enqueue)
        payload = enqueue.call_args.args[1]
        self.assertEqual('local_generation', payload['queue_lane'])
        self.assertEqual('r2v', payload['generation_mode'])
        self.assertNotIn('source_clip_id', payload)
        self.assertEqual(2, result['generation_count'])
        self.assertEqual('rendering', result['segments'][0]['status'])
        result['segments'][0]['plan']['prompt'] = 'changed'
        self.assertEqual(plan()['prompt'], result['segments'][0]['rounds'][0]['prompt'])

    def test_real_h3_queue_bridge_in_temporary_root(self):
        state = self.ready()
        with mock.patch.object(research.h3_queue, '_compile_workflow', return_value=(
            {"1": {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {"width": 608, "height": 352}}}, [],
            {"generation_mode": "r2v", "workflow_settings": {}})):
            result = research.tick(self.root, state['experiment_id'])
        self.assertEqual('running', result['status'], result.get('last_error'))
        round_data = result['segments'][0]['rounds'][0]
        for job_id in round_data['job_ids']:
            job_root = self.root / 'runtime/h3/jobs' / job_id
            request = json.loads((job_root/'request.json').read_text())
            self.assertEqual('local_generation', request['queue_lane'])
            self.assertEqual('r2v', request['generation_mode'])
            self.assertEqual(4, request['duration_seconds'])
            self.assertTrue(Path(request['references'][0]['source_path']).is_file())
            self.assertEqual('queued', json.loads((job_root/'status.json').read_text())['status'])

    def test_submission_crash_persists_intent_and_prevents_duplicate(self):
        state = self.ready()
        enqueue = mock.Mock(side_effect=RuntimeError('lost connection'))
        result = research.tick(self.root, state['experiment_id'], enqueue_fn=enqueue)
        self.assertEqual('blocked', result['status'])
        self.assertTrue(result['queue_intent'])
        with self.assertRaisesRegex(ValueError, 'reconcile'):
            research.control(self.root, state['experiment_id'], 'resume')
        research.tick(self.root, state['experiment_id'], enqueue_fn=enqueue)
        self.assertEqual(1, enqueue.call_count)

    def test_reconcile_recovers_completed_submission(self):
        state = self.ready()
        marker = state['experiment_id'] + '_segment_0001_1'
        state['queue_intent'] = marker
        self.write(state)
        candidate = {'candidate_set_id': 's1', 'candidate_job_ids': ['j1', 'j2'],
            'project_test_set_id': marker, 'prompt': plan()['prompt']}
        atomic_write_json(self.root/'runtime/h3/candidate_sets/s1/candidate_set.json', candidate)
        for job_id in ['j1', 'j2']:
            atomic_write_json(self.root/f'runtime/h3/jobs/{job_id}/request.json', {'job_id': job_id, 'project_test_set_id': marker})
        result = research.reconcile(self.root, state['experiment_id'])
        self.assertEqual(2, result['generation_count'])
        self.assertEqual('rendering', result['segments'][0]['status'])
        self.assertNotIn('queue_intent', result)

    def test_pilot_then_continuous_auto_selection(self):
        state = self.ready()
        segment = state['segments'][0]
        segment['rounds'] = [{'reviews': {'j1': review()}, 'number': 1}]
        research.finish_round(state, segment)
        self.assertEqual('awaiting_acceptance', state['status'])
        self.write(state)
        result = research.control(self.root, state['experiment_id'], 'accept', {'segment_id': segment['id']})
        self.assertTrue(result['pilot_approved'])
        self.assertEqual('needs_revision', result['segments'][1]['status'])
        second = result['segments'][1]
        second['rounds'] = [{'reviews': {'j2': review()}, 'number': 1}]
        research.finish_round(result, second)
        self.assertEqual('auto_accepted', second['status'])
        self.assertEqual('awaiting_final_review', result['status'])
        self.write(result)
        with self.assertRaisesRegex(ValueError, '모든 구간'):
            research.assemble(self.root, state['experiment_id'])
        preview = self.root / 'preview.mp4'
        preview.write_bytes(b'preview')
        result['preview_path'] = str(preview)
        self.write(result)
        result = research.control(self.root, state['experiment_id'], 'accept_sequence', {'feedback': '전체 연출 연결 확인'})
        self.assertEqual('ready_to_assemble', result['status'])

    def test_stagnation_does_not_regenerate_forever(self):
        state = self.ready()
        segment = state['segments'][0]
        segment['rounds'] = [{'score': 2.0, 'reviews': {'j1': review(2)}} for _ in range(3)]
        research.finish_round(state, segment)
        self.assertEqual('stagnated', segment['status'])
        self.assertEqual('needs_attention', state['status'])

    def test_render_timeout_blocks_without_resubmitting(self):
        state = self.ready()
        segment = state['segments'][0]
        segment.update(status='rendering', rounds=[{'job_ids': ['missing'], 'reviews': {}, 'queued_at': 0}])
        self.write(state)
        enqueue = mock.Mock()
        result = research.tick(self.root, state['experiment_id'], enqueue_fn=enqueue)
        self.assertEqual('blocked', result['status'])
        self.assertIn('대기 한도', result['last_error'])
        enqueue.assert_not_called()

    def test_lock_rejects_concurrent_mutation(self):
        state = self.create()
        with research.locked(self.root, state['experiment_id']):
            with self.assertRaisesRegex(RuntimeError, '다른 단계'):
                research.control(self.root, state['experiment_id'], 'start')

    def test_model_event_parser_rejects_errors(self):
        output = json.dumps({'type':'text', 'part': {'text': '```json\n{"ok":true}\n```'}})
        self.assertEqual({'ok':True}, research.parse_model_output(output))
        with self.assertRaises(RuntimeError):
            research.parse_model_output(json.dumps({'type':'error'}))

    def test_model_budget_before_process(self):
        state = self.create()
        state['model_calls'] = state['config']['max_model_calls']
        with mock.patch.object(research.subprocess, 'run') as process, self.assertRaisesRegex(RuntimeError, '한도'):
            research.muse_call(research.directory(self.root, state['experiment_id']), state, 'analyze', {}, [])
        process.assert_not_called()

    def test_opencode_call_pins_model_and_denies_tools(self):
        state = self.create()
        response = json.dumps({'type':'text','part': {'text':'{"ok":true}'}})
        with mock.patch.object(research, 'opencode_binary', return_value='/opencode'), mock.patch.object(
            research.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, response, '')) as process:
            research.muse_call(research.directory(self.root, state['experiment_id']), state, 'test', {}, [])
        args = process.call_args.args[0]
        self.assertIn(research.MODEL, args)
        cfg = json.loads(process.call_args.kwargs['env']['OPENCODE_CONFIG_CONTENT'])
        self.assertEqual({'*':'deny'}, cfg['permission'])
        self.assertEqual(1, research.load(self.root, state['experiment_id'])['model_calls'])

    def test_reject_invalidates_only_automatic_successors(self):
        state = self.ready()
        first, second = state['segments']
        first.update(status='auto_accepted', accepted_job='j1')
        second.update(status='auto_accepted', accepted_job='j2')
        state['status'] = 'awaiting_final_review'
        state['preview_path'] = '/old/preview.mp4'
        self.write(state)
        result = research.control(self.root, state['experiment_id'], 'reject', {
            'segment_id': first['id'], 'feedback': '접촉점이 빗나감'})
        self.assertEqual('needs_revision', result['segments'][0]['status'])
        self.assertEqual('needs_boundary_review', result['segments'][1]['status'])
        self.assertNotIn('preview_path', result)

    def test_source_change_during_run_blocks_before_model(self):
        state = self.ready()
        self.source.write_bytes(b'new source')
        caller = mock.Mock()
        result = research.tick(self.root, state['experiment_id'], call=caller)
        self.assertEqual('blocked', result['status'])
        caller.assert_not_called()

    def test_summary_rejects_invented_evidence_and_caches_real_findings(self):
        state = self.ready()
        state['segments'][0]['rounds'] = [{'reviews': {'j1': review()}, 'prompt': plan()['prompt']}]
        self.write(state)
        finding = {'technique': '접촉 후 컷', 'when_to_use': '찌르기', 'prompt_pattern': 'Cut after contact.',
            'evidence_job_ids': ['invented'], 'limitations': '단일 후보 관찰'}
        caller = mock.Mock(return_value={'findings': [finding]})
        with self.assertRaisesRegex(ValueError, '실제 평가'):
            research.summarize(self.root, state['experiment_id'], call=caller)
        finding['evidence_job_ids'] = ['j1']
        output = research.summarize(self.root, state['experiment_id'], call=caller)
        self.assertIn('Cut after contact.', Path(output['path']).read_text())
        research.summarize(self.root, state['experiment_id'], call=caller)
        self.assertEqual(2, caller.call_count)

    def test_rendering_candidate_cannot_be_accepted_from_old_review(self):
        state = self.ready()
        state['segments'][0].update(status='rendering', rounds=[{'reviews': {'old': review()}}])
        self.write(state)
        with self.assertRaisesRegex(ValueError, '현재 평가'):
            research.control(self.root, state['experiment_id'], 'accept', {'segment_id': 'segment_0001', 'job_id': 'old'})

    def test_ids_cannot_escape_runtime(self):
        for value in ('../x', '/tmp/x', '', 'research_'+'a'*12+'/../../x'):
            with self.assertRaises(ValueError): research.directory(self.root, value)


@unittest.skipUnless(research.shutil.which('ffmpeg') and research.shutil.which('ffprobe'), 'ffmpeg needed')
class MediaTests(unittest.TestCase):
    def test_real_frame_extraction_and_probe(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            video = base/'pattern.mp4'
            research.command(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=96x64:rate=24',
                '-t','1','-c:v','libx264','-y',str(video)])
            self.assertAlmostEqual(1, research.probe(video), places=1)
            samples = research.frame_samples(video, 0, 1, base/'frames', 4)
            self.assertEqual([0,.25,.5,.75], [r['time'] for r in samples])
            self.assertTrue(all(Path(r['path']).stat().st_size > 0 for r in samples))

    def test_synthetic_end_to_end_queue_review_preview_and_assembly(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/'source.mp4'
            picture = root/'target.png'
            research.command(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=96x64:rate=24',
                '-t','8','-c:v','libx264','-y',str(source)])
            research.command(['ffmpeg','-v','error','-i',str(source),'-frames:v','1','-y',str(picture)])
            clip = {'generation_mode': 'r2v', 'video_prompt': plan()['prompt'],
                'references': [{'picture_index': 1, 'role': 'identity'}]}
            with mock.patch.object(research.h3_prompt_projects, 'load_clip', return_value=clip), mock.patch.object(
                research.h3_prompt_projects, 'picture_path', return_value=picture):
                state = research.create(root, {'source_path': str(source), 'project_id': 'p', 'clip_id': 'c',
                    'adapter_id': 'a', 'boundaries': [0,4,8], 'character_mapping': 'test subject = Lua',
                    'candidate_count': 1, 'sample_fps': 1, 'width': 608, 'height': 352})
            eid = state['experiment_id']
            research.control(root, eid, 'start')
            def model(base, state, task, packet, media):
                self.assertTrue(media)
                if task == 'compare':
                    kinds = {m['kind'] for m in media}
                    self.assertTrue({'source','candidate','target_identity'} <= kinds)
                    return review()
                return plan()
            with mock.patch.object(research.h3_queue, '_compile_workflow', return_value=(
                {'1': {'class_type':'MiniMaxH3ReferenceToVideo','inputs':{'width':608,'height':352}}}, [], {'generation_mode':'r2v','workflow_settings':{}})):
                for _ in range(24):
                    state = research.tick(root, eid, call=model)
                    self.assertNotEqual('blocked', state['status'], state.get('last_error'))
                    for segment in state['segments']:
                        if segment['status'] != 'rendering': continue
                        for job in research.inspect_jobs(root, segment['rounds'][-1]):
                            if job['status'] != 'queued': continue
                            output = root/'runtime/h3/outputs'/f"{job['job_id']}.mp4"
                            output.parent.mkdir(parents=True, exist_ok=True)
                            research.command(['ffmpeg','-v','error','-i',str(source),'-t','4','-an','-vf','scale=608:352','-c:v','libx264','-y',str(output)])
                            atomic_write_json(root/'runtime/h3/jobs'/job['job_id']/'status.json',
                                {'status':'completed','local_video_path':str(output)})
                    if state['status'] == 'awaiting_acceptance':
                        research.control(root,eid,'accept',{'segment_id':'segment_0001'})
                    if state['status'] == 'awaiting_final_review': break
                self.assertEqual('awaiting_final_review', state['status'])
            preview = research.assemble(root,eid,preview=True)
            self.assertAlmostEqual(8,preview['preview_duration'],places=1)
            research.control(root,eid,'accept_sequence',{'feedback':'합성 테스트 연속성 확인'})
            result = research.assemble(root,eid)
            self.assertEqual('complete',result['status'])
            self.assertAlmostEqual(8,result['assembly_duration'],places=1)
            report = research.export_report(root,eid)
            self.assertIn('사용자 확정',Path(report['path']).read_text())


if __name__ == '__main__':
    unittest.main()
