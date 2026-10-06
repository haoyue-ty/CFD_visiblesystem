"""Versioned report artifacts separate from scientific identity and AI availability."""
from pathlib import Path

from backend.ai.analysis import ScientificAIService, digest
from backend.ai.context_builder import build_context
from backend.models.v2.experiment import ValidateExperimentRequest
from backend.models.v2.report import ReportMetadata
from backend.models.v2.result import RunFieldQuery
from backend.services.v2.experiments import ExperimentError, validate_experiment
from backend.services.v2.results import ScientificResultService
from backend.services.v2.report_renderer import render
from backend.solver_runtime.artifacts import target, write_json, sha256, utc_now
from backend.solver_runtime.run_store import file_lock

REPORT_VERSION = 'case8.html.p6.1'


class ReportService:
    def __init__(self, store, client):
        self.store, self.client = store, client
        self.science = ScientificResultService(store)

    def inputs(self, run_id):
        result = self.science.result(run_id)
        root = self.store.directory(run_id)
        try:
            request = ValidateExperimentRequest.model_validate_json(target(root, 'request.json').read_text(encoding='utf-8'))
            if validate_experiment(request).config_hash != result.config.config_hash:
                raise ValueError('Submission drift')
        except (ValueError, OSError, ExperimentError):
            raise ExperimentError('RUN_OUTPUT_INVALID', '提交配置未通过校验。', 500) from None
        analysis, reason = None, '尚无经过校验的同版本解读；可在结果页生成解读后更新报告'
        try:
            analysis = ScientificAIService(self.store, self.client).cached_interpretation(run_id)
        except ExperimentError as error:
            if error.code != 'AI_CACHE_INVALID':
                raise
            reason = 'AI 缓存未通过科学证据校验，解读未纳入报告'
        renderer_hash = digest([sha256(Path(__file__)), sha256(Path(__file__).with_name('report_renderer.py'))])
        context = build_context(self.store, run_id)
        context_hash = digest(context.model_dump(mode='json'))
        ai_hash = digest(analysis.model_dump(mode='json')) if analysis else None
        submission = request.submission.model_dump(mode='json')
        report_id = digest([result.result_hash, REPORT_VERSION, renderer_hash, context_hash, digest(submission), ai_hash, reason if not analysis else None])
        meta = ReportMetadata(run_id=run_id, status='NOT_GENERATED', result_hash=result.result_hash,
            report_version=REPORT_VERSION, renderer_sha256=renderer_hash, scientific_context_hash=context_hash,
            ai_status='AVAILABLE' if analysis else 'UNAVAILABLE',
            ai_reason=None if analysis else reason, ai_model=analysis.model if analysis else None,
            ai_prompt_version=analysis.prompt_version if analysis else None, ai_content_sha256=ai_hash)
        return result, submission, analysis, meta, report_id, context

    def stored(self, run_id, expected, report_id):
        root = self.store.directory(run_id)
        pointer = target(root, 'report/current.json')
        if not pointer.exists():
            return expected
        try:
            metadata = ReportMetadata.model_validate_json(pointer.read_text(encoding='utf-8'))
            if metadata.run_id != run_id or metadata.result_hash != expected.result_hash:
                raise ValueError('Identity drift')
            if metadata.report_id != report_id:
                return expected.model_copy(update={'status':'STALE'})
            for key in ('report_version','renderer_sha256','scientific_context_hash','ai_status','ai_reason','ai_model','ai_prompt_version','ai_content_sha256'):
                if getattr(metadata,key) != getattr(expected,key):
                    raise ValueError('Metadata drift')
            html = target(root, f'report/{report_id}.html')
            if metadata.status != 'READY' or sha256(html) != metadata.html_sha256 or html.stat().st_size != metadata.size_bytes:
                raise ValueError('HTML drift')
            return metadata
        except (ValueError, OSError):
            raise ExperimentError('REPORT_OUTPUT_INVALID', '报告文件未通过身份或哈希校验。', 500) from None

    def status(self, run_id):
        _, _, _, meta, key, _ = self.inputs(run_id)
        return self.stored(run_id, meta, key)

    def generate(self, run_id):
        record = self.store.get(run_id)
        if record.status != 'COMPLETED':
            raise ExperimentError('RUN_RESULT_NOT_READY', '运行尚未成功完成，科学结果不可用。', 409)
        root = self.store.directory(run_id)
        try:
            with file_lock(target(root, 'report/generate.lock'), blocking=False):
                result, submission, analysis, expected, key, context = self.inputs(run_id)
                metadata = self.stored(run_id, expected, key)
                if metadata.status == 'READY':
                    return metadata
                if not result.snapshots:
                    raise ExperimentError('RUN_OUTPUT_INVALID', '完成结果缺少真实快照。', 500)
                snapshot = result.snapshots[-1]
                fields = [self.science.field(RunFieldQuery(run_id=run_id, snapshot_id=snapshot.snapshot_id, field=name))
                          for name in ('density','pressure','mach')]
                metadata = expected.model_copy(update={'status':'READY', 'report_id':key, 'created_at':utc_now(),
                    'html_url':f'/api/v2/reports/{run_id}/html'})
                html = render(result, submission, fields, analysis, metadata, context)
                path = target(root, f'report/{key}.html')
                temporary = target(root, f'report/{key}.html.tmp')
                temporary.write_text(html, encoding='utf-8', newline='\n')
                temporary.replace(path)
                metadata = metadata.model_copy(update={'html_sha256':sha256(path), 'size_bytes':path.stat().st_size})
                write_json(root, f'report/{key}.json', metadata.model_dump(mode='json'))
                write_json(root, 'report/current.json', metadata.model_dump(mode='json'))
                return metadata
        except RuntimeError:
            raise ExperimentError('REPORT_BUSY', '该 Run 的报告正在生成，请稍后重试。', 429, retryable=True) from None

    def html(self, run_id):
        metadata = self.status(run_id)
        if metadata.status != 'READY':
            raise ExperimentError('REPORT_NOT_READY', '报告尚未生成或版本已变化，请生成报告。', 409)
        return target(self.store.directory(run_id), f'report/{metadata.report_id}.html').read_text(encoding='utf-8')
