"""Python startup hook for optional application observability."""

try:
    from packages.observability import configure_observability

    configure_observability()
except Exception:
    # Observability must never prevent the commerce process from starting.
    pass
