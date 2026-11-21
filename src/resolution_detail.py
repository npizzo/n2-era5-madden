"""Resolve degree-aggregated differences into target-mode differences."""
import json
import os
from pathlib import Path
import numpy as np
import xarray as xr
from n2tools import STORE, STORE_FINE, grid_to_cilm, complex_coeffs
checks=json.loads(Path('results/data_checks.json').read_text())['checks']
a=xr.open_zarr(STORE,storage_options={'token':'anon'},consolidated=True)
b=xr.open_zarr(STORE_FINE,storage_options={'token':'anon'},consolidated=True)
rows=[]
for date in sorted(set(r['date'] for r in checks)):
    low=a.vorticity.sel(time=date+'T00:00:00',level=[300,500]).load()
    high=b.vorticity.sel(time=date+'T00:00:00',level=[300,500]).load()
    for level in [300,500]:
        c=complex_coeffs(grid_to_cilm(low.sel(level=level),21))
        d=complex_coeffs(grid_to_cilm(high.sel(level=level),21))
        for m,n in [(0,1),(0,2),(1,2),(2,2),(1,3),(1,4),(2,3),(3,3)]:
            rows.append({'date':date,'level':level,'m':m,'n':n,'coarse_abs':float(abs(c[n,m])),'fine_abs':float(abs(d[n,m])),'absolute_difference':float(abs(c[n,m]-d[n,m])),'relative_difference':float(abs(c[n,m]-d[n,m])/max(abs(d[n,m]),1e-30))})
summary={'job_id':os.environ.get('SLURM_JOB_ID'),'rows':rows,'max_madden_mode_relative':max(r['relative_difference'] for r in rows if (r['m'],r['n']) in [(1,2),(1,3),(1,4),(2,3),(3,3)])}
Path('results/resolution_detail.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='rows'}),flush=True)
