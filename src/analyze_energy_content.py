"""Degree-space KE climatology and explicitly limited historical comparison."""
import csv
import json
import os
from pathlib import Path
import numpy as np
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from n2tools import ke_spectrum, RADIUS

OUT=Path('results');OUT.mkdir(exist_ok=True)
YEARS=np.arange(1979,2023);N=np.arange(60)
SEASONS={'ALL':list(range(1,13)),'DJF':[12,1,2],'JJA':[6,7,8]}
KINDS=['rotational','divergent','total']
annual=np.zeros((44,2,3,3,60));counts=np.zeros((44,3))
zsum=np.zeros((2,3,2,22,22));dsum=np.zeros_like(zsum)
for yi,year in enumerate(YEARS):
    with xr.open_dataset(f'data/stage1/coeffs_{year}.nc') as r, xr.open_dataset(f'data/energy/divergent_{year}.nc') as d:
        np.testing.assert_array_equal(r.time.values,d.time.values)
        er=r.ke_rot.values;ed=d.ke_div.values
        cr=r.zeta_real.values;cs=-r.zeta_imag.values
        months=r.time.dt.month.values
        for si,(season,month_list) in enumerate(SEASONS.items()):
            mask=np.isin(months,month_list);count=int(mask.sum());counts[yi,si]=count
            annual[yi,:,si,0]=er[mask].mean(axis=0)
            annual[yi,:,si,1]=ed[mask].mean(axis=0)
            annual[yi,:,si,2]=annual[yi,:,si,:2].sum(axis=1)
            zsum[:,si,0]+=cr[mask].sum(axis=0,dtype=np.float64)
            zsum[:,si,1]+=cs[mask].sum(axis=0,dtype=np.float64)
            if int(d.monthly_count.sel(month=month_list).sum())!=count:
                raise ValueError('Monthly divergence counts do not match')
            dsum[:,si]+=d.monthly_sum_cilm.sel(month=month_list).sum('month').values
mean=np.sum(annual*counts[:,None,:,None,None],axis=0)/counts.sum(axis=0)[None,:,None,None]
stationary=np.zeros((2,3,22))
for li in range(2):
    for si in range(3):
        count=counts[:,si].sum()
        stationary[li,si]=ke_spectrum(zsum[li,si]/count,dsum[li,si]/count)
transient=mean[:,:,2,:22]-stationary
if transient.min() < -1e-7:
    raise ValueError('Negative transient energy beyond rounding')
transient=np.maximum(transient,0)
result=xr.Dataset({'annual_energy':(('year','level','season','kind','n'),annual),'mean_energy':(('level','season','kind','n'),mean),'stationary_total':(('level','season','n_low'),stationary),'transient_total':(('level','season','n_low'),transient)},coords={'year':YEARS,'level':[300,500],'season':list(SEASONS),'kind':KINDS,'n':N,'n_low':np.arange(22)},attrs={'units':'m2 s-2 per degree','stationary_definition':'KE of long-term mean coefficients within the selected months; transient is mean KE minus stationary KE','job_id':os.environ.get('SLURM_JOB_ID','unknown')})
result.to_netcdf(OUT/'energy_degree_statistics.nc')
with (OUT/'energy_degree_spectra.csv').open('w',newline='') as stream:
    writer=csv.writer(stream);writer.writerow(['level_hpa','season','degree','rotational_m2_s2','divergent_m2_s2','total_m2_s2','stationary_total_m2_s2','transient_total_m2_s2'])
    for li,level in enumerate([300,500]):
        for si,season in enumerate(SEASONS):
            for n in range(1,60):
                writer.writerow([level,season,n,*mean[li,si,:,n],stationary[li,si,n] if n<=21 else '',transient[li,si,n] if n<=21 else ''])

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(2,2,figsize=(12,9),constrained_layout=True)
colors=['#1769aa','#cd6b32','#222222']
for li,level in enumerate([300,500]):
    ax=axs[0,li]
    for ki,kind in enumerate(KINDS):
        ax.loglog(N[1:],mean[li,0,ki,1:],color=colors[ki],label=kind)
    ref=mean[li,0,2,15]*(N[10:]/15)**-3.
    ax.loglog(N[10:],ref,color='#999999',ls=':',label='n⁻³ shape guide, anchored at n=15')
    ax.axvline(2,color='#a33370',ls='--',lw=.8)
    ax.set(title=f'{level} hPa · 1979–2022 mean',xlabel='Total spherical-harmonic degree n',ylabel='KE per degree (m² s⁻²)',xlim=(1,59))
    ax.legend(fontsize=8)
    ax=axs[1,li]
    for si,season in enumerate(SEASONS):
        ax.loglog(N[1:],mean[li,si,2,1:],label=season)
    lower,upper=np.percentile(annual[:,li,0,2,1:],[5,95],axis=0)
    ax.fill_between(N[1:],lower,upper,color='gray',alpha=.15,label='5–95% spread of annual spectra')
    ax.set(title=f'{level} hPa · seasonal total KE',xlabel='Total spherical-harmonic degree n',ylabel='KE per degree (m² s⁻²)',xlim=(1,59))
    ax.legend(fontsize=8)
