import numpy as np
import pyshtools as sh
import xarray as xr
from scipy.signal import welch
from n2tools import grid_to_cilm, complex_coeffs, energy_closure, RADIUS, inverse_laplacian


def fixture_coeffs(L=21):
    rng=np.random.default_rng(431)
    c=rng.normal(size=(2,L+1,L+1))*1e-6
    for n in range(L+1):
        c[:,n,n+1:]=0
    c[1,:,0]=0
    c[:,0,:]=0
    return c


def test_roundtrip_and_orientation():
    c=fixture_coeffs()
    g=sh.expand.MakeGridDH(c,lmax=59,sampling=2,norm=1,csphase=1,extend=True)[:,:-1]
    field=xr.DataArray(g[::-1],dims=['latitude','longitude'],coords={'latitude':np.linspace(-90,90,121),'longitude':np.arange(240)*1.5})
    got=grid_to_cilm(field,lmax=21)
    assert np.max(np.abs(got-c))/np.max(np.abs(c)) < 2e-13


def test_energy_closure():
    c=fixture_coeffs()
    assert energy_closure(c,.31*c) < 1e-12


def test_solid_body_rotation():
    omega=1e-5
    lat=np.linspace(-90,90,121)
    g=2*omega*np.sin(np.deg2rad(lat))[:,None]*np.ones((1,240))
    c=grid_to_cilm(xr.DataArray(g,dims=['latitude','longitude'],coords={'latitude':lat,'longitude':np.arange(240)*1.5}))
    np.testing.assert_allclose(np.sqrt(3)/2*c[0,1,0],omega,rtol=1e-12)
    np.testing.assert_allclose(inverse_laplacian(c)[0,1,0],-RADIUS**2*c[0,1,0]/2)


def test_physical_westward_wave_fft_sign():
    # A moving spatial field sampled independently of the FFT convention.
    t=np.arange(1024)*.25
    lon=np.deg2rad(np.arange(240)*1.5)
    phi=-2*np.pi*t/5
    g=np.cos(lon[None,:]-phi[:,None])
    C=2*np.mean(g*np.cos(lon),axis=1)
    S=2*np.mean(g*np.sin(lon),axis=1)
    f,p=welch(C-1j*S,fs=4,nperseg=512,return_onesided=False)
    assert abs(f[np.argmax(p)]-.2)<1/128
    assert p[f>0].sum()>1000*p[f<0].sum()
