"""SerpAPI geo lookup testleri (P1-E / patch 3b5cc5e)."""

from core.lead_collector import _get_ll, _TR_CENTROID_LL


def test_istanbul_ilce_resolves():
    # Kadıköy istanbul ilçesi — özel koordinat olmali
    ll = _get_ll("Kadıköy", "İstanbul")
    assert ll.startswith("@40.")   # Kadıköy civari
    assert ll != _TR_CENTROID_LL


def test_sehir_resolves_when_ilce_missing():
    ll = _get_ll("", "Ankara")
    assert ll.startswith("@39.9")   # Ankara centroid
    assert ll != _TR_CENTROID_LL


def test_unknown_city_falls_back_to_centroid():
    # Eskiden İstanbul koordinatı dönüyordu — şimdi Türkiye centroid olmali
    ll = _get_ll("", "YokBöyleBirŞehir")
    assert ll == _TR_CENTROID_LL


def test_case_insensitive():
    # Türkçe İ/ı dolayisiyla normalize olmali
    ll1 = _get_ll("", "İzmir")
    ll2 = _get_ll("", "izmir")
    ll3 = _get_ll("", "IZMIR")
    assert ll1 == ll2 == ll3


def test_ilce_preferred_over_sehir():
    # Ikisi de bilinirse ilce'nin koordinati doner
    ll_ilce = _get_ll("Kadıköy", "")
    ll_both = _get_ll("Kadıköy", "İstanbul")
    assert ll_ilce == ll_both
