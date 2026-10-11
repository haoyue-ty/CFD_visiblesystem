"""Independent PDF opening, A4/text/layout and figure rendering in analysis-env."""
import argparse
import json
from pathlib import Path
import re

import fitz


def validate(root, output):
    output.mkdir(parents=True,exist_ok=True)
    pdf=root/'exports/reports/report.pdf'
    result=json.loads((root/'exports/raw/scientific_result.json').read_text(encoding='utf-8'))
    doc=fitz.open(pdf)
    assert doc.is_pdf and len(doc)>0
    texts=[]
    outside=[]
    rendered=[]
    for i,page in enumerate(doc):
        assert abs(page.rect.width-595.276)<1 and abs(page.rect.height-841.89)<1
        text=page.get_text()
        texts.append(text)
        for block in page.get_text('blocks'):
            x0,y0,x1,y1=block[:4]
            if x0 < -1 or y0 < -1 or x1 > page.rect.width+1 or y1 > page.rect.height+1:
                outside.append({'page':i+1,'bbox':[x0,y0,x1,y1]})
        # Render actual report figures and the first page for visual review.
        if i==0 or ('Density' in text and len(page.get_drawings())>50) or '累计标量 E' in text:
            name=f'page-{i+1:02d}.png'
            page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(output/name)
            rendered.append(name)
    text=''.join(texts)
    compact=re.sub(r'\s+','',text)
    assert result['identity']['run_id'] in compact
    assert result['result_hash'] in compact
    for word in ('实验概况','数值配置','流场结果','熵耗散路径分析','宏观指标','科学边界','Provenance'):
        assert word in compact,word
    assert all(name in text for name in ('Density','Pressure','Mach'))
    assert 'grid.nx' in compact and 'grid.ny' in compact
    assert 'E_bg' in text and 'E_aa' in text and 'E_at' in text
    assert not outside,outside
    assert len(rendered)>=3
    assert len(re.findall(r'[\u4e00-\u9fff]',text))>100
    summary={'status':'PASS','file':str(pdf),'bytes':pdf.stat().st_size,'pages':len(doc),'page_format':'A4',
             'run_id':result['identity']['run_id'],'chinese_text':'PASS','result_hash_match':True,
             'text_blocks_outside_page':outside,'rendered_pages':rendered,'renderer_validation':'PyMuPDF opened every page'}
    (output/'pdf-acceptance.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    doc.close()
    print(f"PDF ACCEPTANCE PASS: {result['identity']['run_id']}, {summary['pages']} A4 pages, Chinese text and scientific identity match, figures rendered")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    validate(args.run_dir,args.output)


if __name__=='__main__':main()
