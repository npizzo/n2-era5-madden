"""Compare a complete year at 1.5° and 1°, without certifying the full record."""
import json
from pathlib import Path
import numpy as np
import xarray as xr
from scipy.signal import welch
from n2tools import deseason
with xr.open_dataset('data/stage1/coeffs_1979.nc') as a, xr.open_dataset('data/resolution1deg/coeffs_1979.nc') as b:
    np.testing.assert_array_equal(a.time.values,b.time.values)
    rows=[]
    for level in [300,500]:
        for m,n in [(0,1),(0,2),(1,2),(2,2),(1,3),(1,4),(2,3),(3,3)]:
            x=(a.zeta_real+1j*a.zeta_imag).sel(level=level,n=n,m=m).values.astype(complex)
            y=(b.zeta_real+1j*b.zeta_imag).sel(level=level,n=n,m=m).values.astype(complex)
            rms=float(np.linalg.norm(x-y)/np.linalg.norm(y))
            x=deseason(a.time.values,x);y=deseason(b.time.values,y)
            f,px=welch(x,fs=4,window='hann',nperseg=512,noverlap=256,detrend=False,return_onesided=False)
            _,py=welch(y,fs=4,window='hann',nperseg=512,noverlap=256,detrend=False,return_onesided=False)
            band=(f>=1/40)&(f<=1/1.5)
            rel=float(np.linalg.norm(px[band]-py[band])/np.linalg.norm(py[band]))
            rows.append({'level':level,'m':m,'n':n,'coefficient_relative_rms':rms,'westward_psd_relative_l2':rel})
    summary={'year':1979,'rows':rows,'note':'One-year sensitivity check. This cannot establish all-year convergence. Seasonal fit and spectral power can be unstable for weak modes.'}
    Path('results/resolution_year.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary),flush=True)
