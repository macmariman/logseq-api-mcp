try:
    import lancedb  # noqa: F401
    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False
