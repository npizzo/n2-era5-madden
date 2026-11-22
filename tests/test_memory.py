import numpy as np
import pyshtools as sh
from memory_tools import lag_products,rotate_products,ratio,fit_collapse
from n2tools import OMEGA

def test_fft_products_match_direct_without_wraparound():
    rng=np.random.default_rng(923);x=rng.normal(size=(87,4))+1j*rng.normal(size=(87,4))
    q,d=lag_products(x,100)
    for k in (0,1,20,86):
        np.testing.assert_allclose(q[k],np.sum(x[k:]*x[:len(x)-k].conj(),axis=0),atol=1e-12)
        np.testing.assert_allclose(d[k],np.sum(abs(x[k:])**2,axis=0),atol=1e-12)
    assert np.all(q[87:]==0) and np.all(d[87:]==0)

def test_westward_pattern_is_frozen_and_wrong_sign_is_not():
    n=3;t=np.arange(800)*21600;omega=2*OMEGA/(n*(n+1))
    x=np.zeros((len(t),n+1),complex)
    # Direct spatial cosine projected onto cosine/sine bases, not a prescribed coefficient phase.
    lon=np.linspace(0,2*np.pi,240,endpoint=False)
    field=np.cos(2*(lon[None,:]+omega*t[:,None]))
    x[:,2]=2*np.mean(field*np.cos(2*lon),axis=1)-2j*np.mean(field*np.sin(2*lon),axis=1)
    q,d=lag_products(x,80)
    c=ratio(rotate_products(q,n).sum(axis=1),d.sum(axis=1))
    np.testing.assert_allclose(c,1,atol=2e-13)
    assert np.min(ratio(rotate_products(q,n,sign=-1).sum(axis=1),d.sum(axis=1)))<-.9

def test_degree_inner_product_equals_area_integral():
    rng=np.random.default_rng(8);n=5
    c=np.zeros((2,n+1,n+1));d=c.copy()
    c[:,n,:]=rng.normal(size=(2,n+1));d[:,n,:]=rng.normal(size=(2,n+1))
    c[1,:,0]=0;d[1,:,0]=0
    g=sh.expand.MakeGridDH(c,lmax=2*n+1,sampling=2,norm=1,csphase=1)
    h=sh.expand.MakeGridDH(d,lmax=2*n+1,sampling=2,norm=1,csphase=1)
    inner=sh.expand.SHExpandDH(g*h,norm=1,sampling=2,csphase=1,lmax_calc=0)[0,0,0]
    np.testing.assert_allclose(inner,np.sum(c*d),atol=1e-12)

def test_known_time_collapse_and_held_out_n2():
    lag=np.arange(241)*.25;b=-1.2
    c=np.array([np.exp(-lag/(6*(max(n,1)/3)**b)) for n in range(11)])
    fit=fit_collapse(c,lag)
    assert abs(fit['b']-b)<.01 and abs(fit['n2_mean_excess'])<.001
    c[2]=np.exp(-lag/(12*(2/3)**b));second=fit_collapse(c,lag)
    assert second['b']==fit['b'] and second['n2_mean_excess']>.1

def test_zonal_rotation_invariance_and_zero_lag_normalization():
    rng=np.random.default_rng(37);x=rng.normal(size=(500,1))
    q,d=lag_products(x,100)
    np.testing.assert_allclose(rotate_products(q,2),q.real)
    assert abs(ratio(q.real.sum(axis=1),d.sum(axis=1))[0]-1)<1e-12
