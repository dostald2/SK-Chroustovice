import os
import pandas as pd
from flask import Flask, render_template, url_for

app = Flask(__name__)

# Pomocné funkce pro výběr top 3 (sestupně)
def get_top_3_desc(df, col):
    if col not in df.columns:
        return []
    df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[col].dropna().empty:
        return []
    top3 = df.nlargest(3, col)
    records = top3.to_dict(orient="records")
    # Převod hodnot v daném sloupci na celá čísla
    for record in records:
        if col in record and pd.notna(record[col]):
            record[col] = int(record[col])
    return records

# Pomocná funkce pro výběr top 3 (vzestupně)
def get_top_3_asc(df, col):
    if col not in df.columns:
        return []
    df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[col].dropna().empty:
        return []
    top3 = df.nsmallest(3, col)
    records = top3.to_dict(orient="records")
    for record in records:
        if col in record and pd.notna(record[col]):
            record[col] = int(record[col])
    return records

def load_data():
    excel_file = "main.xlsx"
    if not os.path.exists(excel_file):
        print(f"Excel soubor '{excel_file}' nebyl nalezen!")
        sestava_df = pd.DataFrame()
        cenik_df = pd.DataFrame()
        kasa_df = pd.DataFrame()
        dluhy_df = pd.DataFrame()
    else:
        try:
            xl = pd.ExcelFile(excel_file, engine='openpyxl')
            print("Nalezené listy v Excelu:", xl.sheet_names)
            sestava_df = pd.read_excel(xl, sheet_name="Sestava", engine='openpyxl')
            cenik_df = pd.read_excel(xl, sheet_name="Ceník", engine='openpyxl')
            kasa_df = pd.read_excel(xl, sheet_name="Částka v kase", engine='openpyxl', header=None)
            kasa_df.columns = ["Částka"]
            dluhy_df = pd.read_excel(xl, sheet_name="Dluhy", engine='openpyxl')
        except Exception as e:
            print("Chyba při načítání Excelu:", e)
            sestava_df = pd.DataFrame()
            cenik_df = pd.DataFrame()
            kasa_df = pd.DataFrame()
            dluhy_df = pd.DataFrame()

    # Nahrazení NaN prázdnými řetězci
    sestava_df = sestava_df.fillna("")
    cenik_df = cenik_df.fillna("")
    kasa_df = kasa_df.fillna("")
    dluhy_df = dluhy_df.fillna("")

    # Odstraníme sloupec ID, pokud existuje
    if "ID" in sestava_df.columns:
        sestava_df = sestava_df.drop(columns=["ID"])

    # Formátování "Číslo dresu" – bez desetinných míst
    if "Číslo dresu" in sestava_df.columns:
        sestava_df["Číslo dresu"] = sestava_df["Číslo dresu"].apply(
            lambda x: str(int(x)) if x != "" and str(x).replace('.', '', 1).isdigit() else ""
        )

    # Převod sloupců ŽK a ČK na celá čísla
    if "ŽK" in sestava_df.columns:
        sestava_df["ŽK"] = pd.to_numeric(sestava_df["ŽK"], errors="coerce").fillna(0).astype(int)
    if "ČK" in sestava_df.columns:
        sestava_df["ČK"] = pd.to_numeric(sestava_df["ČK"], errors="coerce").fillna(0).astype(int)

    # Přidání " KČ" u hodnot v kase a ceniku
    for col in kasa_df.columns:
        try:
            numeric = pd.to_numeric(kasa_df[col], errors='coerce')
            if numeric.notna().sum() > 0:
                kasa_df[col] = numeric.apply(lambda x: f"{int(x)} KČ" if pd.notna(x) else "")
        except Exception:
            pass
    for col in cenik_df.columns:
        try:
            numeric = pd.to_numeric(cenik_df[col], errors='coerce')
            if numeric.notna().sum() > 0:
                cenik_df[col] = numeric.apply(lambda x: f"{int(x)} KČ" if pd.notna(x) else "")
        except Exception:
            pass

    # Dluhy: vytvoříme kopii s numerickým sloupcem "Dluh_numeric"
    raw_dluhy_df = dluhy_df.copy()
    if "Dluh" in raw_dluhy_df.columns:
        raw_dluhy_df["Dluh_numeric"] = pd.to_numeric(raw_dluhy_df["Dluh"], errors="coerce")
        if not raw_dluhy_df["Dluh_numeric"].dropna().empty:
            top3_dluhy = raw_dluhy_df.nlargest(3, "Dluh_numeric")
        else:
            top3_dluhy = pd.DataFrame()
        top3_dluhy_list = []
        for _, row in top3_dluhy.iterrows():
            name = str(row.get("Jméno", "")).strip()
            dluh_val = row["Dluh_numeric"]
            photo = "placeholder.png"
            if not sestava_df.empty and "Jméno" in sestava_df.columns and "Foto" in sestava_df.columns:
                match = sestava_df[sestava_df["Jméno"].str.strip() == name]
                if not match.empty:
                    photo = match.iloc[0]["Foto"]
            top3_dluhy_list.append({
                "Jméno": name,
                "Dluh": f"{int(dluh_val)} KČ" if pd.notna(dluh_val) else "",
                "Foto": photo
            })
        top_3_debtors = top3_dluhy_list
    else:
        top_3_debtors = []
    if "Dluh" in dluhy_df.columns:
        dluhy_df["Dluh"] = dluhy_df["Dluh"].apply(lambda x: f"{int(x)} KČ" if str(x).replace('.', '', 1).isdigit() else x)

    # Výpočet sloupce "Minuty na gól" z "Minuty" a "Počet gólů za sezónu"
    if "Minuty" in sestava_df.columns and "Počet gólů za sezónu" in sestava_df.columns:
        def calc_minutes_per_goal(row):
            try:
                goals = float(row["Počet gólů za sezónu"])
                minutes = float(row["Minuty"])
                if goals > 0:
                    return minutes / goals
                else:
                    return None
            except:
                return None
        sestava_df["Minuty na gól"] = sestava_df.apply(calc_minutes_per_goal, axis=1)
    else:
        sestava_df["Minuty na gól"] = None

    # Rozdělení hráčů podle pozice
    positions = ['útočnící', 'záložníci', 'obránci', 'brankáři', 'realizační tým']
    sestava_groups = {}
    if not sestava_df.empty and "Pozice" in sestava_df.columns:
        for pos in positions:
            group = sestava_df[sestava_df["Pozice"].str.lower() == pos.lower()]
            sestava_groups[pos] = group.to_dict(orient="records")
    else:
        for pos in positions:
            sestava_groups[pos] = []

    # Pro statistiky převod relevantních sloupců na čísla
    stat_cols = ["Věk", "Počet gólů za sezónu", "Počet zápasů", "ŽK", "ČK", "Minuty", "Minuty na gól"]
    for col in stat_cols:
        if col in sestava_df.columns:
            sestava_df[col] = pd.to_numeric(sestava_df[col], errors="coerce")

    # Statistika: Nejlepší střelci – top 3 podle "Počet gólů za sezónu"
    top_3_goals = get_top_3_desc(sestava_df, "Počet gólů za sezónu")
    # Statistika: Nejvíce odehraných minut – top 3 podle "Minuty"
    top_3_minutes = get_top_3_desc(sestava_df, "Minuty")
    # Statistika: Nejtrestanější hráči – top 3 podle penalizačního skóre (Penalty = ŽK + 2*ČK)
    if "ŽK" in sestava_df.columns and "ČK" in sestava_df.columns:
        sestava_df["Penalty"] = sestava_df["ŽK"] + 2 * sestava_df["ČK"]
        top_3_penalized = get_top_3_desc(sestava_df, "Penalty")
    else:
        top_3_penalized = []
    # Statistika: Nejméně potřebných minut na gól – top 3 podle "Minuty na gól" (vzestupně)
    top_3_minute_per_goal = get_top_3_asc(sestava_df, "Minuty na gól")

    # Vytvoření HTML tabulek
    cenik_html = cenik_df.to_html(classes="table table-striped text-center", index=False, na_rep="")
    kasa_html = kasa_df.to_html(classes="table table-striped text-center", index=False, header=False, na_rep="")
    dluhy_html = dluhy_df.to_html(classes="table table-striped text-center", index=False, na_rep="")

    # Zvýšení šířky sloupce "Částka" nebo "Momentální částka v kase"
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
        "top_3_debtors": top_3_debtors,
        "top_3_goals": top_3_goals,
        "top_3_minutes": top_3_minutes,
        "top_3_penalized": top_3_penalized,
        "top_3_minute_per_goal": top_3_minute_per_goal
    }
    return data

@app.route("/")
def index():
    data = load_data()
    return render_template("index.html", data=data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
