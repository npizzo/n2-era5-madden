import numpy as np
from memory_utc_control import remove_utc_cycle

def test_removes_repeating_cycle_preserving_monthly_background():
    time=np.arange(np.datetime64('2000-01-01'),np.datetime64('2000-03-01'),np.timedelta64(6,'h'))
    month=time.astype('datetime64[M]').astype(int)%12+1
    hour=time.astype('datetime64[h]').astype(int)%24
    background=month[:,None,None]*np.ones((1,3,3))
    tide=(3*np.cos(2*np.pi*hour/24)+2j*np.cos(4*np.pi*hour/24))[:,None,None]
    cleaned,removed=remove_utc_cycle(time,background+tide)
    np.testing.assert_allclose(cleaned,background,atol=1e-13)
    for m in (1,2):np.testing.assert_allclose(removed[month==m].mean(axis=0),0,atol=1e-13)
