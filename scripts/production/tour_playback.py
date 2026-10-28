"""Prepare interactive previews without changing frozen scene/mesh or capture API."""
import re
from pathlib import Path
ASSETS=Path(__file__).resolve().parents[2]/'assets/h5/tour'

def prepare_renderer(source):
    source=re.sub(r'/\* interactive-pose-renderer/1 \*/.*?/\* end-interactive-pose-renderer \*/\n','',source,flags=re.S)
    source=re.sub(r'/\* closing-fade-adapter/1 \*/.*?/\* end-closing-fade-adapter \*/\n','',source,flags=re.S)
    pattern=r'window\.renderFrame=async f=>\{.*?\n\};'
    match=re.search(pattern,source,re.S)
    if not match or 'camera.position.set' not in match[0] or 'renderer.render' not in match[0]:
        raise ValueError('Unknown renderer frame API; explicit adapter required')
    factory=(ASSETS/'interactive-camera.js').read_text().replace('export function','function',1)
    addition='/* interactive-pose-renderer/1 */\n'+factory+"\nconst poseRenderer=createPoseRenderer({renderer,camera,scene,settings,model:data.model});\nwindow.renderInteractiveFrame=f=>poseRenderer.draw(f);\n/* end-interactive-pose-renderer */\n"
    wrapper='/* closing-fade-adapter/1 */\nconst captureWithoutFade=window.renderFrame;\nwindow.renderFrame=async f=>{poseRenderer.applyFade(f);return captureWithoutFade(f);};\n/* end-closing-fade-adapter */\n'
    return source[:match.start()]+addition+source[match.start():match.end()]+ '\n'+wrapper+source[match.end():].lstrip('\n')

def preview_page(label):
    return (ASSETS/'camera-preview-template.html').read_text().replace('__STATUS__',label)
