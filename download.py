from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from bs4 import BeautifulSoup
import openpyxl

# URL stránky se statistikami
url = "https://is1.fotbal.cz/hraci/statistiky.aspx?req=4f6ff782-6377-466b-92f3-ce1a91d375fe"

# Nastavení možností pro Chrome (headless režim)
chrome_options = Options()
chrome_options.add_argument("--headless")  # Spuštění prohlížeče v režimu bez GUI
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Inicializace Selenium webdriveru (ujistěte se, že chromedriver je ve vašem PATH)
driver = webdriver.Chrome(options=chrome_options)
driver.get(url)

# Počkejme několik sekund, aby se stránka načetla včetně JavaScriptu
time.sleep(5)

# Získání zdrojového kódu stránky
page_source = driver.page_source
driver.quit()

# Parsování HTML pomocí BeautifulSoup
soup = BeautifulSoup(page_source, "html.parser")

# Vyhledáme tabulku podle id "MainContent_gridData"
table = soup.find("table", {"id": "MainContent_gridData"})
if table is None:
    print("Tabulka s ID 'MainContent_gridData' nebyla nalezena.")
    exit()

# Najdeme všechny řádky v těle tabulky
rows = table.find("tbody").find_all("tr")

# Vytvoříme slovník: klíč = ID hráče, hodnota = (Góly, Zápasy, ŽK, ČK, Minuty)
player_stats = {}
for row in rows:
    cells = row.find_all("td")
    if len(cells) < 9:
        continue
    # ID hráče se nachází v první buňce uvnitř tagu <a>
    player_id = cells[0].find("a").get_text(strip=True)
    goly = cells[4].get_text(strip=True)
    zapasy = cells[5].get_text(strip=True)
    zk = cells[6].get_text(strip=True)
    ck = cells[7].get_text(strip=True)
    minuty = cells[8].get_text(strip=True)

    player_stats[player_id] = (goly, zapasy, zk, ck, minuty)

# Načtení existujícího Excel souboru main.xlsx a otevření listu "Sestava"
wb = openpyxl.load_workbook("main.xlsx")
ws = wb["Sestava"]

# Pro každý řádek v listu "Sestava" (předpokládáme, že první řádek je hlavička)
# kontrolujeme sloupec A (index 0) a pokud najdeme odpovídající data, zapíšeme je do sloupců G až K (indexy 6 až 10)
for row in ws.iter_rows(min_row=2):
    excel_id = row[0].value  # Sloupec A
    if excel_id is None:
        continue
    excel_id_str = str(excel_id).strip()

    if excel_id_str in player_stats:
        goly, zapasy, zk, ck, minuty = player_stats[excel_id_str]
        row[6].value = goly  # Sloupec G
        row[7].value = zapasy  # Sloupec H
        row[8].value = zk  # Sloupec I
        row[9].value = ck  # Sloupec J
        row[10].value = minuty  # Sloupec K

# Uložení změn do Excel souboru
wb.save("main.xlsx")
print("Data byla úspěšně aktualizována v souboru main.xlsx.")
