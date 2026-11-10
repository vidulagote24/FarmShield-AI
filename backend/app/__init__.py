"""FarmShield AI Backend Application Package."""

import sys
import types
from importlib.machinery import ModuleSpec

__version__ = "1.0.0"


class _ExistingLoader:
    def __init__(self, mod):
        self.mod = mod

    def create_module(self, spec):
        return self.mod

    def exec_module(self, module):
        pass


class _BackendAppAliasHook:
    """Redirect legacy and cross-module 'backend.app' imports to 'app' to prevent module duality and class mismatch."""

    def find_spec(self, fullname: str, path=None, target=None):
        if fullname == "backend":
            mod = sys.modules.get("backend") or types.ModuleType("backend")
            return ModuleSpec("backend", _ExistingLoader(mod), is_package=True)
        if fullname == "backend.app":
            import app
            return ModuleSpec("backend.app", _ExistingLoader(app), is_package=True)
        if fullname.startswith("backend.app."):
            actual_name = fullname[len("backend."):]
            __import__(actual_name)
            target_mod = sys.modules[actual_name]
            is_pkg = hasattr(target_mod, "__path__")
            return ModuleSpec(fullname, _ExistingLoader(target_mod), is_package=is_pkg)
        return None


if not any(isinstance(h, _BackendAppAliasHook) for h in sys.meta_path):
    sys.meta_path.insert(0, _BackendAppAliasHook())
