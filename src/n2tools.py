"""4π real harmonics, csphase=1; a=C-iS; eastward longitude."""
import numpy as np
import pyshtools as sh

RADIUS = 6.371e6
OMEGA = 7.2921e-5
STORE = 'gs://weatherbench2/datasets/era5/1959-2023_01_10-6h-240x121_equiangular_with_poles_conservative.zarr'
STORE_FINE = STORE.replace('240x121', '360x181')


def grid_to_cilm(field, lmax=59):
    field = field.transpose('latitude', 'longitude').sortby('latitude', ascending=False).sortby('longitude')
    lat, lon = field.latitude.values, field.longitude.values
    n = len(lat) - 1
    if n % 2 or len(lon) != 2*n:
        raise ValueError('Expected DH grid including both poles, nlon=2*(nlat-1)')
    np.testing.assert_allclose(lat, np.linspace(90, -90, n+1), atol=1e-8)
    np.testing.assert_allclose(lon, np.arange(2*n)*180/n, atol=1e-8)
    if lmax > n//2-1:
        raise ValueError('Requested degree exceeds grid bandwidth')
    grid = np.asarray(field.values[:-1], dtype=np.float64)
    if not np.isfinite(grid).all():
        raise ValueError('Missing/nonfinite grid data')
    return sh.expand.SHExpandDH(grid, norm=1, sampling=2, csphase=1, lmax_calc=lmax)


def complex_coeffs(cilm):
    return cilm[0] - 1j*cilm[1]


def inverse_laplacian(cilm):
    n = np.arange(cilm.shape[1])
    factor = np.zeros_like(n, dtype=float)
    factor[1:] = -RADIUS**2/(n[1:]*(n[1:]+1))
    return cilm * factor[None, :, None]


def ke_spectrum(vorticity, divergence=None):
    n = np.arange(vorticity.shape[1])
    power = np.sum(vorticity**2, axis=(0, 2))
    if divergence is not None:
        power += np.sum(divergence**2, axis=(0, 2))
    energy = np.zeros_like(power)
    energy[1:] = .5*RADIUS**2*power[1:]/(n[1:]*(n[1:]+1))
    return energy


def energy_closure(vorticity, divergence):
    # Oversample products to integrate the bandlimited reconstructed wind exactly.
    L = vorticity.shape[1]-1
    pt, pp = sh.expand.MakeGradientDH(inverse_laplacian(vorticity), lmax=2*L+1, sampling=2, radius=RADIUS)
    ct, cp = sh.expand.MakeGradientDH(inverse_laplacian(divergence), lmax=2*L+1, sampling=2, radius=RADIUS)
    u, v = pt+cp, pp-ct
    grid_energy = sh.expand.SHExpandDH(.5*(u*u+v*v), norm=1, sampling=2, csphase=1, lmax_calc=0)[0,0,0]
    spectral_energy = ke_spectrum(vorticity, divergence).sum()
    return float(abs(grid_energy-spectral_energy)/spectral_energy)


def deseason(time, values):
    t = (np.asarray(time)-np.datetime64('2000-01-01'))/np.timedelta64(1,'D')
    X = np.column_stack([np.ones(len(t))] + [f(2*np.pi*k*t/365.2425) for k in range(1,5) for f in (np.cos,np.sin)])
    return values-X@np.linalg.lstsq(X, values, rcond=None)[0]
