"""Self-contained HTML/SVG. Only escaped text and deterministic science enter markup."""
import json
from html import escape

SECTIONS = ["实验概况", "输入方式", "流动物理参数", "数值配置", "ShockPath 方法配置", "求解过程",
            "流场结果", "熵耗散路径分析", "宏观指标", "AI 科学解读", "科学边界", "Provenance / Evidence"]


def text(value):
    return escape(str(value), quote=True)


def table(rows, headings=("项目", "值")):
    return '<div class="table-wrap"><table><thead><tr>' + ''.join(f'<th>{text(h)}</th>' for h in headings) + '</tr></thead><tbody>' + ''.join(
        '<tr>' + ''.join(f'<td>{text(v)}</td>' for v in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def leaves(value, prefix=""):
    if isinstance(value, dict):
        return [row for k, v in value.items() for row in leaves(v, f"{prefix}.{k}" if prefix else k)]
    return [(prefix, json.dumps(value, ensure_ascii=False, allow_nan=False) if isinstance(value, (list, tuple)) else value)]


def items(values):
    return '<ul>' + ''.join(f'<li>{text(v)}</li>' for v in values) + '</ul>'


def color(value, low, high):
    ratio = (value - low) / (high - low) if high > low else .5
    a, b = (234, 242, 248), (24, 71, 109)
    return '#'+''.join(f'{round(x+(y-x)*ratio):02x}' for x, y in zip(a, b))


def heatmap(field):
    """Rectangles occupy actual cell geometry; y is inverted only for SVG display."""
    ny, nx = field.shape
    x0, x1 = field.extent_x
    y0, y1 = field.extent_y
    width, height = 640, 260
    dx, dy = width/nx, height/ny
    rects = ''.join(f'<rect x="{i%nx*dx:.6f}" y="{height-(i//nx+1)*dy:.6f}" width="{dx:.6f}" height="{dy:.6f}" fill="{color(v, field.minimum, field.maximum)}"/>' for i, v in enumerate(field.values))
    caption = f'{field.label} · {field.snapshot_id} · t={field.time!r} · {nx}×{ny} cell · {field.unit}; min={field.minimum!r}, max={field.maximum!r}; x=[{x0}, {x1}], y=[{y0}, {y1}]（下→上）'
    return f'<figure data-field="{text(field.field_id)}" data-snapshot="{text(field.snapshot_id)}" data-time="{field.time!r}"><svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{text(caption)}" viewBox="0 0 {width} {height}">{rects}</svg><figcaption>{text(caption)}<br>颜色：浅色=min，深色=max。源 SHA-256：{text(field.source_sha256)}<br>{text(field.definition)}</figcaption></figure>'


def entropy_chart(entropy):
    rows = entropy.rows
    # Include the known cumulative zero at the start; no invented snapshots.
    times = [float(rows[0]['time_start'])] + [float(r['time_end']) for r in rows]
    series = {key: [0.] + [float(r[key]) for r in rows] for key in ('E_bg', 'E_aa', 'E_at')}
    low, high = min(v for s in series.values() for v in s), max(v for s in series.values() for v in s)
    span = high-low or 1.
    tspan = times[-1]-times[0] or 1.
    colors = {'E_bg': '#597184', 'E_aa': '#246b97', 'E_at': '#b15136'}
    lines = ''.join(f'<polyline fill="none" stroke="{colors[key]}" stroke-width="2" points="' + ' '.join(f'{60+580*(t-times[0])/tspan:.6f},{270-240*(v-low)/span:.6f}' for t, v in zip(times, values)) + '"/>' for key, values in series.items())
    return '<figure><svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="真实接受步累计熵预算" viewBox="0 0 680 310"><path d="M60 20V270H640" stroke="#8999a6" fill="none"/>' + lines + f'<text x="4" y="25" font-size="11">{high:.5g}</text><text x="4" y="270" font-size="11">{low:.5g}</text><text x="60" y="295" font-size="12">{times[0]:.6g}</text><text x="590" y="295" font-size="12">{times[-1]:.6g}</text></svg><figcaption>累计标量 E：横轴 t（model time），纵轴 {text(entropy.unit)}。{len(rows)} 个真实接受步；E_bg 灰，E_aa 蓝，E_at 红。源 SHA-256：{text(entropy.source_sha256)}</figcaption></figure>'


def render(result, submission, fields, analysis, metadata, ai_context):
    c = result.config.normalized_config
    sections = []
    def section(body):
        index = len(sections)+1
        sections.append(f'<section id="section-{index}"><h2>{index}. {SECTIONS[index-1]}</h2>{body}</section>')
    section(table(leaves(result.identity.model_dump(mode='json'))) + table([
        ('config_hash', result.config.config_hash), ('result_hash', result.result_hash), ('report_id', metadata.report_id),
        ('report version', metadata.report_version), ('renderer SHA-256', metadata.renderer_sha256), ('生成时间（UTC）', metadata.created_at)]) + '<p>本次新建 V2 计算；论文模板匹配与科学复现结论分别核查。</p>')
    section(table(leaves(submission)) + '<p>输入方式属于提交记录；下列数字来自后端确认的归一化配置。</p>')
    section(table(leaves(c.physics.model_dump(mode='json'))))
    section(table(leaves({'grid': c.grid.model_dump(mode='json'), 'time': c.time.model_dump(mode='json'),
        'discretization': c.discretization.model_dump(mode='json'), 'output': c.output.model_dump(mode='json')})))
    section(table(leaves(c.method.model_dump(mode='json'))) + table([(d.field, d.expected, d.actual) for d in result.config.protocol_diff + result.config.output_diff], ('差异字段', '标准值', '本次值')) + items(result.config.warnings))
    section(table(leaves(result.runtime.model_dump(mode='json'))) + table([(s.snapshot_id, s.step, s.time) for s in result.snapshots], ('真实快照', '接受步', 't / model time')))
    section(''.join(heatmap(f) for f in fields) + table([(f.field_id, f.unit, f.definition) for f in result.fields], ('变量', '单位', '定义')) + '<p>图使用各变量自己的色标，展示终态真实 cell 值；没有插值生成中间帧。</p>')
    section(entropy_chart(result.entropy) + table(result.entropy.totals.items()) + table(leaves({k:v for k,v in result.entropy.model_dump(mode='json').items() if k not in ('rows', 'totals')})) + table(leaves({k:v for k,v in result.allocation.model_dump(mode='json').items() if k != 'arrays'})) + '<p>瞬时 Pi、全轨迹累计空间分配与累计标量 E 分别定义。累计 face 保留原生几何，报告不将其 reshape 为 cell 场。</p>')
    metric_rows = [(m.label, repr(m.value) if m.value is not None else '不可用', m.unit, m.time, m.availability, m.reason or '') for m in result.metrics]
    section(table(metric_rows, ('指标', '值', '单位', 't', '可用性', '原因')) + ''.join(f'<details><summary>{text(m.label)} 的定义</summary>{table(leaves(m.model_dump(mode="json")))}</details>' for m in result.metrics))
    if analysis is not None:
        content = analysis.interpretation
        facts = {f.evidence_id: f for f in analysis.evidence}
        claims = [content.summary, *content.key_findings, *content.observations]
        ai_html = table([('model', analysis.model), ('prompt version', analysis.prompt_version), ('AI content SHA-256', metadata.ai_content_sha256), ('解读时间（UTC）', analysis.created_at)])
        for claim in claims:
            ai_html += f'<article><p><strong>{text(claim.kind)}</strong> {text(claim.text)}</p>' + table([(ref, facts[ref].value, facts[ref].unit, facts[ref].availability) for ref in claim.evidence_refs], ('证据 ID', '确定性值', '单位', '可用性')) + '</article>'
        ai_html += '<h3>解读局限</h3>' + items(content.limitations) + '<h3>建议问题</h3>' + items(content.suggested_questions)
    else:
        ai_html = f'<p data-ai-status="UNAVAILABLE">AI 科学解读不可用：{text(metadata.ai_reason)}。配置、图表、数字与来源记录仍完整。</p>'
    section(ai_html)
    section(items(ai_context.limitations))
    section(table([(k,v) for k,v in leaves(result.provenance.model_dump(mode='json')) if not isinstance(v, (dict,list))]) + '<p>以下内容是相对来源记录；保存报告后仍可独立核查哈希，不依赖临时服务路径。</p>')
    data = {'run_id': result.identity.run_id, 'result_hash': result.result_hash,
        'report': metadata.model_dump(mode='json', exclude={'html_sha256','size_bytes'}), 'submission': submission, 'config': result.config.model_dump(mode='json'),
        'identity': result.identity.model_dump(mode='json'), 'runtime': result.runtime.model_dump(mode='json'),
        'entropy': result.entropy.model_dump(mode='json'), 'metrics': [m.model_dump(mode='json') for m in result.metrics],
        'snapshots': [s.model_dump(mode='json') for s in result.snapshots], 'provenance': result.provenance.model_dump(mode='json'),
        'charts': [{k:v for k,v in f.model_dump(mode='json').items() if k != 'values'} for f in fields],
        'ai_context': ai_context.model_dump(mode='json'), 'ai': analysis.model_dump(mode='json') if analysis else None}
    # This JSON is inert and readable offline; escape every HTML parser delimiter.
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
    style = 'body{font:16px/1.65 system-ui,sans-serif;color:#24384c;max-width:1000px;margin:auto;padding:32px 20px;background:#fff}h1{font-size:28px}h2{font-size:21px;border-bottom:1px solid #dce4eb;padding-bottom:8px}section{margin:36px 0}td,th{padding:8px;border-bottom:1px solid #dce4eb;text-align:left;vertical-align:top;overflow-wrap:anywhere}table{width:100%;border-collapse:collapse;font-size:13px}.table-wrap{overflow:auto}svg{width:100%;height:auto;display:block}figure{margin:24px 0}figcaption{font-size:12px;overflow-wrap:anywhere;color:#52687a}p,li,summary{overflow-wrap:anywhere}article{border-left:3px solid #246b97;padding-left:12px}a{color:#246b97}@media print{body{padding:0}section,figure{break-inside:avoid}}'
    nav = ' · '.join(f'<a href="#section-{i}">{i}. {text(title)}</a>' for i,title in enumerate(SECTIONS,1))
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:; base-uri \'none\'; form-action \'none\'"><title>ShockPath 数值实验报告</title><style>' + style + '</style></head><body><h1>ShockPath 数值实验报告</h1><nav>'+nav+'</nav>' + ''.join(sections) + '<script type="application/json" id="report-data">'+payload+'</script></body></html>'
