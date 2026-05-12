import os
import traceback
os.chdir(r'd:\MESTRADO\1º Ano\2º Semestre\VAD\VAD_project')
try:
    import dashboard_principal as dp
    print('loaded')
    out = dp.update_dashboard(None, None)
    print('success', type(out), len(out) if hasattr(out, '__len__') else 'nolen')
except Exception:
    traceback.print_exc()
