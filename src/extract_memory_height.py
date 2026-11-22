"""Extract actual 500 hPa geopotential height, separately from streamfunction."""
import argparse,json,os,time
from pathlib import Path
import numpy as np
import xarray as xr
from n2tools import STORE,grid_to_cilm,complex_coeffs

def main():
    p=argparse.ArgumentParser();p.add_argument('--year',type=int,required=True)
    p.add_argument('--limit',type=int,default=0);p.add_argument('--store',default=STORE)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    out=a.out/f'height_{a.year}{"_pilot" if a.limit else ""}.nc'
    if out.exists():raise FileExistsError(out)
    ds=xr.open_zarr(a.store,storage_options={'token':'anon'},consolidated=True)
    field=ds.geopotential.sel(level=500,time=slice(f'{a.year}-01-01',f'{a.year}-12-31T23:59:59'))
    units=field.attrs.get('units','');print(json.dumps({'units':units,'variable':'geopotential','dims':dict(field.sizes)}),flush=True)
    if units not in ('m**2 s**-2','m2 s-2','m^2 s^-2','m2/s2'):raise ValueError(f'Unexpected geopotential units: {units}')
    expected=int((np.datetime64(f'{a.year+1}-01-01')-np.datetime64(f'{a.year}-01-01'))/np.timedelta64(6,'h'))
    if field.sizes['time']!=expected:raise ValueError('Incomplete year')
    if a.limit:field=field.isel(time=slice(0,a.limit))
    times=field.time.values
    if not np.all(np.diff(times)==np.timedelta64(6,'h')):raise ValueError('Cadence mismatch')
    coeff=np.zeros((len(times),11,11),complex);start=time.monotonic()
    for j in range(0,len(times),200):
        block=(field.isel(time=slice(j,j+200))/9.80665).load()
        for k in range(len(block.time)):coeff[j+k]=complex_coeffs(grid_to_cilm(block.isel(time=k),lmax=10))
        print(json.dumps({'completed':j+len(block.time),'total':len(times),'seconds':time.monotonic()-start}),flush=True)
    result=xr.Dataset({'height_real':(('time','n','m'),coeff.real),'height_imag':(('time','n','m'),coeff.imag)},coords={'time':times,'n':np.arange(11),'m':np.arange(11)},attrs={'source':a.store,'units':'m','pressure_hPa':500,'geopotential_to_height_g':9.80665,'normalization':'4pi csphase=1; a=C-iS','retained_degree':10,'job_id':os.environ.get('SLURM_JOB_ID','unknown')})
    result.to_netcdf(str(out)+'.part',encoding={v:{'zlib':True,'complevel':4} for v in result.data_vars})
    Path(str(out)+'.part').replace(out)
    print('SAVED',out,flush=True)
if __name__=='__main__':main()
