"""ERA5 July 1993–1997, matching the UKMO comparison window in KH2001.

Pressure-weighted 92–353 hPa layer means use linearly interpolated spectral
energies at endpoints. Original model-level averaging is not exactly recreated.
"""
import json
import os
from pathlib import Path
import numpy as np
import xarray as xr
from n2tools import STORE, grid_to_cilm, ke_spectrum
out=Path('data/energy/historical_window.nc');out.parent.mkdir(exist_ok=True,parents=True)
if out.exists():
    raise FileExistsError(out)
ds=xr.open_zarr(STORE,storage_options={'token':'anon'},consolidated=True)
variables=['vorticity','divergence','u_component_of_wind','v_component_of_wind']
levels=[50,100,150,200,250,300,400,500]
energies=np.zeros((5,len(levels),4,60))
counts=[]
for yi,year in enumerate(range(1993,1998)):
    d=ds[variables].sel(time=slice(f'{year}-07-01',f'{year}-07-31T23:59:59'),level=levels).isel(time=slice(None,None,2))
    if len(d.time)!=62 or not np.isin(d.time.dt.hour,[0,12]).all():
        raise ValueError('Need 62 twice-daily July samples')
    counts.append(len(d.time))
    for start in range(0,len(d.time),16):
        block=d.isel(time=slice(start,start+16)).load()
        for ti in range(block.sizes['time']):
            for li in range(len(levels)):
                z,div,u,v=[grid_to_cilm(block[name].isel(time=ti,level=li)) for name in variables]
                er,ed=ke_spectrum(z),ke_spectrum(div)
                # Direct scalar expansion of u,v is an alternative scale attribution.
                escalar=.5*np.sum(u*u+v*v,axis=(0,2))
                energies[yi,li]+=np.stack([er,ed,er+ed,escalar])
        print(f'{year}: {start+len(block.time)}/62',flush=True)
    energies[yi]/=len(d.time)
result=xr.Dataset({'energy':(('year','level','kind','n'),energies)},coords={'year':np.arange(1993,1998),'level':levels,'kind':['rotational','divergent','vector_total','scalar_uv_total'],'n':np.arange(60)},attrs={'source':STORE,'job_id':os.environ.get('SLURM_JOB_ID','unknown'),'time_sampling':'00 and 12 UTC, July 1993–1997','units':'m2 s-2','normalization':'real 4pi csphase=1'})
result.to_netcdf(str(out)+'.part');Path(str(out)+'.part').replace(out)
print(f'SAVED {out}',flush=True)
