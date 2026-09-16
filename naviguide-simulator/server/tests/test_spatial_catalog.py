import pytest

from spatial_catalog import Bbox, SpatialCatalogIndex, parse_bbox


def point(lon, lat, **properties):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": properties,
    }


def test_index_filters_bbox_and_science_source_across_antimeridian():
    index = SpatialCatalogIndex("science", [
        point(175, 0, source="argo", name="Fidji Est"),
        point(-175, 0, source="argo", name="Fidji Ouest"),
        point(0, 0, source="sextant", name="Greenwich"),
    ])

    result = index.query(Bbox(170, -10, -170, 10), zoom=8, source="argo")

    assert {feature["properties"]["name"] for feature in result["features"]} == {"Fidji Est", "Fidji Ouest"}
    assert all(feature["properties"]["naviguideCatalogId"].startswith("science:") for feature in result["features"])
    assert result["metadata"]["matched"] == 2


def test_index_clusters_points_to_zoom_budget_without_losing_count():
    index = SpatialCatalogIndex("ports", [
        point(-4 + (position % 40) / 10, 45 + (position // 40) / 10, name=f"Port {position}")
        for position in range(1_000)
    ])

    result = index.query(Bbox(-5, 44, 1, 48), zoom=2, limit=420)

    assert len(result["features"]) <= 80
    assert sum(feature["properties"].get("clusterCount", 1) for feature in result["features"]) == 1_000
    assert result["metadata"]["clustered"] is True


def test_index_simplifies_long_trace_at_low_zoom_and_keeps_ends():
    coordinates = [[-5 + position / 100, 45 + position / 1_000] for position in range(300)]
    index = SpatialCatalogIndex("science", [{
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "properties": {"source": "csr", "name": "Campagne"},
    }])

    result = index.query(Bbox(-10, 40, 10, 55), zoom=2, source="csr")
    rendered = result["features"][0]["geometry"]["coordinates"]

    assert len(rendered) <= 64
    assert rendered[0] == coordinates[0]
    assert rendered[-1] == coordinates[-1]


def test_parse_bbox_rejects_invalid_latitude_but_keeps_wrapped_longitude():
    assert parse_bbox("170,-10,-170,10") == Bbox(170, -10, -170, 10)
    with pytest.raises(ValueError):
        parse_bbox("0,-91,1,1")
