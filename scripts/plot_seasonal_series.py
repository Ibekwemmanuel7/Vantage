"""Plot actual dated observations and quality; never interpolate cloud gaps."""
from datetime import datetime
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


if __name__=='__main__':
    root=ROOT/'outputs/africa/seasonal'
    pointer=json.loads((root/'latest.json').read_text())
    report=json.loads((root/pointer['directory']/pointer['manifest']).read_text())
    fig,axes=plt.subplots(2,1,figsize=(11,7.5),sharex=True,gridspec_kw={'height_ratios':[1.5,1]})
    fig.patch.set_facecolor('#fafaf5')
    colors={2023:'#44775a',2024:'#b75b37'}
    for year,color in colors.items():
        rows=[s for s in report['slots'] if s['year']==year and s['observation']]
        dates=[datetime.fromisoformat('2000'+s['acquired_at'][4:10]) for s in rows]
        good=[i for i,s in enumerate(rows) if s['observation']['features'] is not None]
        bad=[i for i,s in enumerate(rows) if s['observation']['features'] is None]
        axes[0].scatter([dates[i] for i in good],[rows[i]['observation']['features']['ndvi_b8a_median'] for i in good],
                        color=color,s=48,label=f'{year}: {len(good)}/{len(rows)} coverage-qualified observations',zorder=3)
        axes[0].scatter([dates[i] for i in bad],[.025]*len(bad),color=color,marker='x',s=36,
                        transform=axes[0].get_xaxis_transform(),zorder=3)
        axes[1].scatter(dates,[s['observation']['crop_usable_fraction'] for s in rows],color=color,s=42,label=str(year),zorder=3)
    fig.suptitle('Iganga research series · March–July 2023 and 2024',x=.09,y=.96,ha='left',fontsize=16)
    axes[0].set(ylabel='Median NDVI (B8A / red)',ylim=(-.05,1))
    axes[0].legend(loc='lower left',bbox_to_anchor=(0,1.02),frameon=False,ncol=2,fontsize=9)
    axes[0].text(.02,.08,'× Coverage withheld; these marks are not NDVI values',transform=axes[0].transAxes,fontsize=9,color='#62675f')
    axes[1].axhline(.6,color='#777777',linestyle='--',linewidth=1,label='60% development coverage threshold')
    axes[1].set(ylabel='Usable historical-cropland fraction',ylim=(-.04,1.05),xlabel='Acquisition month/day (years aligned for display)')
    axes[1].text(.98,.62,'60% development coverage threshold',transform=axes[1].get_yaxis_transform(),ha='right',fontsize=9,color='#62675f')
    axes[1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    for ax in axes:
        ax.set_facecolor('#ffffff');ax.grid(axis='y',alpha=.18)
        for side in ('top','right'):ax.spines[side].set_visible(False)
    fig.subplots_adjust(left=.09,right=.97,top=.83,bottom=.18,hspace=.24)
    fig.text(.09,.10,'Observed points only; no temporal interpolation. One selected acquisition per ten-day slot.',fontsize=10)
    fig.text(.09,.065,'WorldCover 2021 cropland is historical context; crop identity and planting stage remain unconfirmed.',fontsize=9,color='#62675f')
    fig.text(.09,.03,'No independent field labels or crop-damage validation. Dataset '+report['dataset_id'],fontsize=9,color='#62675f')
    out=root/'seasonal-observations.png';fig.savefig(out,dpi=160);plt.close(fig)
    print('Saved',out,'with matplotlib',importlib.metadata.version('matplotlib'))
