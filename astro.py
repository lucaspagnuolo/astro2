# app_astrologia.py
# Requisiti:
# pip install streamlit pyswisseph geopy timezonefinder pytz pandas

import streamlit as st
from datetime import datetime, time, date
import pytz
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
import swisseph as swe
import pandas as pd

# --- Costanti e mapping
SIGNS_IT = [
    "Ariete", "Toro", "Gemelli", "Cancro", "Leone", "Vergine",
    "Bilancia", "Scorpione", "Sagittario", "Capricorno", "Acquario", "Pesci"
]

ELEMENTS = {
   "Fuoco": ["Ariete","Leone","Sagittario"],
   "Terra": ["Toro","Vergine","Capricorno"],
   "Aria":  ["Gemelli","Bilancia","Acquario"],
   "Acqua": ["Cancro","Scorpione","Pesci"]
}

MODALITIES = {
   "Cardinale": ["Ariete","Cancro","Bilancia","Capricorno"],
   "Fisso": ["Toro","Leone","Scorpione","Acquario"],
   "Mobili": ["Gemelli","Vergine","Sagittario","Pesci"]
}

RULERS = {
   "Ariete":"Marte", "Toro":"Venere", "Gemelli":"Mercurio", "Cancro":"Luna",
   "Leone":"Sole", "Vergine":"Mercurio", "Bilancia":"Venere", "Scorpione":"Plutone/Marte",
   "Sagittario":"Giove", "Capricorno":"Saturno", "Acquario":"Urano/Saturno", "Pesci":"Nettuno/Giove"
}

PLANET_MEANINGS = {
    "Sole":"Identità di base, volontà e vitalità.",
    "Luna":"Emozioni, bisogni interiori, reazioni automatiche.",
    "Mercurio":"Mente, comunicazione, apprendimento.",
    "Venere":"Affetti, bellezza, valore e relazioni.",
    "Marte":"Energia, azione, assertività.",
    "Giove":"Espansione, fortuna, visione filosofica.",
    "Saturno":"Disciplina, struttura, limiti e responsabilità.",
    "Urano":"Originalità, rivoluzione, cambi improvvisi.",
    "Nettuno":"Sensibilità, sogno, immaginazione, spiritualità.",
    "Plutone":"Trasformazione profonda, potere, rigenerazione.",
    "Nodo":"Tema del percorso karmico o direzione evolutiva.",
    "Chirone":"Ferita che conduce a guarigione e insegnamento."
}

HOUSE_MEANINGS = {
    1: "Identità e presenza personale; come ti mostri al mondo.",
    2: "Risorse materiali, valore personale, possedimenti.",
    3: "Comunicazione, vicini, fratelli, apprendimento immediato.",
    4: "Casa, famiglia, radici, base emotiva.",
    5: "Creatività, amore romantico, progetti personali, figli.",
    6: "Lavoro quotidiano, salute, servizio.",
    7: "Partnership, matrimonio, relazioni strette.",
    8: "Risorse condivise, trasformazione, morte/rinascita.",
    9: "Filosofia, viaggi lunghi, studi superiori, fede.",
    10: "Carriera, reputazione, obiettivi pubblici.",
    11: "Amicizie, gruppi, aspirazioni collettive.",
    12: "Inconscio, ritiri, limitazioni, spiritualità."
}

# --- Helper functions
def deg_to_sign(deg):
    deg = deg % 360
    idx = int(deg // 30)
    deg_in_sign = deg % 30
    return SIGNS_IT[idx], deg_in_sign, idx

def get_element(sign):
    for el, signs in ELEMENTS.items():
        if sign in signs:
            return el
    return None

def get_modality(sign):
    for mod, signs in MODALITIES.items():
        if sign in signs:
            return mod
    return None

def geocode_place(place):
    geolocator = Nominatim(user_agent="streamlit_astrology_app")
    location = geolocator.geocode(place, timeout=10)
    if not location:
        return None
    return location.latitude, location.longitude, location.address

def get_timezone(lat, lon):
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lng=lon, lat=lat)
    return tz_name

