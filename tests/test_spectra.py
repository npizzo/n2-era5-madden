import numpy as np
from analyze_stage1 import segments
from n2tools import deseason


def test_seasons_do_not_join_years():
    t=np.arange(np.datetime64('2000-01-01'),np.datetime64('2003-01-01'),np.timedelta64(6,'h'))
    values=np.exp(2j*np.pi*np.arange(len(t))*.25/5)
    f,p,dof,count=segments(t,values,'DJF',64)
    assert 1 <= count <= 6
    assert abs(f[np.argmax(p)]-.2)<1/64
    assert dof>0


def test_deseason_uses_actual_times():
    time=np.arange(np.datetime64('2000-01-01'),np.datetime64('2004-01-01'),np.timedelta64(6,'h'))
    t=(time-np.datetime64('2000-01-01'))/np.timedelta64(1,'D')
    x=2+3j+(2-1j)*np.cos(2*np.pi*t/365.2425)+(1+2j)*np.sin(8*np.pi*t/365.2425)
    assert np.max(abs(deseason(time,x)))<1e-12
