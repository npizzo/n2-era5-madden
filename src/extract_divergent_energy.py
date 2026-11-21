"""Add six-hourly divergent KE spectra without repeating vorticity extraction."""
import argparse
import os
import time
from pathlib import Path
import numpy as np
import xarray as xr
from n2tools import STORE, grid_to_cilm, ke_spectrum
p=argparse.ArgumentParser();p.add_argument('--year',type=int,required=True);a=p.parse_args()
out=Path(f'data/energy/divergent_{a.year}.nc');out.parent.mkdir(exist_ok=True,parents=True)
if out.exists():
    raise FileExistsError(out)
t0=time.monotonic()
ds=xr.open_zarr(STORE,storage_options={'token':'anon'},consolidated=True)
d=ds.divergence.sel(time=slice(f'{a.year}-01-01',f'{a.year}-12-31T23:59:59'),level=[300,500])
times=d.time.values
expected=int((np.datetime64(f'{a.year+1}-01-01')-np.datetime64(f'{a.year}-01-01'))/np.timedelta64(6,'h'))
if len(times)!=expected or not np.all(np.diff(times)==np.timedelta64(6,'h')):
    raise ValueError('Incomplete year')
E=np.zeros((len(times),2,60));sums=np.zeros((12,2,2,22,22));count=np.zeros(12,dtype=int)
months=d.time.dt.month.values-1
for start in range(0,len(times),200):
    block=d.isel(time=slice(start,start+200)).load()
    for ti in range(block.sizes['time']):
        month=months[start+ti];count[month]+=1
        for li in range(2):
            c=grid_to_cilm(block.isel(time=ti,level=li))
            E[start+ti,li]=ke_spectrum(c)
            sums[month,li]+=c[:,:22,:22]
    print(f'{a.year}: {start+len(block.time)}/{len(times)}',flush=True)
result=xr.Dataset({'ke_div':(('time','level','nk'),E),'monthly_sum_cilm':(('month','level','component','n','m'),sums),'monthly_count':('month',count)},coords={'time':times,'level':[300,500],'nk':np.arange(60),'month':np.arange(1,13),'component':['cos','sin'],'n':np.arange(22),'m':np.arange(22)},attrs={'source':STORE,'normalization':'4pi, csphase=1','job_id':os.environ.get('SLURM_JOB_ID','unknown'),'elapsed_seconds':time.monotonic()-t0})
result.ke_div.attrs['units']='m2 s-2'
result.to_netcdf(str(out)+'.part',encoding={v:{'zlib':True,'complevel':4} for v in result.data_vars})
Path(str(out)+'.part').replace(out)
print(f'SAVED {out}',flush=True)
