"""Opt-in import compatibility for libraries written against Textual."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from importlib import import_module
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from importlib.util import find_spec, spec_from_loader
from types import ModuleType

__all__ = ["alias_textual"]


class _AliasLoader(Loader):
    def __init__(self, canonical_name: str) -> None:
        self._canonical_name = canonical_name
        self._canonical_spec: ModuleSpec | None = None

    def create_module(self, spec: ModuleSpec) -> ModuleType:
        module = import_module(self._canonical_name)
        self._canonical_spec = module.__spec__
        return module

    def exec_module(self, module: ModuleType) -> None:
        # module_from_spec sets __spec__ even for an existing module returned
        # by create_module. Keep reloads and resource lookups canonical.
        module.__spec__ = self._canonical_spec


class _TextualAliasFinder(MetaPathFinder):
    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        if not fullname.startswith("textual."):
            return None
        canonical_name = "anytext" + fullname[len("textual") :]
        canonical_spec = find_spec(canonical_name)
        if canonical_spec is None:
            return None
        return spec_from_loader(
            fullname,
            _AliasLoader(canonical_name),
            is_package=canonical_spec.submodule_search_locations is not None,
        )


def alias_textual() -> None:
    """Route ``textual`` imports to the corresponding Anytext modules.

    Call this once at application startup, before importing any library that
    imports Textual. Repeated calls are harmless. Already imported Anytext
    modules are supported, but loading the real Textual first raises
    ``RuntimeError`` rather than mixing two framework implementations.

    Both import names share the same module objects, classes, and app contexts.
    Canonical module metadata and the Anytext version are preserved. This is a
    process-wide import alias; it does not alter installed distribution metadata,
    dependency resolution, command-line entry points, or environment settings.
    """
    conflicts = []
    for name, module in tuple(sys.modules.items()):
        if name == "textual" or name.startswith("textual."):
            canonical_name = "anytext" + name[len("textual") :]
            if module is None or module is not sys.modules.get(canonical_name):
                conflicts.append(name)
    if conflicts:
        names = ", ".join(sorted(conflicts)[:5])
        raise RuntimeError(
            "Cannot install Anytext as Textual because Textual modules are already "
            f"loaded: {names}. Call alias_textual() before importing Textual "
            "or libraries that import it."
        )

    # Public names renamed by the fork remain available after opting in.
    # Load these small modules now so imports through the package's existing
    # attributes work as well as imports handled by the alias finder.
    from anytext import errors, logging

    setattr(errors, "TextualError", errors.AnytextError)
    setattr(logging, "TextualHandler", logging.AnytextHandler)

    if not any(isinstance(finder, _TextualAliasFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _TextualAliasFinder())
    # Aliasing preloaded modules also supports direct sys.modules lookups and
    # avoids touching their metadata through the import machinery unnecessarily.
    for name, module in tuple(sys.modules.items()):
        if (name == "anytext" or name.startswith("anytext.")) and module is not None:
            sys.modules["textual" + name[len("anytext") :]] = module