fig.suptitle('ERA5 kinetic energy by spherical-harmonic degree\nSpectral energy is averaged after transformation; guide amplitudes are not historical measurements.')
fig.savefig(OUT/'energy_degree_spectra.png',dpi=170);plt.close(fig)

fig,axs=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
for li,level in enumerate([300,500]):
    ax=axs[0,li];n=np.arange(1,22)
    ax.semilogy(n,mean[li,0,2,1:22],'o-',label='total mean KE')
    ax.semilogy(n,stationary[li,0,1:],'o-',label='KE of long-term mean flow')
    ax.semilogy(n,transient[li,0,1:],'o-',label='transient KE')
    ax.axvline(2,color='#a33370',ls='--');ax.set(xlim=(1,21),title=f'{level} hPa · low-degree partition',xlabel='n',ylabel='KE per degree (m² s⁻²)');ax.legend(fontsize=8)
    ax=axs[1,li]
    for si,season in enumerate(SEASONS):
        ax.semilogx(N[1:],mean[li,si,1,1:]/mean[li,si,2,1:],label=season)
    ax.set(title=f'{level} hPa · divergent fraction',xlabel='n',ylabel='Divergent / total KE',xlim=(1,59),ylim=(0,1));ax.legend(fontsize=8)
fig.suptitle('Mean-flow and transient content, with n=2 highlighted\nMean flow is the long-term seasonal mean; this is not a nonlinear transfer diagnostic.')
fig.savefig(OUT/'energy_degree_decomposition.png',dpi=170);plt.close(fig)

# Bootstrap entire calendar-year spectra, not individual correlated degree bins.
rng=np.random.default_rng(2481);samples=rng.integers(0,44,size=(1000,44))
slopes=[]
for li,level in enumerate([300,500]):
    for si,season in enumerate(SEASONS):
        for lo,hi in [(10,20),(13,40)]:
            idx=np.arange(lo,hi+1);x=np.log(idx);xc=x-x.mean()
            slope=float(np.dot(np.log(mean[li,si,2,idx]),xc)/np.dot(xc,xc))
            spectra=annual[:,li,si,2,:][samples]
            w=counts[:,si][samples]
            boot=np.sum(spectra*w[:,:,None],axis=1)/w.sum(axis=1)[:,None]
            bs=np.log(boot[:,idx])@xc/np.dot(xc,xc)
            slopes.append({'level':level,'season':season,'range':[lo,hi],'slope':slope,'year_bootstrap_95':np.percentile(bs,[2.5,97.5]).tolist()})

with xr.open_dataset('data/energy/historical_window.nc') as hist:
    pressure=[92,100,150,200,250,300,353]
    layer=hist.energy.interp(level=pressure).integrate('level')/(353-92)
    layer=layer.mean('year').load()
layer.to_dataset(name='energy').to_netcdf(OUT/'historical_window_layer.nc')
fig,axs=plt.subplots(1,3,figsize=(14,4.8),constrained_layout=True)
for ax,kind,label in zip(axs,['vector_total','rotational','divergent'],['Total','Rotational','Divergent']):
    energy=layer.sel(kind=kind).values
    ax.loglog(N[1:],energy[1:],lw=2,label='ERA5 · matching years/month/layer')
    ax.loglog(N[10:],energy[15]*(N[10:]/15)**-3.,ls=':',color='gray',label='n⁻³ guide normalized to ERA5')
    if kind=='vector_total':
        ax.loglog(N[1:],layer.sel(kind='scalar_uv_total').values[1:],ls='--',color='#ad6b32',label='ERA5 direct scalar u,v expansion')
    ax.axvspan(10,20,color='#2d9670',alpha=.13,label='UKMO total-KE comparison interval')
    ax.axvline(30,color='gray',ls='--',lw=.8)
    ax.set(title=label,xlim=(1,59),xlabel='Spherical-harmonic degree n',ylabel='Layer-mean KE per degree (m² s⁻²)')
    ax.legend(fontsize=7,loc='lower left')
fig.suptitle('Historical context: July 1993–1997, 92–353 hPa\nUKMO benchmark: Koshyk & Hamilton (2001), Fig. 4; historical ordinates were not digitized.')
fig.savefig(OUT/'historical_degree_comparison.png',dpi=170);plt.close(fig)

low=[]
for li,level in enumerate([300,500]):
    for si,season in enumerate(SEASONS):
        e=mean[li,si,2]
        low.append({'level':level,'season':season,'E1':float(e[1]),'E2':float(e[2]),'E3':float(e[3]),'n2_below_neighbors':bool(e[2]<min(e[1],e[3])),'n2_stationary_fraction':float(stationary[li,si,2]/e[2]),'n2_divergent_fraction':float(mean[li,si,1,2]/e[2])})
layer_slopes={}
for kind in ['vector_total','rotational','divergent','scalar_uv_total']:
    idx=np.arange(10,21);layer_slopes[kind]=float(np.polyfit(np.log(idx),np.log(layer.sel(kind=kind).values[idx]),1)[0])
