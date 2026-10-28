"""Reusable sample comparison page. No video, no visual approval or full-tour claim."""
import json,shutil
from pathlib import Path
from tour_playback import ASSETS,prepare_renderer
from tour_pages import theme

def build(out,runtime,manifest):
    out=Path(out);target=out/'runtime'
    if target.exists():raise ValueError('Fresh comparison runtime required')
    target.mkdir(parents=True)
    for name in ('scene.json','geometry.bin','three.module.js','three.core.js','THREE-LICENSE.txt'):shutil.copy2(Path(runtime)/name,target/name)
    renderer=prepare_renderer((Path(runtime)/'renderer.html').read_text())
    renderer=renderer.replace('</style>','html,body{height:100%;background:#eae6de}body{display:flex;align-items:center;justify-content:center}canvas{width:100%!important;height:auto!important;max-height:100%;object-fit:contain}</style>',1)
    (target/'renderer.html').write_text(renderer)
    for name in ('rehearsal-player.js','motion-comparison.js'):shutil.copy2(ASSETS/name,out/name)
    (out/'index.html').write_text((ASSETS/'motion-comparison.html').read_text().replace('__STYLE__',theme()))
    (out/'comparison.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
