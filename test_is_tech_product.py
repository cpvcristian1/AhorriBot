from scrapers import is_tech_product


def test_tech_products_detected():
    assert is_tech_product("Lenovo IdeaPad Slim 3 Gen 8 - Portatil 15.6 FHD")
    assert is_tech_product("ASUS TUF Gaming A15 - Laptop Gaming")
    assert is_tech_product("Apple 2024 MacBook Air de 13 pulgadas M3")


def test_non_tech_products_rejected():
    assert not is_tech_product("Funda para Kindle Paperwhite de silicona")
    assert not is_tech_product("Funda para port\u00e1til 15.6 pulgadas")
