"""Order-resolved covariance attribution. Numerical work runs on Unity."""
import csv,json,os
from pathlib import Path
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from n2tools import deseason
from memory_tools import lag_products,rotate_products,ratio,crossing_time
from memory_utc_control import remove_utc_cycle

YEARS=np.arange(1979,2023);NS=np.arange(2,6);LAGS=np.arange(241)*.25
PREPS=['anomalies','utc_cycle_removed'];FRAMES=['earth','rossby_haurwitz']
WINDOWS=[(5,30),(2,10),(10,30)]
OUT=Path('results/memory-orders-v1')

def decompose(num,den,pairs):
    """Inputs lag x order sums; pairs is lag. Zero variance orders stay NaN."""
    cov=num/pairs[:,None];energy=den/pairs[:,None]
    var=energy[0];total=var.sum()
    return {'covariance':cov,'pair_energy':energy,'fixed_contribution':cov/total,
            'own_correlation':ratio(cov,energy),'prior_contribution':cov/energy.sum(axis=1)[:,None],
            'variance':var,'variance_fraction':var/total}

def window_mean(x,lo,hi):
    mask=(LAGS>=lo)&(LAGS<=hi)
    return np.trapezoid(x[mask],LAGS[mask],axis=0)/(hi-lo)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'summary.json').exists():raise RuntimeError('Completed results exist; choose a new run directory.')
    arrays=[];times=[]
    for y in YEARS:
        with xr.open_dataset(f'data/memory-v1/height/height_{y}.nc') as d:
            arrays.append(d.height_real.values[:,:6,:6]+1j*d.height_imag.values[:,:6,:6]);times.append(d.time.values)
    time=np.concatenate(times);raw=np.concatenate(arrays)
    assert len(time)==64284 and np.all(np.diff(time)==np.timedelta64(6,'h'))
    x=deseason(time,raw.reshape(len(time),-1)).reshape(raw.shape)
    clean,_=remove_utc_cycle(time,x)
    year=time.astype('datetime64[Y]').astype(int)+1970
    # preprocessing, frame, year, n, lag, m. Padded orders are zero.
    nums=np.zeros((2,2,44,4,241,6));dens=np.zeros((2,44,4,241,6));pairs=np.zeros((44,241))
    for yi,y in enumerate(YEARS):
        ids=year==y;pairs[yi]=ids.sum()-np.arange(241)
        for pi,values in enumerate((x,clean)):
            for ni,n in enumerate(NS):
                q,d=lag_products(values[ids,n,:n+1],240)
                nums[pi,0,yi,ni,:,:n+1]=q.real
                nums[pi,1,yi,ni,:,:n+1]=rotate_products(q,n)
                dens[pi,yi,ni,:,:n+1]=d
    dims=('preprocessing','frame','year','n','lag_days','m')
    ds=xr.Dataset({'lag_product_sum':(dims,nums),
        'later_energy_sum':(('preprocessing','year','n','lag_days','m'),dens),
        'pair_count':(('year','lag_days'),pairs)},
        coords={'preprocessing':PREPS,'frame':FRAMES,'year':YEARS,'n':NS,'lag_days':LAGS,'m':np.arange(6)},
        attrs={'units':'height products m2; pair_count dimensionless','normalization':'real 4pi harmonics, a=C-iS; order products equal area-mean contributions',
               'boundary':'within-calendar-year pairs only; full-record anomaly fit held fixed',
               'invalid_orders':'m>n padded with zero; excluded from tabular metrics',
               'job_id':os.environ.get('SLURM_JOB_ID','unknown')})
    ds.to_netcdf(OUT/'annual_products.nc',encoding={k:{'zlib':True,'complevel':4} for k in ds.data_vars})
    agg={};rows=[];split_rows=[];draw_rows=[];closure={}
    rng=np.random.default_rng(221126);draws=rng.integers(0,44,size=(400,44))
    for pi,prep in enumerate(PREPS):
        for fi,frame in enumerate(FRAMES):
            for ni,n in enumerate(NS):
                q=nums[pi,fi,:,ni,:,:n+1];d=dens[pi,:,ni,:,:n+1]
                v=decompose(q.sum(axis=0),d.sum(axis=0),pairs.sum(axis=0));agg[pi,fi,ni]=v
                boot={key:[] for key in ('variance','variance_fraction','covariance','fixed_contribution','own_correlation')}
                for ix in draws:
                    z=decompose(q[ix].sum(axis=0),d[ix].sum(axis=0),pairs[ix].sum(axis=0))
                    for key in boot:
                        boot[key].append(z[key] if key.startswith('variance') else np.array([window_mean(z[key],*w) for w in WINDOWS]))
                ci={k:np.quantile(b,[.025,.975],axis=0) for k,b in boot.items()}
                for m in range(n+1):
                    for wi,(lo,hi) in enumerate(WINDOWS):
                        row={'preprocessing':prep,'frame':frame,'n':int(n),'m':m,'window_days':f'{lo}-{hi}',
                             'variance_m2':float(v['variance'][m]),'variance_fraction':float(v['variance_fraction'][m]),
                             'variance_fraction_ci_low':float(ci['variance_fraction'][0,m]),'variance_fraction_ci_high':float(ci['variance_fraction'][1,m]),
                             'first_efold_days':crossing_time(v['own_correlation'][:,m],LAGS,np.exp(-1))}
                        for key in ('covariance','fixed_contribution','own_correlation'):
                            row[key]=float(window_mean(v[key],lo,hi)[m])
                            row[key+'_ci_low']=float(ci[key][0,wi,m]);row[key+'_ci_high']=float(ci[key][1,wi,m])
                        rows.append(row)
                for lo,hi,label in [(0,22,'1979-2000'),(22,44,'2001-2022')]:
                    z=decompose(q[lo:hi].sum(axis=0),d[lo:hi].sum(axis=0),pairs[lo:hi].sum(axis=0))
                    for m in range(n+1):split_rows.append({'preprocessing':prep,'frame':frame,'n':int(n),'m':m,'years':label,
                        'variance_fraction':float(z['variance_fraction'][m]),'covariance_5_30':float(window_mean(z['covariance'],5,30)[m]),
                        'fixed_contribution_5_30':float(window_mean(z['fixed_contribution'],5,30)[m])})
                # Paired bootstrap contrast: n=2 later against n=3..5 assembled below.
                for j in range(400):
                    for m in range(n+1):draw_rows.append([pi,fi,ni,m,j,*[boot['fixed_contribution'][j][wi,m] for wi in range(3)]])
    # Reconstruct prior lag-dependent normalization, independently for all/nonzonal.
    with xr.open_dataset('results/memory-v1/correlations.nc') as old,xr.open_dataset('results/memory-v1/utc_control_correlations.nc') as utc:
        for pi in range(2):
            for fi,frame in enumerate(FRAMES):
                for ni,n in enumerate(NS):
                    v=agg[pi,fi,ni]
                    for start,sector in [(0,'all_m'),(1,'nonzonal')]:
                        calc=v['covariance'][:,start:].sum(axis=1)/v['pair_energy'][:,start:].sum(axis=1)
                        target=(old.correlation.sel(field='height',preprocessing='deseasonalized',season='ALL',sector=sector,frame=frame,n=n).values if pi==0 else utc.correlation.sel(sector=sector,frame=frame,n=n).values)
                        err=float(np.max(abs(calc-target)));closure[f'{PREPS[pi]}/{frame}/n{n}/{sector}']=err
                        np.testing.assert_allclose(calc,target,atol=1e-11,rtol=1e-10)
    data={key:np.full((2,2,4,241,6),np.nan) for key in ('covariance','pair_energy','fixed_contribution','own_correlation','prior_contribution')}
    for (pi,fi,ni),v in agg.items():
        for key in data:data[key][pi,fi,ni,:,:NS[ni]+1]=v[key]
    curves=xr.Dataset({key:(('preprocessing','frame','n','lag_days','m'),val) for key,val in data.items()},coords={'preprocessing':PREPS,'frame':FRAMES,'n':NS,'lag_days':LAGS,'m':np.arange(6)},attrs=ds.attrs)
    curves['covariance'].attrs['units']='m2';curves['pair_energy'].attrs['units']='m2'
    curves.to_netcdf(OUT/'order_curves.nc',encoding={k:{'zlib':True,'complevel':4} for k in curves.data_vars})
    for name,table in [('order_metrics.csv',rows),('time_halves.csv',split_rows)]:
        with (OUT/name).open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    draws_array=np.array(draw_rows);np.save(OUT/'paired_bootstrap_contributions.npy',draws_array)
    # Contrasts across degrees and an exact zonal/nonzonal budget, same denominator per degree.
    budgets=[]
    for pi,prep in enumerate(PREPS):
        for wi,win in enumerate(WINDOWS):
            values=[];boots=[]
            for ni,n in enumerate(NS):
                v=agg[pi,1,ni];t=window_mean(v['fixed_contribution'],*win)
                z=draws_array[(draws_array[:,0]==pi)&(draws_array[:,1]==1)&(draws_array[:,2]==ni)]
                b=np.array([[z[(z[:,3]==m)&(z[:,4]==j),5+wi][0] for m in range(n+1)] for j in range(400)])
                values.append([t[0],t[1:].sum(),t.sum()]);boots.append(np.column_stack([b[:,0],b[:,1:].sum(axis=1),b.sum(axis=1)]))
                for si,sector in enumerate(['zonal','nonzonal','total']):
                    ci=np.quantile(boots[-1][:,si],[.025,.975]);budgets.append({'preprocessing':prep,'window_days':f'{win[0]}-{win[1]}','n':int(n),'component':sector,'fixed_contribution':float(values[-1][si]),'ci95':ci.tolist()})
            for ni,n in enumerate(NS[1:],start=1):
                for si,sector in enumerate(['zonal','nonzonal','total']):
                    contrast=boots[0][:,si]-boots[ni][:,si]
                    budgets.append({'preprocessing':prep,'window_days':f'{win[0]}-{win[1]}','contrast':f'n2-minus-n{n}','component':sector,'fixed_contribution':float(values[0][si]-values[ni][si]),'ci95':np.quantile(contrast,[.025,.975]).tolist()})
    summary={'job_id':os.environ.get('SLURM_JOB_ID','unknown'),'sample_count':len(time),'bootstrap_replicates':400,
             'primary_tail_window_days':[5,30],'max_prior_reconstruction_error':max(closure.values()),'reconstruction_errors':closure,'budgets_and_paired_contrasts':budgets,
             'bootstrap_draw_columns':['prep_index','frame_index','degree_index_2_to_5','m','replicate','5_30','2_10','10_30']}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    plot(agg,rows,budgets)
    primary=[r for r in rows if r['frame']=='rossby_haurwitz' and r['window_days']=='5-30' and r['n']==2]
    report=['# Order-resolved atmospheric memory','',f'Completed on Unity, job {summary["job_id"]}. Height anomalies, 500 hPa, 1979–2022.','',
            'No time scaling is fitted here. The primary later-tail window is fixed at physical lags 5–30 days. Components are summed under a common total-degree variance denominator; the previous all-order and nonzonal curves reconstruct to a maximum absolute error of '+f'{max(closure.values()):.3g}.','',
            '| Data | Order m | Variance fraction | Tail covariance (m²) | Contribution / total variance | 95% interval | Own normalized tail |','|---|---:|---:|---:|---:|---|---:|']
    for r in primary:report.append(f'| {r["preprocessing"]} | {r["m"]} | {r["variance_fraction"]:.4f} | {r["covariance"]:.4f} | {r["fixed_contribution"]:.4f} | [{r["fixed_contribution_ci_low"]:.4f}, {r["fixed_contribution_ci_high"]:.4f}] | {r["own_correlation"]:.4f} |')
    report+=['','![Degree-2 covariance budget](order_covariance.png)','','![Degree-2 own correlations](order_correlations.png)','','![Variance and tail comparison](order_degree_comparison.png)','','![Paired degree comparisons](order_tail_contrasts.png)','',
             'Intervals are paired whole-year bootstrap intervals with climatology and UTC correction held fixed. Negative contributions are retained. Products use full-record anomalies and are not re-centered separately at each lag or year. No causal mechanism or forecast skill is inferred.','',
             '[Specification](../../docs/order_memory_approach.md) · [All metrics and window sensitivities](order_metrics.csv) · [Time halves](time_halves.csv) · [Numerical curves](order_curves.nc) · [Annual products](annual_products.nc) · [Summary and paired contrasts](summary.json)']
    (OUT/'REPORT.md').write_text('\n'.join(report)+'\n')
    print(json.dumps({'n2_primary':primary,'budgets': [b for b in budgets if b['window_days']=='5-30'],'reconstruction':max(closure.values())},indent=2),flush=True)

