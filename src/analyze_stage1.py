"""ERA5 comparison to Madden: harmonic spectra plus unselected EOF diagnostics.

Approximate pointwise reference bounds are exploratory, not a calibrated
familywise detection test. No automated claim of replication is made.
"""
import argparse
import json
import os
from pathlib import Path
import numpy as np
import xarray as xr
from scipy import signal, stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from n2tools import RADIUS, deseason

MODES=[(1,2,5.,4.85),(1,3,10.,9.91),(1,4,16.,18.39),(2,3,4.,3.84),(3,3,2.,2.30)]


def segments(time, values, season, days):
    months=xr.DataArray(time,dims='time').dt.month.values
    mask=np.ones(len(time),dtype=bool) if season=='ALL' else np.isin(months,{'DJF':[12,1,2],'JJA':[6,7,8]}[season])
    nseg=int(days*4)
    window=signal.windows.hann(nseg,sym=False)
    spectra=[]
    for start in range(0,len(values)-nseg+1,nseg//2):
        end=start+nseg
        if not mask[start:end].all():
            continue
        if not np.all(np.diff(time[start:end])==np.timedelta64(6,'h')):
            continue
        x=values[start:end]
        if not np.isfinite(x).all():
            raise ValueError('Nonfinite coefficient')
        f,p=signal.periodogram(x,fs=4,window=window,detrend=False,return_onesided=False,scaling='density')
        spectra.append(p)
    if not spectra:
        raise ValueError(f'No complete {days}-day {season} segments')
    # Conservative bound: maximum adjacent 50%-overlap correlation.
    rho=np.dot(window[:nseg//2],window[nseg//2:])/np.dot(window,window)
    dof=2*len(spectra)/(1+2*rho*rho)
    return f,np.mean(spectra,axis=0),dof,len(spectra)


def background(f,p):
    result=np.full_like(p,np.nan)
    for i,frequency in enumerate(f):
        if frequency==0:
            continue
        neighbors=(np.sign(f)==np.sign(frequency))&(np.abs(f)>=.75*abs(frequency))&(np.abs(f)<=1.25*abs(frequency))
        neighbors[i]=False
        if neighbors.sum()<3:
            available=np.flatnonzero(np.sign(f)==np.sign(frequency))
            available=available[available!=i]
            neighbors=np.zeros(len(f),dtype=bool)
            neighbors[available[np.argsort(abs(f[available]-frequency))[:5]]]=True
        result[i]=np.median(p[neighbors])
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=Path('data/stage1'))
    parser.add_argument('--out',type=Path,default=Path('results'))
    args=parser.parse_args()
    files=sorted(args.input.glob('coeffs_[0-9][0-9][0-9][0-9].nc'))
    expected=[f'coeffs_{y}.nc' for y in range(1979,2023)]
    if [f.name for f in files]!=expected:
        raise ValueError('Full analysis requires all 44 years, 1979–2022')
    ds=xr.open_mfdataset(files,combine='by_coords').load()
    time=ds.time.values
    if not np.all(np.diff(time)==np.timedelta64(6,'h')):
        raise ValueError('Gap or duplicate timestamps')
    args.out.mkdir(exist_ok=True,parents=True)
    z=ds.zeta_real+1j*ds.zeta_imag
    n=ds.n.values
    scale=np.zeros(len(n));scale[1:]=-RADIUS**2/(n[1:]*(n[1:]+1))
    psi=z*xr.DataArray(scale,dims='n',coords={'n':n})
    rows=[]
    for level in [300,500]:
        for season in ['ALL','DJF','JJA']:
            days=128 if season=='ALL' else 64
            fig,axs=plt.subplots(3,2,figsize=(11,11),constrained_layout=True)
            for ax,(m,n,target,theory) in zip(axs.flat,MODES):
                values=deseason(time,psi.sel(level=level,n=n,m=m).values)
                f,p,dof,k=segments(time,values,season,days)
                bg=background(f,p)
                threshold=bg*stats.chi2.ppf(.95,dof)/dof
                for sign,label,color in [(1,'Westward','#1769aa'),(-1,'Eastward','#b95135')]:
                    pick=(sign*f>0)&(abs(f)>=1/40)&(abs(f)<=1/1.5)
                    order=np.argsort(1/abs(f[pick]));idx=np.flatnonzero(pick)[order]
                    ax.plot(1/abs(f[idx]),p[idx],label=label,color=color)
                    ax.plot(1/abs(f[idx]),threshold[idx],ls=':',alpha=.7,color=color)
                ax.axvline(theory,color='black',ls='--',lw=.8,label='Kasahara DJF winds')
                rh=n*(n+1)/(2*m)*86164.0905/86400
                ax.axvline(rh,color='gray',ls='-.',lw=.8,label='Resting nondivergent RH')
                ax.set(xlim=(1.5,40),yscale='log',xlabel='Period (days)',ylabel='PSD (m⁴ s⁻² / cycles day⁻¹)',title=f'(m,n)=({m},{n})')
                lo,hi=(14,20) if (m,n)==(1,4) else (.9*target,1.1*target)
                band=(f>=1/hi)&(f<=1/lo)
                candidates=np.flatnonzero(band)
                peak=candidates[np.argmax(p[band])]
                east=np.argmin(abs(f+f[peak]))
                rows.append({'level':level,'season':season,'m':m,'n':n,'expected_days':target,'theory_djf_days':theory,'peak_days':float(1/f[peak]),'peak_background':float(p[peak]/bg[peak]),'west_east':float(p[peak]/p[east]),'above_pointwise_reference':bool(p[peak]>threshold[peak]),'segments':k,'effective_dof':float(dof),'window_days':days})
                np.savez_compressed(args.out/f'spectrum_{level}_{season}_{m}_{n}.npz',frequency_cpd=f,power=p,background=bg,pointwise_reference=threshold,dof=dof)
            axs.flat[-1].axis('off')
            axs.flat[0].legend(fontsize=7)
            fig.suptitle(f'ERA5 {level} hPa · {season} · {days}-day Hann windows\nDotted: approximate pointwise 95% background reference; not corrected for peak search')
            filename='stage1_spectra.png' if (level,season)==(300,'ALL') else f'stage1_spectra_{level}_{season}.png'
            fig.savefig(args.out/filename,dpi=170);plt.close(fig)
    # Save all EOF pairs rather than hand-picking pairs to favor expected periods.
    eof_summary=[]
    for m in range(1,5):
        a=psi.sel(level=300,m=m,n=slice(m,m+5)).values
        a=deseason(time,a)
        X=np.stack([a.real,-a.imag],axis=-1).reshape(len(time),12)
        covariance=X.T@X/(len(X)-1)
        ev,V=np.linalg.eigh(covariance);order=np.argsort(ev)[::-1];ev,V=ev[order],V[:,order]
        pc=X@V
        coherence=[];phase=[];pairs=[]
        for i in range(12):
            for j in range(i+1,12):
                f,coh=signal.coherence(pc[:,i],pc[:,j],fs=4,window='hann',nperseg=512,noverlap=256,detrend=False)
                _,cross=signal.csd(pc[:,i],pc[:,j],fs=4,window='hann',nperseg=512,noverlap=256,detrend=False)
                coherence.append(coh);phase.append(np.angle(cross));pairs.append([i+1,j+1])
        np.savez_compressed(args.out/f'eof_m{m}_300.npz',degrees=np.arange(m,m+6),eigenvectors=V,variance_fraction=ev/ev.sum(),pairs=pairs,frequency_cpd=f,coherence_squared=coherence,cross_phase_radians=phase)
        eof_summary.append({'m':m,'variance_fraction':(ev/ev.sum()).tolist()})
    months=ds.time.dt.month.values
    djf=np.isin(months,[12,1,2])
    omega=float((np.sqrt(3)/2*z.sel(level=300,n=1,m=0).real.values[djf]).mean())
    z20=[float(z.sel(level=300,n=2,m=0).real.values[months==month].mean()) for month in range(1,13)]
    plt.figure(figsize=(7,4));plt.plot(np.arange(1,13),z20,'o-');plt.xlabel('Month');plt.ylabel('Mean ζ₂⁰ (s⁻¹)');plt.title('300 hPa annual climatology');plt.tight_layout();plt.savefig(args.out/'zeta20_annual_cycle.png',dpi=150);plt.close()
    checks=json.loads((args.out/'data_checks.json').read_text())
    detail=json.loads((args.out/'resolution_detail.json').read_text())
    summary={'numerical_checks':checks,'resolution_max_individual_target_difference':detail['max_madden_mode_relative'],'status':'REVIEW_REQUIRED','job_id':os.environ.get('SLURM_JOB_ID'),'years':[1979,2022],'samples':len(time),'omega_djf_300':omega,'orientation_positive_djf':omega>0,'zeta20_monthly':z20,'spectra':rows,'eof':eof_summary}
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    lines=['# Stage 1 — ERA5 comparison to Madden (2007)','','Status: **REVIEW REQUIRED**. No Stage 2 computation is enabled.','',f'Analysis job: {summary["job_id"]}. {len(time)} six-hourly samples, 1979–2022.',f'DJF 300 hPa superrotation ω = {omega:.6g} s⁻¹; expected-positive check: {omega>0}.','','## Primary 300 hPa, all-season spectrum','','| (m,n) | Expected (d) | Peak in target band (d) | Peak/background | West/east at peak | Above pointwise reference |','|---|---:|---:|---:|---:|---|']
    for r in rows:
        if (r['level'],r['season'])==(300,'ALL'):
            lines.append(f"| ({r['m']},{r['n']}) | {r['expected_days']:g} | {r['peak_days']:.3f} | {r['peak_background']:.3f} | {r['west_east']:.3f} | {r['above_pointwise_reference']} |")
    lines+=['','## Numerical checks','',f'Synthetic suite: see synthetic-tests.txt. Energy closure passed: {checks["energy_pass"]}; maximum relative error {max(r["energy_closure_relative"] for r in checks["checks"]):.3g}.',f'Whole-field resolution L2 <1%: {checks["resolution_l2_within_one_percent"]}. All individual degrees <1%: {checks["resolution_all_degrees_within_one_percent"]}. The strict resolution criterion is therefore NOT satisfied.',f'Maximum individual target-mode resolution difference over sampled dates: {detail["max_madden_mode_relative"]:.2%}. Small-amplitude modes amplify relative error. See resolution_detail.json and resolution_year.json for absolute errors and the full-year sensitivity check.','','![Primary spectra](stage1_spectra.png)','','## Seasonal and height comparison','','| (m,n) | 300 DJF peak/background | 300 JJA | 500 ALL |','|---|---:|---:|---:|']
    for m,n,_,_ in MODES:
        values=[next(r['peak_background'] for r in rows if (r['m'],r['n'],r['level'],r['season'])==(m,n,lev,season)) for lev,season in [(300,'DJF'),(300,'JJA'),(500,'ALL')]]
        lines.append(f'| ({m},{n}) | '+ ' | '.join(f'{v:.3f}' for v in values)+' |')
    lines+=['','Seasonal comparisons use 64-day windows entirely within each season; all-season windows are 128 days. Their resolutions differ. Full values and eastward comparisons are in summary.json.','','## Interpretation limits','','These are target-band maxima, not automatically identified independent wave detections. The fitted running-median background and approximate χ² bounds are exploratory pointwise references: background uncertainty, correlated frequency bins and the search over periods are not calibrated. No overall statistical pass is assigned. Inspect wave shapes, eastward spectra and EOF-pair coherence before drawing conclusions.','','Madden used a different reanalysis, period and spectral estimator. EOF files contain all 66 pairs for each m, ordered by variance; pair identification against Hough structures remains a scientific review step. See ../docs/methods.md.','','Numerical and resolution checks are recorded separately in data_checks.json and synthetic-tests.txt. Job timings and frozen environment are retained alongside the report.']
    (args.out/'STAGE1_REPORT.md').write_text('\n'.join(lines)+'\n')
    print('Analysis complete; scientific review required.',flush=True)

if __name__=='__main__':
    main()
