"""Plot the observed Lira pair and common-support difference, with evidence limits."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import rasterio


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    args=parser.parse_args()
    report=json.loads(args.report.read_text())
    archive_path=ROOT/report['plan']['archive_report']
    if sha(archive_path)!=report['plan']['archive_report_sha256']: raise ValueError('Optical archive differs')
    archive=json.loads(archive_path.read_text())
    images=[]
    for source in report['optical_sources']:
        row=next(r for r in archive['windows'] if r.get('processed_scene_id')==source['scene_id'])
        path=archive_path.parent/row['artifact']
        if sha(path)!=source['artifact_sha256']: raise ValueError('Optical input differs')
        with np.load(path,allow_pickle=False) as data: images.append(data['ndvi'].copy())
    raster=args.report.parent/'observed-ndvi-difference.tif'
    if sha(raster)!=report['optical_difference_sha256']: raise ValueError('Difference raster differs')
    with rasterio.open(raster) as source:
        delta=source.read(1); extent=[source.bounds.left/1000,source.bounds.right/1000,source.bounds.bottom/1000,source.bounds.top/1000]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,axes=plt.subplots(1,3,figsize=(15,6.5))
    fig.patch.set_facecolor('#f6f7f2')
    for ax in axes:
        ax.set_facecolor('#dcded7');ax.set_xlabel('UTM easting (km)');ax.set_ylabel('UTM northing (km)')
    for i,image in enumerate(images):
        handle=axes[i].imshow(image,extent=extent,cmap='YlGn',vmin=0,vmax=1,interpolation='nearest')
        axes[i].set_title(report['optical_sources'][i]['acquired_at'][:10]+' · observed NDVI',fontweight='bold')
        fig.colorbar(handle,ax=axes[i],shrink=.75,label='NDVI (display range 0–1)')
    cmap=LinearSegmentedColormap.from_list('difference',['#ae6519','#f1f0e8','#167c83'])
    handle=axes[2].imshow(delta,extent=extent,cmap=cmap,vmin=-.3,vmax=.3,interpolation='nearest')
    axes[2].set_title('2024 minus 2023 · common pixels',fontweight='bold')
    fig.colorbar(handle,ax=axes[2],shrink=.75,label='NDVI difference (display clipped at ±0.30)')
    fig.suptitle('Vantage | Lira study box: an exploratory interannual comparison',x=.04,ha='left',fontsize=17,fontweight='bold',color='#173f35')
    o=report['optical']
    fig.text(.04,.13,f"Common observed coverage: {o['common_fraction']:.1%} ({o['common_pixels']:,} pixels) · Median difference: {o['median_ndvi_difference']:+.4f}",fontsize=12)
    fig.text(.04,.085,'Gray: unavailable. Entire study box; no current crop mask or farm boundaries. One reference date is not a normal seasonal baseline.',fontsize=10)
    fig.text(.04,.05,'Rainfall reconstruction: '+report['rainfall']['status']+'. No drought attribution, yield-loss estimate or independent field validation.',fontsize=10)
    fig.subplots_adjust(left=.06,right=.97,top=.84,bottom=.24,wspace=.42)
    output=args.report.parent/'lira-observed-comparison.png'
    fig.savefig(output,dpi=150,facecolor=fig.get_facecolor());plt.close(fig)
    print(output)


if __name__=='__main__':main()
