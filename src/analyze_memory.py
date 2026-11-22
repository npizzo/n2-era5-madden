"""Document-driven rotating-frame height persistence; all computation on Unity."""
import json,os
from pathlib import Path
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from n2tools import deseason,RADIUS
from memory_tools import lag_products,rotate_products,ratio,fit_collapse,crossing_time

OUT=Path('results/memory-v1');OUT.mkdir(parents=True,exist_ok=True)
LAGS=np.arange(241)*.25
YEARS=np.arange(1979,2023)
SEASONS=('ALL','DJF','JJA')
PREP=('raw','demeaned','deseasonalized','detrended_anomalies')
FIELDS=('height','streamfunction')
SECTORS=('all_m','nonzonal')
FRAMES=('earth','rossby_haurwitz')

def load_data():
    hs=[];zs=[];ts=[]
    for year in YEARS:
        with xr.open_dataset(f'data/memory-v1/height/height_{year}.nc') as d:
            hs.append(d.height_real.values+1j*d.height_imag.values);ts.append(d.time.values)
        with xr.open_dataset(f'data/stage1/coeffs_{year}.nc') as d:
            d=d.sel(level=500).isel(n=slice(0,11),m=slice(0,11))
            np.testing.assert_array_equal(d.time.values,ts[-1])
            zs.append(d.zeta_real.values+1j*d.zeta_imag.values)
    z=np.concatenate(zs).astype(complex)
    for n in range(1,11):z[:,n,:]*=-RADIUS**2/(n*(n+1))
    time=np.concatenate(ts)
    assert len(time)==64284 and np.all(np.diff(time)==np.timedelta64(6,'h'))
    return time,np.concatenate(hs),z

def segments(mask):
    ids=np.flatnonzero(mask)
    if not len(ids):return []
    return np.split(ids,np.flatnonzero(np.diff(ids)>1)+1)

def compute_products(time,values):
    # prep, season, sector, frame, year, degree, lag
    shape=(len(PREP),3,2,2,44,11,241);num=np.zeros(shape);den=np.zeros(shape)
    years=time.astype('datetime64[Y]').astype(int)+1970
    months=time.astype('datetime64[M]').astype(int)%12+1
    residual=deseason(time,values.reshape(len(time),-1)).reshape(values.shape)
    trend_time=np.arange(len(time),dtype=float);trend_time-=trend_time.mean()
    slope=np.einsum('t,tnm->nm',trend_time,residual)/np.sum(trend_time**2)
    for pi,kind in enumerate(PREP):
        x=values if kind=='raw' else values-values.mean(axis=0) if kind=='demeaned' else residual if kind=='deseasonalized' else residual-trend_time[:,None,None]*slope
        for yi,year in enumerate(YEARS):
            for si,season in enumerate(SEASONS):
                mask=years==year
                if season!='ALL':mask=mask&np.isin(months,[12,1,2] if season=='DJF' else [6,7,8])
                for ids in segments(mask):
                    if len(ids)<2:continue
                    for n in range(1,11):
                        q,d=lag_products(x[ids,n,:n+1],240)
                        for fi in range(2):
                            re=q.real if fi==0 else rotate_products(q,n)
                            for ei in range(2):
                                num[pi,si,ei,fi,yi,n]+=re[:,ei:].sum(axis=1)
                                den[pi,si,ei,fi,yi,n]+=d[:,ei:].sum(axis=1)
            print(json.dumps({'preprocessing':kind,'year':int(year)}),flush=True)
    return num,den

def bootstrap(num,den,reps=400):
    rng=np.random.default_rng(211126);out=[]
    for j in range(reps):
        ix=rng.integers(0,len(num),len(num))
        f=fit_collapse(ratio(num[ix].sum(axis=0),den[ix].sum(axis=0)),LAGS)
        out.append([f['b'],f['n2_mean_excess']])
    out=np.array(out)
    return {'replicates':reps,'b_ci95':np.quantile(out[:,0],[.025,.975]).tolist(),
            'n2_excess_ci95':np.quantile(out[:,1],[.025,.975]).tolist(),
            'bootstrap_fraction_excess_positive':float(np.mean(out[:,1]>0))},out