def get_house_of_longitude(planet_deg, cusps):
    """Determina la casa (1..12) in cui cade una longitudine, dati i cusps restituiti da swe.houses."""
    p = planet_deg % 360
    # cusps is typically an array-like with indices 1..12 (cusps[1] = cusp of house 1)
    # We'll accomodate 0-indexed list as well.
    # Normalize cusps into list indexed 1..12
    cusp = [0]*13
    try:
        for i in range(1,13):
            cusp[i] = cusps[i]
    except Exception:
        # if cusps is 0-indexed
        for i in range(1,13):
            cusp[i] = cusps[i-1]
    for i in range(1,13):
        start = cusp[i] % 360
        end = cusp[1] % 360 if i==12 else cusp[i+1] % 360
        # normalize interval
        s = start
        e = end
        if e <= s:
            e += 360
        pp = p
        if pp < s:
            pp += 360
        if s <= pp < e:
            return i
    # fallback
    return None

def calc_positions_and_houses(dt_utc, lat, lon):
    # dt_utc: timezone-aware datetime in UTC
    year = dt_utc.year
    month = dt_utc.month
    day = dt_utc.day
    hour = dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600
    jd_ut = swe.julday(year, month, day, hour, swe.GREG_CAL)

    # compute houses
    cusps, ascmc = swe.houses(jd_ut, lat, lon)
    # prepare planet map (Italian names)
    planet_list = [
        ("Sole", getattr(swe, "SUN", None)),
        ("Luna", getattr(swe, "MOON", None)),
        ("Mercurio", getattr(swe, "MERCURY", None)),
        ("Venere", getattr(swe, "VENUS", None)),
        ("Marte", getattr(swe, "MARS", None)),
        ("Giove", getattr(swe, "JUPITER", None)),
        ("Saturno", getattr(swe, "SATURN", None)),
        ("Urano", getattr(swe, "URANUS", None)),
        ("Nettuno", getattr(swe, "NEPTUNE", None)),
        ("Plutone", getattr(swe, "PLUTO", None)),
        ("Nodo (Vero)", getattr(swe, "TRUE_NODE", getattr(swe, "MEAN_NODE", None))),
        ("Chirone", getattr(swe, "CHIRON", None))
    ]

    results = []
    for pname, pconst in planet_list:
        if pconst is None:
            # skip if this constant not available in the swisseph build
            continue
        try:
            calc = swe.calc_ut(jd_ut, pconst)
            # calc can be (pos, retflag) or raise; pos may be at index 0
            pos = calc[0]
            lon = pos[0] % 360
        except Exception as e:
            # se non è possibile calcolare, salta
            continue

        sign, deg_in_sign, sign_idx = deg_to_sign(lon)
        house = get_house_of_longitude(lon, cusps)
        element = get_element(sign)
        modality = get_modality(sign)
        ruler = RULERS.get(sign, "-")
        results.append({
            "pianeta": pname,
            "long_deg": lon,
            "segno": sign,
            "deg_in_sign": deg_in_sign,
            "sign_idx": sign_idx,
            "casa": house,
            "elemento": element,
            "modalita": modality,
            "ruler": ruler
        })
    # also return cusps and asc for display
    asc = ascmc[0] if len(ascmc) > 0 else None
    return results, cusps, asc

# --- Streamlit UI
st.set_page_config(page_title="Mini-app Astrologica", layout="centered")
st.title("📜 Mini-app Astrologica — Sole, Ascendente, Luna e oltre")
st.write("Inserisci i tuoi dati di nascita per ottenere segno zodiacale, ascendente, Luna, tutte le posizioni planetarie disponibili e l'analisi per le 12 case.")

with st.form("astro_form"):
    nome = st.text_input("Nome e cognome", placeholder="Es: Mario Rossi")
    luogo = st.text_input("Luogo di nascita (città, paese). Se preferisci puoi inserire latitudine/longitudine sotto", placeholder="Es: Roma, Italia")
    col1, col2 = st.columns(2)
    with col1:
        lat_in = st.text_input("Facoltativo - Latitudine (es. 41.90)", value="")
    with col2:
        lon_in = st.text_input("Facoltativo - Longitudine (es. 12.49)", value="")
    date_of_birth = st.date_input("Data di nascita",
                                  min_value=date(1900,1,1),
                                  max_value=date.today(),
                                  value=date(1990,1,1))
    time_of_birth = st.time_input("Ora di nascita (ora locale)", value=time(12,0))
    submitted = st.form_submit_button("Calcola")