def plot(agg,rows,budgets):
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    colors=['#24586c','#bc7330','#8b568e','#62934a','#5e7eaa','#a94c4c']
    fig,axs=plt.subplots(2,2,figsize=(13,8),sharex=True)
    for pi in range(2):
        v=agg[pi,1,0]
        for ri,key in enumerate(['covariance','fixed_contribution']):
            ax=axs[ri,pi]
            for m in range(3):ax.plot(LAGS,v[key][:,m],label=f'm={m}',color=colors[m])
            ax.plot(LAGS,v[key].sum(axis=1),color='.2',ls='--',label='sum of orders')
            ax.axhline(0,color='.6',lw=.7);ax.axvspan(5,30,color='.8',alpha=.18)
            ax.set(xlim=(0,30),xlabel='Physical lag (days)',ylabel='Covariance (m²)' if ri==0 else 'Contribution / total n=2 variance',title=['Original anomalies','UTC cycle removed'][pi]);ax.legend(fontsize=9)
    fig.suptitle('Degree 2: exact covariance budget in the rotating frame');fig.tight_layout();fig.savefig(OUT/'order_covariance.png',dpi=160);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(13,4.5),sharey=True)
    for pi,ax in enumerate(axs):
        for m in range(3):
            ax.plot(LAGS,agg[pi,1,0]['own_correlation'][:,m],label=f'm={m} · rotating',color=colors[m])
            if m:ax.plot(LAGS,agg[pi,0,0]['own_correlation'][:,m],ls=':',lw=1,label=f'm={m} · Earth-fixed',color=colors[m])
        ax.axhline(0,color='.6',lw=.7);ax.set(xlim=(0,30),ylim=(-1.05,1.05),xlabel='Physical lag (days)',title=['Original anomalies','UTC cycle removed'][pi]);ax.legend(fontsize=9)
    axs[0].set_ylabel('Each order normalized by its own pair energy');fig.suptitle('Degree 2: order-specific persistence and frame sensitivity');fig.tight_layout();fig.savefig(OUT/'order_correlations.png',dpi=160);plt.close(fig)
    fig,axs=plt.subplots(2,2,figsize=(12,8))
    for pi in range(2):
        bottom=np.zeros(4)
        for m in range(6):
            shares=np.array([agg[pi,1,ni]['variance_fraction'][m] if m<=n else 0 for ni,n in enumerate(NS)])
            axs[0,pi].bar(NS,shares,bottom=bottom,color=colors[m],label=f'm={m}');bottom+=shares
        for m in range(6):
            rr=[next((r for r in rows if r['preprocessing']==PREPS[pi] and r['frame']=='rossby_haurwitz' and r['n']==n and r['m']==m and r['window_days']=='5-30'),None) for n in NS]
            xx=np.array([n+(m-2.5)*.12 for n,r in zip(NS,rr) if r]);yy=np.array([r['fixed_contribution'] for r in rr if r]);low=np.array([r['fixed_contribution_ci_low'] for r in rr if r]);high=np.array([r['fixed_contribution_ci_high'] for r in rr if r])
            axs[1,pi].vlines(xx,low,high,color=colors[m]);axs[1,pi].scatter(xx,yy,color=colors[m],s=22)
        for ax in axs[:,pi]:ax.set(xticks=NS,xlabel='Spherical-harmonic degree n',title=['Original anomalies','UTC cycle removed'][pi])
        axs[0,pi].legend(ncol=3,fontsize=9);axs[1,pi].axhline(0,color='.6',lw=.7)
    axs[0,0].set_ylabel('Fraction of zero-lag degree variance');axs[1,0].set_ylabel('Mean 5–30 day contribution / degree variance')
    fig.suptitle('Which orders carry variance and the later tail? · 95% year-bootstrap intervals');fig.tight_layout();fig.savefig(OUT/'order_degree_comparison.png',dpi=160);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(12,4.5),sharey=True)
    for pi,ax in enumerate(axs):
        for si,sector in enumerate(['zonal','nonzonal','total']):
            rr=[next(b for b in budgets if b['preprocessing']==PREPS[pi] and b['window_days']=='5-30' and b.get('contrast')==f'n2-minus-n{n}' and b['component']==sector) for n in [3,4,5]]
            xx=np.arange(3)+(si-1)*.18;yy=[r['fixed_contribution'] for r in rr]
            ax.vlines(xx,[r['ci95'][0] for r in rr],[r['ci95'][1] for r in rr],color=colors[si]);ax.scatter(xx,yy,color=colors[si],label=sector)
        ax.axhline(0,color='.6',lw=.7);ax.set(xticks=np.arange(3),xticklabels=['n2 − n3','n2 − n4','n2 − n5'],title=['Original anomalies','UTC cycle removed'][pi]);ax.legend()
    axs[0].set_ylabel('Difference in 5–30 day normalized contribution');fig.suptitle('Degree-2 tail contrast · paired 95% year-bootstrap intervals');fig.tight_layout();fig.savefig(OUT/'order_tail_contrasts.png',dpi=160);plt.close(fig)

if __name__=='__main__':main()
