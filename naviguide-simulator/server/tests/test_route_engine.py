import pytest

from route_engine import searoute_with_exact_end


def test_short_offshore_leg():
    # La Rochelle → ~20 nm au large (ouest)
    route = searoute_with_exact_end((-1.167, 46.1541), (-1.7, 46.25))
    assert route is not None
    coords = route["geometry"]["coordinates"]
    assert len(coords) >= 2
