"""ctypes calls a small opaque-context C adapter, never a Python detector."""
from dataclasses import dataclass
import ctypes as C
import hashlib
import math
import os
from pathlib import Path
import shutil
import subprocess
from . import ROOT

@dataclass(frozen=True)
class Health:
    score: int
    state: str
    flags: int

_lib = None

def library():
    global _lib
    if _lib is not None:
        return _lib
    core = ROOT/'vendor/SensorTrust/core'
    bridge = Path(__file__).with_name('trust_bridge.c')
    digest = hashlib.sha256(b''.join(p.read_bytes() for p in [bridge,core/'sensor_trust.c',core/'sensor_trust.h'])).hexdigest()[:16]
    out = ROOT/'build'/f'trust-{digest}.so'
    out.parent.mkdir(exist_ok=True)
    if not out.exists():
        compiler = shutil.which(os.environ.get('CC','cc'))
        if not compiler:
            raise RuntimeError('SensorTrust needs a C11 compiler: install cc/clang/gcc')
        temporary = out.with_suffix(f'.{os.getpid()}.tmp.so')
        subprocess.run([compiler,'-std=c11','-Wall','-Wextra','-Werror','-O2','-shared','-fPIC','-I',str(core),str(bridge),str(core/'sensor_trust.c'),'-lm','-o',str(temporary)],check=True)
        temporary.replace(out)
    lib = C.CDLL(str(out))
    lib.tais_new.argtypes = [C.c_float,C.c_float,C.c_float,C.c_int,C.c_float,C.c_int,C.c_float,C.c_int]
    lib.tais_new.restype = C.c_void_p
    lib.tais_free.argtypes = [C.c_void_p]
    lib.tais_update.argtypes = [C.c_void_p,C.c_float,C.c_int,C.c_uint64,C.POINTER(C.c_int),C.POINTER(C.c_int),C.POINTER(C.c_uint32)]
    _lib = lib
    return lib

class SensorTrust:
    def __init__(self, config):
        self.lib = library()
        self.ctx = self.lib.tais_new(*(config[k] for k in ['min_value','max_value','stuck_epsilon','stuck_window','spike_threshold','drift_window','drift_threshold','missing_limit']))
        if not self.ctx:
            raise ValueError('Invalid SensorTrust configuration')
        self.last_t = -1

    def update(self, t, value):
        if not math.isfinite(t) or t < 0 or t <= self.last_t:
            raise ValueError('SensorTrust timestamps must increase and be nonnegative')
        self.last_t = t
        valid = value is not None and math.isfinite(value)
        score,state,flags = C.c_int(),C.c_int(),C.c_uint32()
        self.lib.tais_update(self.ctx,float(value) if valid else 0.0,int(valid),round(t*1000),C.byref(score),C.byref(state),C.byref(flags))
        return Health(score.value,('HEALTHY','DEGRADED','FAULT')[state.value],flags.value)

    def close(self):
        if self.ctx:
            self.lib.tais_free(self.ctx)
            self.ctx = None

    def __del__(self):
        if getattr(self,'ctx',None):
            self.close()