if submitted:
    if not nome:
        st.error("Inserisci almeno il nome.")
    else:
        # Ottieni lat/lon: preferisci i campi espliciti se compilati, altrimenti geocoding
        lat = lon = None
        address = None
        if lat_in.strip() and lon_in.strip():
            try:
                lat = float(lat_in)
                lon = float(lon_in)
                address = f"Lat:{lat}, Lon:{lon}"
            except:
                st.warning("Latitudine/Longitudine non valide. Provo a geocodificare il luogo.")
        if lat is None or lon is None:
            if luogo.strip():
                geo = geocode_place(luogo)
                if geo:
                    lat, lon, address = geo
                else:
                    st.error("Non sono riuscito a geocodificare il luogo. Inserisci latitudine e longitudine manualmente.")
                    st.stop()
            else:
                st.error("Inserisci il luogo o lat/lon.")
                st.stop()

        # timezone
        tz_name = get_timezone(lat, lon)
        if not tz_name:
            st.error("Non sono riuscito a determinare il fuso orario dal luogo. Inserisci un luogo diverso o il fuso orario manualmente.")
            st.stop()

        # costruisci datetime local e converto in UTC
        local = pytz.timezone(tz_name)
        naive_dt = datetime.combine(date_of_birth, time_of_birth)
        try:
            local_dt = local.localize(naive_dt)
        except Exception:
            # some tz libs accept replace tzinfo
            local_dt = naive_dt.replace(tzinfo=local)
        dt_utc = local_dt.astimezone(pytz.utc)

        # opzionale: set ephemeris path se vuoi usare file locali
        # swe.set_ephe_path('/path/to/ephe')

        try:
            results, cusps, asc_deg = calc_positions_and_houses(dt_utc, lat, lon)
        except Exception as e:
            st.error(f"Errore durante il calcolo astronomico: {e}")
            st.stop()

        if not results:
            st.error("Nessuna posizione planetaria calcolata (problema con swisseph).")
            st.stop()

        # dataframe per visualizzazione
        df = pd.DataFrame(results)
        # migliorie alle colonne
        df_display = df.copy()
        df_display["long_deg"] = df_display["long_deg"].map(lambda x: f"{x:.4f}°")
        df_display["deg_in_sign"] = df_display["deg_in_sign"].map(lambda x: f"{x:.2f}°")
        df_display = df_display[["pianeta","segno","deg_in_sign","long_deg","casa","elemento","modalita","ruler"]]

        # header
        st.subheader(f"Ciao {nome.split()[0].capitalize()} 👋")
        st.info(f"*Segno/Ascendente/Luna e altro* — dati calcolati per: {local_dt.strftime('%Y-%m-%d %H:%M:%S')} ({tz_name})")
        # tecnical details
        with st.expander("Dettagli tecnici (coordinate, data/ora, gradi, cusps)"):
            st.write(f"Luogo risolto: {address}")
            st.write(f"Coordinate: {lat:.5f}, {lon:.5f}")
            st.write(f"Fuso orario rilevato: {tz_name}")
            st.write(f"Data/ora locali: {local_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"Data/ora UTC: {dt_utc.strftime('%Y-%m-%d %H:%M:%S')}")
            st.write("Ascendente approssimativo: {:.4f}°".format(asc_deg if asc_deg is not None else 0))
            # show cusps briefly
            try:
                cusp_dict = {i: f"{cusps[i]:.4f}°" for i in range(1,13)}
            except Exception:
                cusp_dict = {i: f"{cusps[i-1]:.4f}°" for i in range(1,13)}
            st.write("Cusps (case):")
            st.write(cusp_dict)

        # mostra tabella
        st.markdown("### Tabella posizioni planetarie")
        st.dataframe(df_display)

        # analisi sinteticA: elementi, modalità, stellium
        # conteggi
        element_counts = df['elemento'].value_counts(dropna=True).to_dict()
        modality_counts = df['modalita'].value_counts(dropna=True).to_dict()
        sign_counts = df['segno'].value_counts(dropna=True).to_dict()
        house_counts = df['casa'].value_counts(dropna=True).to_dict()

        st.markdown("### Sintesi statistica")
        st.write("- Elementi presenti:", element_counts)
        st.write("- Modalità presenti:", modality_counts)
        st.write("- Pianeti per segno (possibili stellium):", sign_counts)
        st.write("- Pianeti per casa:", house_counts)

        # stellium detection (3+ pianeti in stesso segno)
        stellia = {s:c for s,c in sign_counts.items() if c>=3}
        if stellia:
            st.warning(f"Stellium rilevato in: {stellia} (3 o più pianeti nello stesso segno).")

        # interpretazioni planetarie (sintetiche) e case
        st.markdown("### Interpretazione sintetica planetaria")
        for r in results:
            pname = r["pianeta"]
            sign = r["segno"]
            deg = r["deg_in_sign"]
            casa = r["casa"]
            meaning = PLANET_MEANINGS.get(pname.split()[0], PLANET_MEANINGS.get(pname, ""))
            st.markdown(f"*{pname}* in *{sign} {deg:.2f}°* — Casa {casa if casa else '-'}")
            if meaning:
                st.write(f"- {meaning}")
            # contestualizzazione rapida
            st.write(f"- Elemento: {r['elemento']}, Modalità: {r['modalita']}, Ruler (del segno): {r['ruler']}")
            st.write("")

        st.markdown("### Significato delle case (sintesi)")
        for i in range(1,13):
            st.write(f"*Casa {i}* — {HOUSE_MEANINGS.get(i,'')}")

        # integrazione: combinazioni principali (Sole-Luna-Asc) se presenti
        # trovare Sole, Luna, Ascendente
        def find_by_name(lst, name):
            for it in lst:
                if it["pianeta"].lower().startswith(name.lower()):
                    return it
            return None
        sun = find_by_name(results, "Sole")
        moon = find_by_name(results, "Luna")
        # ascendente: lo capiamo dal grado ascmc[0]
        asc_sign = None
        if asc_deg is not None:
            asc_sign, asc_deg_in_sign, _ = deg_to_sign(asc_deg)
        st.write("---")
        st.markdown("### Integrazione Sole / Ascendente / Luna (sintesi)")
        if sun:
            st.write(f"- Sole in *{sun['segno']}*: {PLANET_MEANINGS.get('Sole')}")
        if asc_sign:
            st.write(f"- Ascendente in *{asc_sign}* (stima dall'ascendente calcolato).")
        if moon:
            st.write(f"- Luna in *{moon['segno']}*: {PLANET_MEANINGS.get('Luna')}")

        # costruzione report testuale scaricabile
        report_lines = []
        report_lines.append(f"Report astrologico per: {nome}")
        report_lines.append(f"Nascita locale: {local_dt.strftime('%Y-%m-%d %H:%M:%S')} ({tz_name})")
        report_lines.append(f"Luogo: {address}  ({lat:.5f}, {lon:.5f})")
        report_lines.append("")
        report_lines.append("Posizioni planetarie:")
        for r in results:
            report_lines.append(f"{r['pianeta']:12s}: {r['segno']} {r['deg_in_sign']:.2f}°  - Casa {r['casa']}  - Elemento: {r['elemento']}  - Modalità: {r['modalita']}")
        report_lines.append("")
        report_lines.append("Sintesi elementi e modalità:")
        report_lines.append(f"Elementi: {element_counts}")
        report_lines.append(f"Modalità: {modality_counts}")
        if stellia:
            report_lines.append(f"Stellium rilevato in: {stellia}")
        report_lines.append("")
        report_lines.append("Interpretazioni sintetiche (per pianeta):")
        for r in results:
            p = r["pianeta"]
            meaning = PLANET_MEANINGS.get(p.split()[0], PLANET_MEANINGS.get(p, ""))
            report_lines.append(f"- {p} in {r['segno']} (Casa {r['casa']}): {meaning}")
        report_text = "\n".join(report_lines)

        st.download_button("Scarica report (.txt)", data=report_text, file_name=f"report_astrologico_{nome.replace(' ','_')}.txt", mime="text/plain")

        st.success("Analisi completata — ricorda che questa è una sintesi generale: un tema natale completo prende in considerazione aspetti, tutte le posizioni dei pianeti, le case e molto altro. Se vuoi, posso:")
        st.write("- generare un report più lungo (es. 3-5 pagine di testo),")
        st.write("- aggiungere gli aspetti (congiunzioni, opposizioni ecc.) e la loro interpretazione,")
        st.write("- includere interpretazioni personalizzate per coppie di pianeti (es. Sole congiunto Venere, ecc.).")