summary={'status':'DESCRIPTIVE_COMPARISON','job_id':os.environ.get('SLURM_JOB_ID'),'degrees':[1,59],'minimum_nominal_wavelength_km':float(2*np.pi*RADIUS/59/1000),'slopes':slopes,'n2':low,'historical_layer_slopes_10_20':layer_slopes,'historical_amplitude_comparison':'Not performed: no digitized historical ordinates. Shape guides are normalized to ERA5.','layer_averaging':'Pressure-weighted mean of spectral energies, endpoints linearly interpolated at 92 and 353 hPa; not an exact reconstruction of original model-level quadrature.'}
(OUT/'energy_content_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=['# Kinetic-energy content versus spherical-harmonic degree','','This companion analysis was added at the user’s request. It measures energy distribution and historical spectral shape; it does not measure nonlinear energy flux.','','## ERA5 results','','![Degree spectra](energy_degree_spectra.png)','','| Level | Season | Degree range | Total-KE slope | 95% year-bootstrap interval |','|---|---|---|---:|---|']
for r in slopes:
    lines.append(f"| {r['level']} hPa | {r['season']} | {r['range'][0]}–{r['range'][1]} | {r['slope']:.3f} | [{r['year_bootstrap_95'][0]:.3f}, {r['year_bootstrap_95'][1]:.3f}] |")
lines+=['','Bootstrap intervals resample the 44 complete calendar-year spectra (1,000 replicates). They describe year-to-year sampling variability; reanalysis, resolution and spectral-model uncertainty are additional. See energy_degree_spectra.csv for numerical spectra.','','![Low-degree decomposition](energy_degree_decomposition.png)','','| Level | Season | E₁ | E₂ | E₃ | n=2 below both neighbors? | n=2 mean-flow fraction | n=2 divergent fraction |','|---|---|---:|---:|---:|---|---:|---:|']
for r in low:
    lines.append(f"| {r['level']} | {r['season']} | {r['E1']:.3f} | {r['E2']:.3f} | {r['E3']:.3f} | {r['n2_below_neighbors']} | {r['n2_stationary_fraction']:.1%} | {r['n2_divergent_fraction']:.1%} |")
lines+=['','Energies are m² s⁻² per degree, summed over all orders. Mean-flow energy is the energy of the long-term coefficient mean over the stated months. Transient energy is the remaining mean energy, not a frequency-filtered wave band.','','## Historical comparisons','','| Benchmark | Published observation | Comparison and limits |','|---|---|---|','| [Boer & Shepherd (1983)](https://journals.ametsoc.org/view/journals/atsc/40/1/1520-0469_1983_040_0164_lstdti_2_0_co_2.xml) | FGGE spectra distinguish a stationary, seasonally sensitive low-degree regime from a more transient high-degree regime. | Compare the low-degree partition and January/winter versus July/summer behavior qualitatively. Our seasonal 44-year means and pressure-level sampling differ; no original FGGE ordinates were recovered. |','| [Nastrom & Gage (1985)](https://doi.org/10.1175/1520-0469(1985)042%3C0950:ACOAWS%3E2.0.CO;2) | Aircraft along-track spectra approach −3 at large scales and −5/3 below approximately 300–400 km. | Compare resolved synoptic-range shape. Along-track spectra differ from global degree spectra; amplitudes are not directly equated. |','| [Koshyk & Hamilton (2001), Fig. 4](https://www.gfdl.noaa.gov/bibliography/related_files/koshyk0101.pdf) | UKMO assimilated winds: five Julys, 1993–1997; 92–353 hPa; T30. Approximate −3 total-KE behavior at n=10–20, with a steeper drop beyond n≈20. | ERA5 uses matching years, month and approximate layer, at 00/12 UTC. The original vertical discretization is not replicated. Published digital ordinates were not retrieved, so reference lines are slope guides normalized to ERA5, not historical measured amplitudes. |','','![Historical context](historical_degree_comparison.png)','','The ERA5 matched-window n=10–20 slopes are: '+', '.join(f'{k}: {v:.3f}' for k,v in layer_slopes.items())+'.','','The scalar u,v expansion and vector/vorticity-divergence spectrum assign energy differently among the lowest degrees. Their distinction is particularly important when discussing n=2 (see the appendix of Koshyk & Hamilton). The physical energy definition used for the project is the vector one.','','## Resolved scales and interpretation','','With n≤59, the shortest nominal wavelength 2πa/n is about 678 km. The aircraft mesoscale −5/3 range is outside this dataset’s resolved range; the analysis cannot test that transition. Conservative regridding may affect the upper part of the retained spectrum. A −3 slope alone does not establish an enstrophy cascade, and neither a low-degree minimum nor a mean-flow fraction establishes condensation.','','The strict individual-coefficient resolution check remains failed as documented in STAGE1_REPORT.md. All energy comparisons are descriptive. Raw historical amplitudes were not digitized; the comparison supplies published shape/scale benchmarks and a matched ERA5 sample, rather than an amplitude validation.']
(OUT/'SPECTRAL_CONTENT_REPORT.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'slopes':slopes,'n2':low,'historical_layer_slopes_10_20':layer_slopes}),flush=True)
