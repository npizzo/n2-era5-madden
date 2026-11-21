"""Stream public WB2 grids on Unity, saving portable split-complex NetCDF."""
import argparse
import json
import os
import platform
import time
from pathlib import Path
import numpy as np
import xarray as xr
from n2tools import STORE, grid_to_cilm, complex_coeffs, ke_spectrum


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--year',type=int,required=True)
    p.add_argument('--levels',type=int,nargs='+',default=[300,500])
    p.add_argument('--lmax',type=int,default=59)
    p.add_argument('--keep',type=int,default=21)
    p.add_argument('--limit',type=int,default=0,help='Pilot only: first N timestamps')
    p.add_argument('--block',type=int,default=200)
    p.add_argument('--store',default=STORE)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if not 1 <= args.keep <= args.lmax:
        p.error('require 1 <= keep <= lmax')
    args.out.mkdir(parents=True,exist_ok=True)
    suffix='_pilot' if args.limit else ''
    out=args.out/f'coeffs_{args.year}{suffix}.nc'
    if out.exists():
        raise FileExistsError(out)
    started=time.monotonic()
    ds=xr.open_zarr(args.store,storage_options={'token':'anon'},consolidated=True)
    z=ds.vorticity.sel(time=slice(f'{args.year}-01-01',f'{args.year}-12-31T23:59:59'),level=args.levels)
    expected=(np.datetime64(f'{args.year+1}-01-01')-np.datetime64(f'{args.year}-01-01'))/np.timedelta64(6,'h')
    if z.sizes['time'] != int(expected):
        raise ValueError('Year incomplete')
    if args.limit:
        z=z.isel(time=slice(0,args.limit))
    times=z.time.values
    if not np.all(np.diff(times)==np.timedelta64(6,'h')):
        raise ValueError('Not a continuous six-hourly record')
    count=len(times)
    coefficients=np.zeros((count,len(args.levels),args.keep+1,args.keep+1),dtype=np.complex64)
    energy=np.zeros((count,len(args.levels),args.lmax+1))
    for start in range(0,count,args.block):
        block=z.isel(time=slice(start,min(start+args.block,count))).load()
        for ti in range(block.sizes['time']):
            for li in range(len(args.levels)):
                c=grid_to_cilm(block.isel(time=ti,level=li),args.lmax)
                coefficients[start+ti,li]=complex_coeffs(c)[:args.keep+1,:args.keep+1]
                energy[start+ti,li]=ke_spectrum(c)
        print(json.dumps({'completed':start+block.sizes['time'],'total':count,'seconds':time.monotonic()-started}),flush=True)
    result=xr.Dataset({'zeta_real':(('time','level','n','m'),coefficients.real),
        'zeta_imag':(('time','level','n','m'),coefficients.imag),
        'ke_rot':(('time','level','nk'),energy)},
        coords={'time':times,'level':args.levels,'n':np.arange(args.keep+1),'m':np.arange(args.keep+1),'nk':np.arange(args.lmax+1)},
        attrs={'source':args.store,'normalization':'4pi, csphase=1','complex_convention':'a=C-iS; westward positive FFT frequency',
               'job_id':os.environ.get('SLURM_JOB_ID','unknown'),'node':platform.node(),'elapsed_seconds':time.monotonic()-started,
               'pilot':int(bool(args.limit)),'lmax':args.lmax})
    for name in ['zeta_real','zeta_imag']:
        result[name].attrs['units']='s-1'
    result.ke_rot.attrs['units']='m2 s-2'
    result.level.attrs['units']='hPa'
    temporary=Path(str(out)+'.part')
    result.to_netcdf(temporary,encoding={v:{'zlib':True,'complevel':4} for v in result.data_vars})
    temporary.replace(out)
    print(f'SAVED {out}',flush=True)

if __name__=='__main__':
    main()
