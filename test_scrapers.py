"""Tests for scrapers.py.

No network access: the only I/O in scrapers is urllib.request.urlopen, which is
replaced by a tiny in-memory fake that returns embedded RSS samples. The parsing
logic (the part that can actually break) is what gets exercised.
"""

import urllib.request

import pytest

from scrapers import (
    fetch_camel_top_drops,
    fetch_chollometro_deals,
    is_tech_product,
    parse_price_str,
)


# --- fake urlopen -----------------------------------------------------------

class _FakeResponse:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake_urlopen(xml_data: bytes):
    """monkeypatch-compatible urlopen replacement. Raises if called with no data."""
    def _open(req, timeout=None):
        assert timeout is not None, "scrapers must set a timeout"
        return _FakeResponse(xml_data)
    return _open


@pytest.fixture
def fake_camel(monkeypatch):
    def _install(xml_data: bytes):
        monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen(xml_data))
    return _install


@pytest.fixture
def fake_chollometro(monkeypatch):
    def _install(xml_data: bytes):
        monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen(xml_data))
    return _install


# --- parse_price_str --------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("8,90", 8.9),
        ("154.33", 15433.0),  # es-ES format: dot = thousands sep, so this is 15433.0 by design
        ("1.234,56", 1234.56),
        ("5,00", 5.0),
        ("no price", 0.0),
        ("", 0.0),
    ],
)
def test_parse_price_str(raw, expected):
    assert parse_price_str(raw) == pytest.approx(expected)


# --- is_tech_product (kept from the original script) ------------------------

@pytest.mark.parametrize(
    "title,expected",
    [
        ("Lenovo IdeaPad Slim 3 Gen 8 - Portátil 15.6 FHD", True),
        ("Apple 2024 MacBook Air de 13 pulgadas M3", True),
        ("ASUS TUF Gaming A15 - Laptop Gaming", True),
        ("Kindle Paperwhite (16 GB) con pantalla de 6,8", True),
        ("Kobo Clara Colour Ereader con pantalla táctil", True),
        ("Funda para Kindle Paperwhite de silicona", False),
        ("Funda para portátil 15.6 pulgadas", False),
    ],
)
def test_is_tech_product_cases(title, expected):
    assert is_tech_product(title) is expected


# --- fetch_camel_top_drops --------------------------------------------------

CAMEL_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Kindle Paperwhite 16 GB - down 35.97% (5,00\xe2\x82\xac) to 8,90\xe2\x82\xac from 13,90\xe2\x82\xac</title>
      <link>https://es.camelcamelcamel.com/product/B08N3J8GTX</link>
      <pubDate>Mon, 13 Oct 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Silla de oficina - down 20.00% (10,00\xe2\x82\xac) to 40,00\xe2\x82\xac from 50,00\xe2\x82\xac</title>
      <link>https://es.camelcamelcamel.com/product/B09XXXXXXX</link>
      <pubDate>Mon, 13 Oct 2026 09:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Sin enlace de producto - down 10.00% (1,00\xe2\x82\xac) to 9,00\xe2\x82\xac from 10,00\xe2\x82\xac</title>
      <link>https://es.camelcamelcamel.com/top_drops</link>
    </item>
    <item>
      <title>Titulo sin patron de bajada</title>
      <link>https://es.camelcamelcamel.com/product/B08N3J8GTY</link>
    </item>
  </channel>
</rss>
"""


def test_camel_top_drops_parses_valid_items_only(fake_camel):
    fake_camel(CAMEL_FEED)
    drops = fetch_camel_top_drops()

    # Items without ASIN in the link or without the drop pattern are skipped.
    assert len(drops) == 2

    tech = drops[0]
    assert tech["source"] == "CamelCamelCamel"
    assert tech["asin"] == "B08N3J8GTX"
    assert tech["title"] == "Kindle Paperwhite 16 GB"
    assert tech["new_price"] == pytest.approx(8.90)
    assert tech["old_price"] == pytest.approx(13.90)
    assert tech["drop_pct"] == pytest.approx(35.97)
    assert tech["amazon_url"] == "https://www.amazon.es/dp/B08N3J8GTX"
    assert "B08N3J8GTX" in tech["keepa_graph_url"]
    assert tech["pub_date"] == "Mon, 13 Oct 2026 10:00:00 GMT"

    # Tech filter over the fetched titles (what the original script printed).
    assert [is_tech_product(d["title"]) for d in drops] == [True, False]


def test_camel_top_drops_swallows_errors(monkeypatch):
    def boom(req, timeout=None):
        raise OSError("network down")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert fetch_camel_top_drops() == []


# --- fetch_chollometro_deals ------------------------------------------------

CHOLLO_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Monitor LG 27 pulgadas</title>
      <link>https://www.chollometro.com/ofertas/monitor-lg</link>
      <category>Electr\xc3\xb3nica</category>
      <description>Precio 149,99\xe2\x82\xac en https://www.amazon.es/dp/B0C1ABCDEF</description>
    </item>
    <item>
      <title>Cafetera de c\xc3\xa1psulas</title>
      <link>https://www.chollometro.com/ofertas/cafetera</link>
      <category>Hogar</category>
      <description>Oferta en https://www.amazon.es/dp/B0C1ABCDEG sin precio</description>
    </item>
    <item>
      <title>SSD NVMe 1TB</title>
      <link>https://www.chollometro.com/ofertas/ssd</link>
      <category>Inform\xc3\xa1tica</category>
      <description>Chollo en Amazon 59,50\xe2\x82\xac, ver /dp/B0C1ABCDEH</description>
    </item>
    <item>
      <title>Zapatillas deportivas</title>
      <link>https://www.chollometro.com/ofertas/zapatillas</link>
      <category>Moda</category>
      <description>Oferta en otra tienda, 39,99\xe2\x82\xac https://www.pccomponentes.com/dp/B0C1ABCDEI</description>
    </item>
  </channel>
</rss>
"""


def test_chollometro_filters_amazon_and_electronics(fake_chollometro):
    fake_chollometro(CHOLLO_FEED)
    deals = fetch_chollometro_deals()

    # Cafetera: amazon but not electronics/tech -> out.
    # Zapatillas: not amazon -> out.
    assert [d["asin"] for d in deals] == ["B0C1ABCDEF", "B0C1ABCDEH"]

    first = deals[0]
    assert first["source"] == "Chollometro"
    assert first["title"] == "Monitor LG 27 pulgadas"
    assert first["new_price"] == pytest.approx(149.99)
    assert first["old_price"] == 0.0
    assert first["drop_pct"] == 0.0
    assert first["amazon_url"] == "https://www.amazon.es/dp/B0C1ABCDEF"
    assert first["chollometro_url"] == "https://www.chollometro.com/ofertas/monitor-lg"

    # No price in the description -> 0.0, and /dp/ASIN fallback still resolves.
    assert deals[1]["asin"] == "B0C1ABCDEH"
    assert deals[1]["new_price"] == pytest.approx(59.50)


def test_chollometro_swallows_errors(monkeypatch):
    def boom(req, timeout=None):
        raise OSError("network down")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert fetch_chollometro_deals() == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
