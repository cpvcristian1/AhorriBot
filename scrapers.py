import re
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from config import TECH_KEYWORDS, EXCLUDE_KEYWORDS

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def is_tech_product(title: str) -> bool:
    """Comprueba si el título del producto corresponde a electrónica / gadgets."""
    title_lower = title.lower()
    
    # Exclusiones
    for excl in EXCLUDE_KEYWORDS:
        if excl in title_lower:
            return False
            
    # Coincidencia con palabras clave tecnológicas
    for kw in TECH_KEYWORDS:
        if kw in title_lower:
            return True
            
    return False

def parse_price_str(price_str: str) -> float:
    """Convierte un precio en texto a float.

    Formato aceptado: espanol (es-ES), que es el que devuelven las fuentes del
    bot (Amazon Espana, Chollometro, CamelCamelCamel). La coma ',' es el
    separador decimal y el punto '.' es el separador de millares.

    Los puntos se eliminan antes de convertir, asi que "154.33" se interpreta
    como 15433.0. Es una decision a proposito, no un error: un punto en estas
    fuentes siempre separa millares. No hay soporte para punto decimal
    anglosajon ("154.33" no significa nunca 154 con 33 centimos).
    """
    clean = price_str.replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return 0.0

def fetch_camel_top_drops() -> List[Dict[str, Any]]:
    """
    Obtiene las mayores bajadas de precio recientes en Amazon España desde CamelCamelCamel.
    No requiere API Key.
    """
    url = "https://es.camelcamelcamel.com/top_drops/feed"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    
    deals = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
            
        root = ET.fromstring(xml_data)
        for item in root.findall("./channel/item"):
            title = item.find("title").text or ""
            link = item.find("link").text or ""
            pub_date = item.find("pubDate").text or ""
            
            # Extraer ASIN
            asin_match = re.search(r'/product/([A-Z0-9]{10})', link)
            if not asin_match:
                continue
            asin = asin_match.group(1)
            
            # Formato típico: "Nombre - down 35.97% (5,00€) to 8,90€ from 13,90€"
            drop_match = re.search(r'down ([\d\.]+)% \(([\d,\.]+)€\) to ([\d,\.]+)€ from ([\d,\.]+)€', title)
            if not drop_match:
                continue
                
            drop_pct = float(drop_match.group(1))
            saved_str = drop_match.group(2)
            new_price_str = drop_match.group(3)
            old_price_str = drop_match.group(4)
            
            new_price = parse_price_str(new_price_str)
            old_price = parse_price_str(old_price_str)
            product_name = title.split(" - down ")[0].strip()
            
            deals.append({
                "source": "CamelCamelCamel",
                "asin": asin,
                "title": product_name,
                "new_price": new_price,
                "old_price": old_price,
                "drop_pct": drop_pct,
                "amazon_url": f"https://www.amazon.es/dp/{asin}",
                "keepa_graph_url": f"https://graph.keepa.com/pricehistory.png?asin={asin}&domain=es",
                "keepa_web_url": f"https://keepa.com/#!product/4-{asin}",
                "pub_date": pub_date
            })
    except Exception as e:
        print(f"[Error Scraper Camel] {e}")
        
    return deals

def fetch_chollometro_deals() -> List[Dict[str, Any]]:
    """
    Obtiene ofertas recientes de Amazon España desde Chollometro (filtrando Electrónica y errores de precio).
    """
    url = "https://www.chollometro.com/rss/nuevos"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    
    deals = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
            
        root = ET.fromstring(xml_data)
        for item in root.findall("./channel/item"):
            title = item.find("title").text or ""
            link = item.find("link").text or ""
            desc = item.find("description").text or ""
            
            category_elem = item.find("category")
            category = category_elem.text if category_elem is not None else ""
            
            # Comprobar si es de Amazon
            # Chollometro usa namespace pepper:merchant o se menciona en descripción/título
            is_amazon = "amazon" in desc.lower() or "amazon" in title.lower()
            if not is_amazon:
                continue
                
            # Comprobar si es electrónica
            if category != "Electrónica" and not is_tech_product(title):
                continue
                
            # Buscar ASIN en la descripción o enlaces
            asin_match = re.search(r'amazon\.es/(?:dp|gp/product)/([A-Z0-9]{10})', desc)
            if not asin_match:
                # Buscar ASIN en formato /dp/ASIN
                asin_match = re.search(r'/dp/([A-Z0-9]{10})', desc)
            
            if not asin_match:
                continue
                
            asin = asin_match.group(1)
            
            # Buscar precio: la regex acepta coma o punto como separador, pero
            # el formato de las fuentes es es-ES ("18,13" = 18.13 euros; un
            # punto, si aparece, son millares y parse_price_str lo trata asi).
            price_match = re.search(r'(\d+[,\.]\d{2})€', desc)
            price = parse_price_str(price_match.group(1)) if price_match else 0.0
            
            deals.append({
                "source": "Chollometro",
                "asin": asin,
                "title": title.strip(),
                "new_price": price,
                "old_price": 0.0,
                "drop_pct": 0.0, # Se comprobará o notificará si es chollo destacado
                "amazon_url": f"https://www.amazon.es/dp/{asin}",
                "keepa_graph_url": f"https://graph.keepa.com/pricehistory.png?asin={asin}&domain=es",
                "keepa_web_url": f"https://keepa.com/#!product/4-{asin}",
                "chollometro_url": link
            })
    except Exception as e:
        print(f"[Error Scraper Chollometro] {e}")
        
    return deals
