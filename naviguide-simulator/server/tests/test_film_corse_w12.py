"""W12 : ports corses regroupés dans l'ordre de la trace (Calvi → … → Porto-Vecchio)."""
import film_script as fs


def test_w12_prefer_coast_ports_corse_trace_order():
    geo = {"fr": "la Corse", "en": "Corsica", "kind": "island"}
    shuffled = ["Porto-Vecchio", "Bastia", "L'ile Rousse", "Calvi"]
    assert fs._prefer_coast_ports(shuffled, geo) == ["Calvi", "L'ile Rousse"]
