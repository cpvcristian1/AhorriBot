from scrapers import fetch_camel_top_drops, fetch_chollometro_deals, is_tech_product

print("Fetching CamelCamelCamel drops...")
drops = fetch_camel_top_drops()
print(f"Total drops fetched: {len(drops)}")
for d in drops:
    tech = is_tech_product(d["title"])
    tag = "TECH" if tech else "OTHER"
    print(f"[{tag}] -{d['drop_pct']}% | {d['new_price']}€ | {d['title'][:50]} | ASIN: {d['asin']}")

print("\n--- Testing Specific Categories (Portátiles & Ebooks) ---")
test_cases = [
    ("Lenovo IdeaPad Slim 3 Gen 8 - Portátil 15.6 FHD", True),
    ("Apple 2024 MacBook Air de 13 pulgadas M3", True),
    ("ASUS TUF Gaming A15 - Laptop Gaming", True),
    ("Kindle Paperwhite (16 GB) con pantalla de 6,8", True),
    ("Kobo Clara Colour Ereader con pantalla táctil", True),
    ("Funda para Kindle Paperwhite de silicona", False),
    ("Funda para portátil 15.6 pulgadas", False),
]
for title, expected in test_cases:
    res = is_tech_product(title)
    print(f"[{'PASS' if res == expected else 'FAIL'}] '{title}' -> Tech: {res}")


print("\nFetching Chollometro deals...")
chollo_deals = fetch_chollometro_deals()
print(f"Total Chollometro Amazon deals fetched: {len(chollo_deals)}")
for c in chollo_deals:
    print(f"[CHOLLO] {c['title'][:50]} | {c['new_price']}€ | ASIN: {c['asin']}")
