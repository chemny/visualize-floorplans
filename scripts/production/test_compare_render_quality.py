import tempfile,unittest
from pathlib import Path
try:
    import cv2,numpy as np
except ImportError:
    cv2=None

@unittest.skipIf(cv2 is None,'OpenCV is not installed')
class CompareRenders(unittest.TestCase):
    def folder(self,p,name,images):
        d=Path(p)/name;d.mkdir()
        for i,img in enumerate(images):cv2.imwrite(str(d/('frame-%06d.png'%i)),img)
        return d
    def test_identical_frames_score_perfectly_and_noise_scores_lower(self):
        from compare_render_quality import compare
        rng=np.random.default_rng(1);base=(np.linspace(0,255,200*300).reshape(200,300,1)*np.ones((1,1,3))).astype('uint8')
        noisy=np.clip(base.astype('int16')+rng.integers(-12,13,base.shape),0,255).astype('uint8')
        with tempfile.TemporaryDirectory() as p:
            ref=self.folder(p,'ref',[base,base]);same=self.folder(p,'same',[base,base]);bad=self.folder(p,'bad',[noisy,noisy])
            r=compare(ref,same);self.assertAlmostEqual(r['ssimMean'],1.0,places=6);self.assertGreaterEqual(r['psnrMean'],99)
            n=compare(ref,bad);self.assertLess(n['ssimMean'],r['ssimMean']);self.assertLess(n['psnrMean'],45)
            self.assertEqual(compare(ref,bad,frames=[1])['frames'],1)
    def test_only_shared_frames_count_and_size_mismatch_is_refused(self):
        from compare_render_quality import compare
        a=np.zeros((50,80,3),'uint8')
        with tempfile.TemporaryDirectory() as p:
            ref=self.folder(p,'ref',[a,a]);other=self.folder(p,'other',[a]);wrong=self.folder(p,'wrong',[np.zeros((40,80,3),'uint8')])
            self.assertEqual(compare(ref,other)['frames'],1)
            with self.assertRaises(ValueError):compare(ref,wrong)
    def test_zoom_sheet_is_written(self):
        from compare_render_quality import zoom_sheet
        a=np.full((600,800,3),90,'uint8')
        with tempfile.TemporaryDirectory() as p:
            f=Path(p)/'a.png';cv2.imwrite(str(f),a);out=zoom_sheet([f,f],Path(p)/'z.png');self.assertEqual(cv2.imread(out).shape,(480,1280,3))

class FastTemplate(unittest.TestCase):
    def test_the_fast_quality_template_is_valid(self):
        import json
        from blender_render_quality import validate
        t=json.loads((Path(__file__).resolve().parents[2]/'assets/h5/tour/blender-quality-fast-template.json').read_text())
        self.assertEqual(validate(t,32)['denoiser'],'OPTIX')
if __name__=='__main__':unittest.main()