def fine_check(time,height):
    with xr.open_dataset('data/memory-v1/fine/height_1979.nc') as d:
        fine=d.height_real.values+1j*d.height_imag.values;t=d.time.values
    mask=time.astype('datetime64[Y]')==np.datetime64('1979','Y')
    coarse=height[mask];np.testing.assert_array_equal(t,time[mask])
    report={};curves=[]
    for array in (coarse,fine):
        a=deseason(t,array.reshape(len(t),-1)).reshape(array.shape)
        cs=[]
        for n in range(1,11):
            q,d=lag_products(a[:,n,:n+1],240)
            cs.append(ratio(rotate_products(q,n).sum(axis=1),d.sum(axis=1)))
        curves.append(np.array(cs))
    for n in range(1,11):
        report[str(n)]={'coefficient_relative_l2':float(np.linalg.norm(fine[:,n]-coarse[:,n])/np.linalg.norm(fine[:,n])),
                         'max_abs_correlation_difference_0_60d':float(np.max(abs(curves[0][n-1]-curves[1][n-1])))}
    report['scope']='1979 only, annual-harmonic removal fitted separately to that year on each grid; not full-record convergence'
    return report

def plot_and_report(c,num,den,summary):
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    colors={n:plt.cm.tab10(n-2) for n in range(2,9)}
    fig,axes=plt.subplots(2,2,figsize=(13,9),sharex=True,sharey=True)
    for ax,(prep,sector,frame,title) in zip(axes.flat,[(0,0,1,'Raw height · all orders · rotating frame'),(2,0,1,'Height anomalies · all orders · rotating frame'),(2,1,1,'Height anomalies · nonzonal · rotating frame'),(2,1,0,'Height anomalies · nonzonal · Earth-fixed')]):
        for n in range(2,9):ax.plot(LAGS,c[0,prep,0,sector,frame,n],color=colors[n],label=f'n={n}',lw=2.3 if n==2 else 1.3)
        ax.axhline(0,color='.6',lw=.7);ax.axhline(np.exp(-1),color='.7',ls=':',lw=.7)
        ax.set(title=title,xlim=(0,30),ylim=(-1.05,1.05),xlabel='Lag (days)',ylabel='Cₙ(T)');ax.legend(ncol=4,fontsize=9)
    fig.suptitle('500 hPa height persistence: climatology, zonal flow, and propagation controls')
    fig.tight_layout();fig.savefig(OUT/'memory_correlations.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    for ei,ax in enumerate(axes):
        fit=summary['primary'][SECTORS[ei]];b=fit['b'];tau=np.linspace(0,10,161)
        for n in range(2,9):
            ax.plot(tau,np.interp((n/3)**b*tau,LAGS,c[0,2,0,ei,1,n],left=np.nan,right=np.nan),color=colors[n],lw=2.5 if n==2 else 1.4,ls='-' if n<=5 else '--',label=f'n={n}'+(' · held out' if n==2 else ''))
        ax.axhline(0,color='.6',lw=.7);ax.set(xlabel='Rescaled lag T (days at n=3)',ylabel='Cₙ((n/3)ᵇ T)',title=f'{SECTORS[ei]} · a=0, b={b:.3f}',ylim=(-1.05,1.05));ax.legend(ncol=2,fontsize=9)
    fig.suptitle('Fit n=3–5; test n=2 without fitting it · height anomalies, rotating frame')
    fig.tight_layout();fig.savefig(OUT/'memory_collapse.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(15,4.5),sharey=True)
    for si,ax in enumerate(axes):
        for n in (2,3,4,5):ax.plot(LAGS,c[0,2,si,0,1,n],label=f'n={n}',color=colors[n])
        ax.axhline(0,color='.6',lw=.7);ax.set(title=SEASONS[si],xlabel='Lag (days)',xlim=(0,30),ylim=(-1.05,1.05));ax.legend()
    axes[0].set_ylabel('Cₙ(T)');fig.suptitle('500 hPa height anomalies · rotating frame · seasonal pairs stay contiguous')
    fig.tight_layout();fig.savefig(OUT/'memory_seasons.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(13,4.5),sharey=True)
    for fi,ax in enumerate(axes):
        for n in (1,2,3,4,5):ax.plot(LAGS,c[fi,2,0,0,1,n],label=f'n={n}')
        ax.axhline(0,color='.6',lw=.7);ax.set(title=FIELDS[fi],xlabel='Lag (days)',xlim=(0,30),ylim=(-1.05,1.05));ax.legend()
    axes[0].set_ylabel('Cₙ(T)');fig.suptitle('Field-definition control · anomalies in the theoretical rotating frame')
    fig.tight_layout();fig.savefig(OUT/'memory_field_control.png',dpi=160);plt.close(fig)
    lines=['# Rotating-frame memory analysis — document follow-up','','Status: **descriptive hypothesis test; scientific review required**.','',
           '500 hPa ERA5 height, 1979–2022; 64,284 six-hourly timestamps. Degrees 1–10 retained. The earlier vorticity-based analysis is a streamfunction control, not a substitute for height.','',
           '## Primary comparison','',
           '| Orders | a | b (n=3–5) | b bootstrap 95% interval | n=2 mean excess | Excess 95% interval | Collapse MSE | No-scaling MSE |',
           '|---|---:|---:|---|---:|---|---:|---:|']
    for sector,f in summary['primary'].items():
        lines.append(f"| {sector} | 0 | {f['b']:.3f} | {f['bootstrap']['b_ci95']} | {f['n2_mean_excess']:.4f} | {f['bootstrap']['n2_excess_ci95']} | {f['mse']:.5f} | {f['unscaled_mse']:.5f} |")
    lines+=['','The primary data remove the mean and four annual harmonics. Degree 2 is excluded from fitting. The signed excess is the mean difference from the n=3 reference over rescaled lags 0–10 days, with n=3–5 defining b. Positive excess supports relative persistence only if the reference collapse is adequate. It is not proof of a unique atmospheric memory mode.','',
            'Normalized Cₙ(0)=1 forces a=0 for a collapse including zero lag. Free-a,b fits are retained as a secondary relaxation in summary.json. Scaling is written relative to n=3; this only changes the common coordinate/amplitude convention of nᵃCₙ(nᵇT).','',
            '![Correlation controls](memory_correlations.png)','','![Held-out collapse](memory_collapse.png)','','## Persistence times','',
            '| n | First 1/e crossing (days) | First zero crossing (days) |','|---|---:|---:|']
    for n in range(1,11):
        v=c[0,2,0,0,1,n];lines.append(f"| {n} | {crossing_time(v,LAGS,np.exp(-1))} | {crossing_time(v,LAGS,0)} |")
    lines+=['','Missing crossings mean none occurred within 60 days; no extrapolated lifetime is assigned. Oscillatory correlations are not forced to decay monotonically.','',
            '![Seasonal comparison](memory_seasons.png)','','![Height and streamfunction](memory_field_control.png)','','## Uncertainty and robustness','',
            'The 400-replicate bootstrap resamples whole calendar-year numerator/denominator contributions and refits b. Lags never cross year boundaries or disconnected seasonal segments. This preserves within-year lag dependence but omits cross-year pairs. DJF treats December and January–February as separate contiguous pieces within each calendar-year cluster. Climatology is fitted once to the full record, not refitted in every bootstrap. Interannual dependence and reanalysis uncertainty are not calibrated.','',
            'The summary retains fits over 5-, 10-, and 15-day rescaled windows (15 days uses b bounds constrained by available lags), reference degrees 3–8, raw/demeaned/anomaly controls, Earth-fixed and theoretical rotating frames, individual seasons, and 1979–2000 versus 2001–2022. Finite fit bounds and sparse low-degree reference curves limit scaling inference.','',
            'The one-degree 1979 extraction checks this new height analysis separately from the earlier failed vorticity coefficient criterion. See resolution_height.json; a one-year check cannot prove full-record convergence.','',
            'The Rossby–Haurwitz rotation law is exact for the ideal single-degree nondivergent barotropic problem. It is a hypothesis to test for observed geopotential height, which is not globally identical to streamfunction. Background winds, divergence, and baroclinic coupling can leave propagation in this frame.','',
            '[Revised approach](../../docs/memory_approach.md) · [Numerical correlations](correlations.nc) · [Fit and robustness results](summary.json) · [Synthetic tests](synthetic-tests.txt)']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n')

def main():
    time,height,psi=load_data();nums=[];dens=[]
    for field,values in zip(FIELDS,(height,psi)):
        print('FIELD',field,flush=True);n,d=compute_products(time,values);nums.append(n);dens.append(d)
    num=np.array(nums);den=np.array(dens);c=ratio(num.sum(axis=5),den.sum(axis=5))
    dims=('field','preprocessing','season','sector','frame','year','n','lag_days')
    coords={'field':list(FIELDS),'preprocessing':list(PREP),'season':list(SEASONS),'sector':list(SECTORS),'frame':list(FRAMES),'year':YEARS,'n':np.arange(11),'lag_days':LAGS}
    ds=xr.Dataset({'numerator':(dims,num),'denominator':(dims,den)},coords=coords,attrs={'estimator':'sum lagged degree inner products / sum later-time degree energies; same valid pairs','normalization':'4pi real harmonics, a=C-iS','frame_factor':'exp(-i*m*2*Omega*T/(n*(n+1)))','n0':'excluded; zero denominators','units':'height products m2, streamfunction products m4 s-2','job_id':os.environ.get('SLURM_JOB_ID','unknown')})
    ds['correlation']=ds.numerator.sum('year')/ds.denominator.sum('year')
    ds[['numerator','denominator']].to_netcdf('data/memory-v1/year_products.nc',encoding={v:{'zlib':True,'complevel':4} for v in ('numerator','denominator')})
    ds[['correlation']].to_netcdf(OUT/'correlations.nc',encoding={'correlation':{'zlib':True,'complevel':4}})
    summary={'primary':{},'controls':{},'time_splits':{},'fit_sensitivity':{},'sample_count':len(time),'job_id':os.environ.get('SLURM_JOB_ID','unknown')}
    for ei,sector in enumerate(SECTORS):
        curve=c[0,2,0,ei,1];f=fit_collapse(curve,LAGS);boot,draws=bootstrap(num[0,2,0,ei,1],den[0,2,0,ei,1]);f['bootstrap']=boot;f['free_amplitude_fit']=fit_collapse(curve,LAGS,free_a=True)
        summary['primary'][sector]=f;np.save(OUT/f'bootstrap_{sector}.npy',draws)
        summary['fit_sensitivity'][sector]={'five_days':fit_collapse(curve,LAGS,tmax=5),'fifteen_days':fit_collapse(curve,LAGS,tmax=15),'degrees_3_to_8':fit_collapse(curve,LAGS,degrees=(3,4,5,6,7,8))}
        for lo,hi,label in [(0,22,'1979-2000'),(22,44,'2001-2022')]:
            sub=ratio(num[0,2,0,ei,1,lo:hi].sum(axis=0),den[0,2,0,ei,1,lo:hi].sum(axis=0))
            summary['time_splits'][sector+'_'+label]=fit_collapse(sub,LAGS)
        early=ratio(num[0,2,0,ei,1,:22].sum(axis=0),den[0,2,0,ei,1,:22].sum(axis=0));late=ratio(num[0,2,0,ei,1,22:].sum(axis=0),den[0,2,0,ei,1,22:].sum(axis=0))
        b=fit_collapse(early,LAGS)['b'];tau=np.linspace(0,10,81)
        summary['time_splits'][sector+'_early_b_tested_late']={'b':b,'n2_mean_excess':float(np.trapezoid(np.interp((2/3)**b*tau,LAGS,late[2])-np.interp(tau,LAGS,late[3]),tau)/10)}
    for fi,field in enumerate(FIELDS):
        for pi,prep in enumerate(PREP):
            for si,season in enumerate(SEASONS):
                for ei,sector in enumerate(SECTORS):
                    for ri,frame in enumerate(FRAMES):
                        curve=c[fi,pi,si,ei,ri]
                        summary['controls']['/'.join([field,prep,season,sector,frame])]=fit_collapse(curve,LAGS)
    # Fit bounds prevent any interpolation request outside observed lag support.
    resolution=fine_check(time,height);(OUT/'resolution_height.json').write_text(json.dumps(resolution,indent=2))
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    plot_and_report(c,num,den,summary)
    print(json.dumps(summary['primary'],indent=2),flush=True)
if __name__=='__main__':main()
