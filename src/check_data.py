"""Real-data checks; distinct numerical and resolution diagnostics."""
import json
import os
from pathlib import Path
import numpy as np
import xarray as xr
from n2tools import STORE, STORE_FINE, grid_to_cilm, energy_closure

out=Path('results');out.mkdir(exist_ok=True)
a=xr.open_zarr(STORE,storage_options={'token':'anon'},consolidated=True)
b=xr.open_zarr(STORE_FINE,storage_options={'token':'anon'},consolidated=True)
summary={'job_id':os.environ.get('SLURM_JOB_ID'),'checks':[],'stores':[STORE,STORE_FINE]}
# Ten dates spanning seasons and years, at both requested levels.
dates=['1979-01-15','1984-04-15','1989-07-15','1994-10-15','1999-01-15','2004-04-15','2009-07-15','2014-10-15','2019-01-15','2022-07-15']
for date in dates:
    low=a[['vorticity','divergence']].sel(time=date+'T00:00:00',level=[300,500]).load()
    high=b.vorticity.sel(time=date+'T00:00:00',level=[300,500]).load()
    for level in [300,500]:
        c=grid_to_cilm(low.vorticity.sel(level=level))
        d=grid_to_cilm(low.divergence.sel(level=level))
        fine=grid_to_cilm(high.sel(level=level),lmax=21)
        coarse=c[:,:22,:22]
        rel=float(np.linalg.norm(coarse-fine)/np.linalg.norm(fine))
        degree=[float(np.linalg.norm(coarse[:,n,:n+1]-fine[:,n,:n+1])/max(np.linalg.norm(fine[:,n,:n+1]),1e-30)) for n in range(1,22)]
        row={'date':date,'level':level,'energy_closure_relative':energy_closure(c,d),'resolution_relative_l2':rel,'resolution_by_degree':degree,'zeta10':float(c[0,1,0])}
        summary['checks'].append(row)
        print(json.dumps(row),flush=True)
summary['energy_pass']=all(x['energy_closure_relative']<1e-6 for x in summary['checks'])
summary['resolution_l2_within_one_percent']=all(x['resolution_relative_l2']<=.01 for x in summary['checks'])
summary['resolution_all_degrees_within_one_percent']=all(max(x['resolution_by_degree'])<=.01 for x in summary['checks'])
summary['note']='Closure uses reconstructed bandlimited winds and oversampled quadrature, not raw ERA5 u/v. Resolution differences include conservative regridding and near-zero modes; inspect by degree. Orientation climatology is checked by the full analysis.'
(out/'data_checks.json').write_text(json.dumps(summary,indent=2)+'\n')
if not summary['energy_pass']:
    raise RuntimeError('Energy closure failed')
