"""Same-frame comparison of a candidate render setting against a reference render.

Reads PNG frames that exist in both folders and reports SSIM and PSNR per frame and in total. It is a
measurement, not an acceptance: look at the zoomed side-by-side too (`zoom_sheet`). Needs OpenCV and numpy.
"""
import json,math,sys
from pathlib import Path

def _gray(a):
    import cv2
    return cv2.cvtColor(a,cv2.COLOR_BGR2GRAY).astype('float64')

def ssim(a,b):
    import cv2,numpy as np
    x,y=_gray(a),_gray(b);c1,c2=6.5025,58.5225;k=(11,11)
    mu1=cv2.GaussianBlur(x,k,1.5);mu2=cv2.GaussianBlur(y,k,1.5)
    s1=cv2.GaussianBlur(x*x,k,1.5)-mu1**2;s2=cv2.GaussianBlur(y*y,k,1.5)-mu2**2;s12=cv2.GaussianBlur(x*y,k,1.5)-mu1*mu2
    return float(np.mean(((2*mu1*mu2+c1)*(2*s12+c2))/((mu1**2+mu2**2+c1)*(s1+s2+c2))))

def psnr(a,b):
    import numpy as np
    mse=float(np.mean((a.astype('float64')-b.astype('float64'))**2))
    return 99.0 if mse==0 else 10*math.log10(255**2/mse)

def compare(reference,candidate,frames=None):
    """Per-frame and mean SSIM and PSNR for the frame files present in both folders."""
    import cv2
    ref,cand=Path(reference),Path(candidate)
    names=sorted(f.name for f in ref.glob('frame-*.png') if (cand/f.name).is_file())
    if frames is not None:names=[n for n in names if int(n[6:12]) in set(frames)]
    if not names:raise ValueError('No frame exists in both folders')
    rows=[]
    for n in names:
        a=cv2.imread(str(ref/n));b=cv2.imread(str(cand/n))
        if a is None or b is None or a.shape!=b.shape:raise ValueError('Unreadable or differently sized frame: '+n)
        rows.append({'frame':n,'ssim':ssim(a,b),'psnr':psnr(a,b)})
    return {'frames':len(rows),'ssimMean':sum(r['ssim'] for r in rows)/len(rows),'ssimMinimum':min(r['ssim'] for r in rows),
            'psnrMean':sum(r['psnr'] for r in rows)/len(rows),'psnrMinimum':min(r['psnr'] for r in rows),'rows':rows,
            'note':'Measurement only. SSIM above about 0.99 and PSNR above about 40 dB are hard to tell apart by eye, but look at the zoomed side-by-side before adopting a setting.'}

def zoom_sheet(images,out,box=(0.45,0.35,320,240),scale=2):
    """Same region of several images side by side, enlarged without smoothing."""
    import cv2,numpy as np
    parts=[]
    for p in images:
        img=cv2.imread(str(p));h,w=img.shape[:2];x0,y0=int(w*box[0]),int(h*box[1])
        parts.append(cv2.resize(img[y0:y0+box[3],x0:x0+box[2]],None,fx=scale,fy=scale,interpolation=cv2.INTER_NEAREST))
    cv2.imwrite(str(out),np.hstack(parts));return str(out)

def main():
    import argparse
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--reference',required=True);a.add_argument('--candidate',required=True);a.add_argument('--frames',type=int,nargs='*')
    v=a.parse_args();r=compare(v.reference,v.candidate,v.frames);print(json.dumps({k:r[k] for k in r if k!='rows'},ensure_ascii=False))
if __name__=='__main__':main()
