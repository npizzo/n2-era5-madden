"""Post-inspection control for the repeating UTC sampling-time cycle in height."""
import json,os
from pathlib import Path
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from scipy.signal import welch
from n2tools import deseason
from memory_tools import lag_products,rotate_products,ratio,fit_collapse,crossing_time


def remove_utc_cycle(time,x):
    month=time.astype('datetime64[M]').astype(int)%12+1
    hour=time.astype('datetime64[h]').astype(int)%24
    component=np.zeros_like(x)
    for mon in np.unique(month):
        mm=month==mon;mean=x[mm].mean(axis=0)
        for hh in np.unique(hour):
            ids=mm&(hour==hh);component[ids]=x[ids].mean(axis=0)-mean
    return x-component,component


def stats(time,x):
    years=time.astype('datetime64[Y]').astype(int)+1970
    num=np.zeros((2,2,44,11,241));den=num.copy()
    for yi,year in enumerate(range(1979,2023)):
        values=x[years==year]
        for n in range(1,11):
            q,d=lag_products(values[:,n,:n+1],240)
            for frame in range(2):
                re=q.real if frame==0 else rotate_products(q,n)
                for sector in range(2):
                    num[sector,frame,yi,n]=re[:,sector:].sum(axis=1)
                    den[sector,frame,yi,n]=d[:,sector:].sum(axis=1)
    return num,den


def main():
    out=Path('results/memory-v1');data=[];times=[]
    for year in range(1979,2023):
        with xr.open_dataset(f'data/memory-v1/height/height_{year}.nc') as d:
            data.append(d.height_real.values+1j*d.height_imag.values);times.append(d.time.values)
    time=np.concatenate(times);raw=np.concatenate(data)
    x=deseason(time,raw.reshape(len(time),-1)).reshape(raw.shape)
    filtered,component=remove_utc_cycle(time,x)
    num,den=stats(time,filtered);c=ratio(num.sum(axis=2),den.sum(axis=2));lags=np.arange(241)*.25
    from analyze_memory import bootstrap
    result={'scope':'Post-inspection sensitivity; the primary preregistered comparison is unchanged. Remove month-dependent UTC-hour departures from each monthly mean, using all 44 years. This removes a repeating sampling-time cycle, without attributing it to physical tides versus analysis effects. Six-hour sampling does not fully resolve semidiurnal phase.',
            'job_id':os.environ.get('SLURM_JOB_ID','unknown'),'sectors':{}}
    for ei,sector in enumerate(('all_m','nonzonal')):
        f=fit_collapse(c[ei,1],lags);f['bootstrap'],_=bootstrap(num[ei,1],den[ei,1])
        f['removed_n2_variance_fraction']=float(np.sum(abs(component[:,2,ei:])**2)/np.sum(abs(x[:,2,ei:])**2))
        f['n2_first_efold_days']=crossing_time(c[ei,1,2],lags,np.exp(-1));f['n2_first_zero_days']=crossing_time(c[ei,1,2],lags,0)
        result['sectors'][sector]=f
    xr.Dataset({'correlation':(('sector','frame','n','lag_days'),c)},coords={'sector':['all_m','nonzonal'],'frame':['earth','rossby_haurwitz'],'n':np.arange(11),'lag_days':lags},attrs={'scope':result['scope']}).to_netcdf(out/'utc_control_correlations.nc')
    (out/'utc_control_summary.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    with xr.open_dataset(out/'correlations.nc') as d:before=d.correlation.sel(field='height',preprocessing='deseasonalized',season='ALL',frame='rossby_haurwitz').values
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(1,2,figsize=(13,5),sharey=True)
    for ei,ax in enumerate(axs):
        ax.plot(lags,before[ei,2],color='0.6',lw=1,label='n=2 · before UTC-cycle removal')
        for n in (2,3,4,5):ax.plot(lags,c[ei,1,n],lw=2.5 if n==2 else 1.3,label=f'n={n} · UTC-cycle removed')
        ax.axhline(0,color='.6',lw=.7);ax.set(xlim=(0,15),ylim=(-1.05,1.05),xlabel='Lag (days)',title=('All orders','Nonzonal orders')[ei]);ax.legend(fontsize=9)
    axs[0].set_ylabel('Cₙ(T)');fig.suptitle('Post-inspection control: repeating UTC cycle removed before frame rotation')
    fig.tight_layout();fig.savefig(out/'memory_utc_control.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4.5))
    for label,values in [('Original anomalies',x),('UTC-cycle removed',filtered)]:
        freq,power=welch(values[:,2,1:3],fs=4,nperseg=2048,axis=0,return_onesided=False)
        ix=np.argsort(freq);ax.semilogy(freq[ix],power.sum(axis=1)[ix],label=label)
    ax.set(xlim=(-2,2),xlabel='Frequency (cycles/day; complex coefficient convention)',ylabel='n=2 nonzonal height PSD (m² day)',title='Earth-fixed temporal spectrum · 6-hour sampling, Nyquist 2 cycles/day');ax.legend()
    fig.tight_layout();fig.savefig(out/'memory_utc_spectrum.png',dpi=160);plt.close(fig)
    print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
