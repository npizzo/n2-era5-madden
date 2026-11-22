"""Degree-resolved correlations; positive RH omega removes westward propagation."""
import numpy as np
from scipy.fft import next_fast_len
from scipy.optimize import minimize, minimize_scalar
from n2tools import OMEGA


def lag_products(x, maxlag):
    """Linear sum x[t] conj(x[t-lag]), and later-time energy, per order."""
    x=np.asarray(x,dtype=np.complex128)
    length=len(x); k=min(maxlag,length-1)
    f=np.fft.fft(x,n=next_fast_len(2*length-1),axis=0)
    q=np.fft.ifft(f*f.conj(),axis=0)[:k+1]
    energy=np.abs(x)**2
    tail=energy.sum(axis=0)-np.vstack([np.zeros((1,x.shape[1])),np.cumsum(energy,axis=0)[:k]])
    out=np.zeros((maxlag+1,x.shape[1]),complex); den=np.zeros_like(out.real)
    out[:k+1]=q; den[:k+1]=tail
    return out,den


def rotate_products(q,n,dt=.25,sign=1):
    lag=np.arange(len(q))*dt*86400
    m=np.arange(q.shape[1])
    return (q*np.exp(-1j*sign*2*OMEGA/(n*(n+1))*lag[:,None]*m)).real


def ratio(num,den):
    return np.divide(num,den,out=np.full_like(num,np.nan,dtype=float),where=den>0)


def fit_collapse(c,lags,tmax=10,free_a=False,degrees=(3,4,5)):
    """Anchor to n=3: compare (n/3)^a Cn((n/3)^b T) to C3(T).

    Degree 2 never participates. For normalized correlations a=0 is the
    required zero-lag normalization; free_a is a secondary relaxation.
    """
    degrees=tuple(n for n in degrees if n!=3)
    last=min(lags[np.flatnonzero(np.isfinite(c[n]))[-1]] for n in (2,3,*degrees))
    lower=max(-3.,np.log(last/tmax)/np.log(2/3))
    upper=min(3.,np.log(last/tmax)/np.log(max(degrees)/3))
    t=np.linspace(0,tmax,81); reference=np.interp(t,lags,c[3])
    def loss(a,b):
        curves=np.array([(n/3)**a*np.interp((n/3)**b*t,lags,c[n]) for n in degrees])
        return float(np.mean((curves-reference)**2))
    bs=np.linspace(lower,upper,121); costs=np.array([loss(0,b) for b in bs]); i=int(np.argmin(costs))
    opt=minimize_scalar(lambda b:loss(0,b),bounds=(bs[max(0,i-1)],bs[min(120,i+1)]),method='bounded')
    a,b=0.,float(opt.x)
    if free_a:
        fits=[minimize(lambda v:loss(*v),[0,np.clip(seed,lower,upper)],bounds=[(-2,2),(lower,upper)],method='L-BFGS-B') for seed in (b,-2,0,2)]
        best=min(fits,key=lambda v:v.fun);a,b=map(float,best.x)
    curve2=(2/3)**a*np.interp((2/3)**b*t,lags,c[2])
    score=float(np.trapezoid(curve2-reference,t)/tmax)
    return {'a':a,'b':b,'mse':loss(a,b),'unscaled_mse':loss(0,0),
            'n2_mean_excess':score,'at_bound':bool(b<lower+.02 or b>upper-.02 or abs(a)>1.98),'b_bounds':[lower,upper],
            'fit_degrees':[3,*degrees],'fit_window_days_at_n3':tmax}


def crossing_time(c,lags,threshold):
    ids=np.flatnonzero(c<=threshold)
    if not len(ids):return None
    k=int(ids[0])
    if k==0:return 0.
    return float(lags[k-1]+(lags[k]-lags[k-1])*(c[k-1]-threshold)/(c[k-1]-c[k]))
