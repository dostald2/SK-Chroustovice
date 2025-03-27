from flask import Flask, render_template, url_for
import pandas as pd
import os

app = Flask(__name__)

def load_data():
    excel_file = "main.xlsx"

    if not os.path.exists(excel_file):
        print(f"Excel soubor '{excel_file}' nebyl nalezen!")
        cenik_df = pd.DataFrame()
        kasa_df = pd.DataFrame()
        dluhy_df = pd.DataFrame()
        sestava_df = pd.DataFrame()
    else:
        try:
            xl = pd.ExcelFile(excel_file, engine='openpyxl')
            print("Nalezené listy v Excelu:", xl.sheet_names)
            cenik_df = pd.read_excel(xl, sheet_name="Ceník", engine='openpyxl')
            kasa_df = pd.read_excel(xl, sheet_name="Částka v kase", engine='openpyxl')
            dluhy_df = pd.read_excel(xl, sheet_name="Dluhy", engine='openpyxl')
            sestava_df = pd.read_excel(xl, sheet_name="Sestava", engine='openpyxl')
        except Exception as e:
            print("Chyba při načítání Excelu:", e)
            cenik_df = pd.DataFrame()
            kasa_df = pd.DataFrame()
            dluhy_df = pd.DataFrame()
            sestava_df = pd.DataFrame()

    # Nahrazení NaN prázdnými řetězci
    cenik_df = cenik_df.fillna("")
    kasa_df = kasa_df.fillna("")
    dluhy_df = dluhy_df.fillna("")
    sestava_df = sestava_df.fillna("")

    # 1) Formátování čísla dresu – bez desetinných míst
    if "Číslo dresu" in sestava_df.columns:
        sestava_df["Číslo dresu"] = sestava_df["Číslo dresu"].apply(
            lambda x: str(int(x)) if x != "" and str(x).replace('.', '', 1).isdigit() else ""
        )

    # 2) U všech sloupců v "kasa_df" se pokusíme přidat "KČ", pokud je to číslo
    for col in kasa_df.columns:
        try:
            numeric_col = pd.to_numeric(kasa_df[col], errors='coerce')
            if numeric_col.notna().sum() > 0:
                kasa_df[col] = numeric_col.apply(lambda x: f"{int(x)} KČ" if pd.notna(x) else "")
        except Exception:
            pass

    # 3) U ceníku: pro každý numerický sloupec přidáme " KČ"
    for col in cenik_df.columns:
        try:
            numeric_col = pd.to_numeric(cenik_df[col], errors='coerce')
            if numeric_col.notna().sum() > 0:
                cenik_df[col] = numeric_col.apply(lambda x: f"{int(x)} KČ" if pd.notna(x) else "")
        except Exception:
            pass

    # 4) Dluhy: pro výpočet top 3 dlužníků si vytvoříme kopii s numerickým sloupcem "Dluh_numeric"
    raw_dluhy_df = dluhy_df.copy()
    if "Dluh" in raw_dluhy_df.columns:
        raw_dluhy_df["Dluh_numeric"] = pd.to_numeric(raw_dluhy_df["Dluh"], errors="coerce")
        try:
            # Vybereme 3 řádky s nejvyšší hodnotou Dluh_numeric
            top3 = raw_dluhy_df.nlargest(3, "Dluh_numeric")
            vitezove_list = []
            for idx, row in top3.iterrows():
                # Nyní hledejme pouze podle sloupce "Jméno"
                debtor_name = str(row.get("Jméno", "")).strip()
                dluh_numeric = row["Dluh_numeric"]
                photo = "placeholder.png"

                # V "Sestava" hledáme stejnou hodnotu "Jméno"
                if not sestava_df.empty and "Jméno" in sestava_df.columns and "Foto" in sestava_df.columns:
                    match = sestava_df[sestava_df["Jméno"].str.strip() == debtor_name]
                    if not match.empty:
                        photo = match.iloc[0]["Foto"]

                # Přidáme do seznamu
                vitezove_list.append({
                    "Jméno": debtor_name,
                    "Dluh": f"{int(dluh_numeric)} KČ" if pd.notna(dluh_numeric) else "",
                    "Foto": photo
                })
            vitezove = {"top3_dluhu": vitezove_list}
        except Exception as e:
            print("Chyba při výběru top 3 dlužníků:", e)
            vitezove = {"top3_dluhu": []}
    else:
        vitezove = {"top3_dluhu": []}

    # 5) Formátování sloupce "Dluh" v dluhy_df pro zobrazení
    if "Dluh" in dluhy_df.columns:
        dluhy_df["Dluh"] = dluhy_df["Dluh"].apply(lambda x: f"{int(x)} KČ" if str(x).replace('.', '', 1).isdigit() else x)

    # 6) Rozdělení hráčů podle pozice (v Sestava)
    positions = ['útočnící', 'záložníci', 'obránci', 'brankáři', 'realizační tým']
    sestava_groups = {}
    if not sestava_df.empty and "Pozice" in sestava_df.columns:
        for pos in positions:
            group = sestava_df[sestava_df["Pozice"].str.lower() == pos.lower()]
            sestava_groups[pos] = group.to_dict(orient="records")
    else:
        for pos in positions:
            sestava_groups[pos] = []

    # 7) Vytvoření HTML tabulek
    cenik_html = cenik_df.to_html(classes="table table-striped text-center", index=False, na_rep="")
    kasa_html = kasa_df.to_html(classes="table table-striped text-center", index=False, na_rep="")
    dluhy_html = dluhy_df.to_html(classes="table table-striped text-center", index=False, na_rep="")

    # 8) Zvýšení šířky sloupce „Částka“ (nebo „Momentální částka v kase“) pomocí replace
    for col_name in ["Částka", "Momentální částka v kase"]:
        kasa_html = kasa_html.replace(
            f"<th>{col_name}</th>",
            f'<th style="min-width: 200px;">{col_name}</th>'
        )
        cenik_html = cenik_html.replace(
            f"<th>{col_name}</th>",
            f'<th style="min-width: 200px;">{col_name}</th>'
        )

    data = {
        "cenik": cenik_html,
        "kasa": kasa_html,
        "dluhy": dluhy_html,
        "sestava": sestava_groups,
        "vitezove": vitezove
    }
    return data

@app.route("/")
def index():
    data = load_data()
    return render_template("index.html", data=data)

if __name__ == "__main__":
    app.run(debug=True)
