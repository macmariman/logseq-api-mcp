"""Vector subsystem retraction guard (v1.0.1)."""

import importlib
import pytest


def test_src_vector_module_is_removed():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.vector")


def test_registry_does_not_reference_vector():
    src = open("src/registry.py").read()
    assert "vector" not in src.lower(), (
        "registry.py must not mention vector after v1.0.1 retraction"
    )
