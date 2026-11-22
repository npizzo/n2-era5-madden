import numpy as np
from memory_orders import decompose
from memory_tools import lag_products,rotate_products

def test_unequal_variance_opposing_covariance_budget():
    pairs=np.array([100.,80.,60.])
    cov=np.array([[9.,1.],[4.5,-.8],[1.8,-.5]])
    energy=np.array([[9.,1.],[8.,2.],[6.,4.]])
    out=decompose(cov*pairs[:,None],energy*pairs[:,None],pairs)
    np.testing.assert_allclose(out['variance_fraction'],[.9,.1])
    np.testing.assert_allclose(out['fixed_contribution'].sum(axis=1),[1,.37,.13])
    np.testing.assert_allclose(out['own_correlation'][1],[.5625,-.4])
    np.testing.assert_allclose(out['prior_contribution'].sum(axis=1),cov.sum(axis=1)/energy.sum(axis=1))
    assert out['fixed_contribution'][1,0] > out['fixed_contribution'][1].sum()

def test_order_budget_matches_direct_products_and_pair_counts():
    rng=np.random.default_rng(73);x=rng.normal(size=(93,3))+1j*rng.normal(size=(93,3));x[:,0]=x[:,0].real
    q,d=lag_products(x,30);out=decompose(rotate_products(q,2),d,len(x)-np.arange(31))
    for lag in [0,3,19,30]:
        direct=np.mean(x[lag:,0]*x[:len(x)-lag,0].conj()).real
        np.testing.assert_allclose(out['covariance'][lag,0],direct,atol=1e-12)
    np.testing.assert_allclose(out['fixed_contribution'][0].sum(),1,atol=1e-12)
