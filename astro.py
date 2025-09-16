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

# --- Funzioni helper
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
    p = planet_deg % 360
    cusp = [0]*13
    try:
        for i in range(1,13):
            cusp[i] = cusps[i]
    except Exception:
        for i in range(1,13):
            cusp[i] = cusps[i-1]
    for i in range(1,13):
        start = cusp[i] % 360
        end = cusp[1] % 360 if i==12 else cusp[i+1] % 360
        s = start
        e = end
        if e <= s:
            e += 360
        pp = p
        if pp < s:
            pp += 360
        if s <= pp < e:
            return i
    return None

def calc_positions_and_houses(dt_utc, lat, lon):
    year = dt_utc.year
    month = dt_utc.month
    day = dt_utc.day
    hour = dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600
    jd_ut = swe.julday(year, month, day, hour, swe.GREG_CAL)
    cusps, ascmc = swe.houses(jd_ut, lat, lon)
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
            continue
        try:
            calc = swe.calc_ut(jd_ut, pconst)
            pos = calc[0]
            lon = pos[0] % 360
        except Exception:
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
    asc = ascmc[0] if len(ascmc) > 0 else None
    return results, cusps, asc

# --- UI Streamlit
st.set_page_config(page_title="Mini-app Astrologica", layout="centered")
st.title("📜 Mini-app Astrologica — Sole, Ascendente, Luna e oltre")
st.write("Inserisci i tuoi dati di nascita per ottenere segno zodiacale, ascendente, Luna, tutte le posizioni planetarie disponibili e l'analisi per le 12 case.")

with st.form("astro_form"):
    nome = st.text_input("Nome e cognome", placeholder="Es: Mario Rossi")
    luogo = st.text_input("Luogo di nascita", placeholder="Es: Roma, Italia")
    col1, col2 = st.columns(2)
    with col1:
        lat_in = st.text_input("Latitudine (facoltativa)", value="")
    with col2:
        lon_in = st.text_input("Longitudine (facoltativa)", value="")
    date_of_birth = st.date_input("Data di nascita", min_value=date(1900,1,1), max_value=date.today(), value=date(1990,1,1))
    time_of_birth = st.time_input("Ora di nascita", value=time(12,0))
    submitted = st.form_submit_button("Calcola")

if submitted:
    if not nome:
        st.error("Inserisci almeno il nome.")
    else:
        lat = lon = None
        address = None
        if lat_in.strip() and lon_in.strip():
            try:
                lat = float(lat_in)
                lon = float(lon_in)
                address = f"Lat:{lat}, Lon:{lon}"
            except:
                st.warning("Coordinate non valide. Provo a geocodificare il luogo.")
        if lat is None or lon is None:
            if luogo.strip():
                geo = geocode_place(luogo)
                if geo:
                    lat, lon, address = geo
                else:
                    st.error("Geocodifica fallita. Inserisci lat/lon manualmente.")
                    st.stop()
            else:
                st.error("Inserisci il luogo o lat/lon.")
                st.stop()

        tz_name = get_timezone(lat, lon)
        if not tz_name:
            st.error("Fuso orario non trovato.")
            st.stop()

        local = pytz.timezone(tz_name)
        naive_dt = datetime.combine(date_of_birth, time_of_birth)
        try:
            local_dt = local.localize(naive_dt)
        except Exception:
            local_dt = naive_dt.replace(tzinfo=local)
        dt_utc = local_dt.astimezone(pytz.utc)

        try:
            results, cusps, asc_deg = calc_positions_and_houses(dt_utc, lat, lon)
        except Exception as e:
            st.error(f"Errore nel calcolo: {e}")
            st.stop()

        if not results:
            st.error("Nessuna posizione calcolata.")
            st.stop()

        df = pd.DataFrame(results)
        df_display = df.copy()
        df_display["long_deg"] = df_display["long_deg"].map(lambda x: f"{x:.4f}°")
        df_display["deg_in_sign"] = df_display["deg_in_sign"].map(lambda x: f"{x:.2f}°")
        df_display = df_display[["pianeta","segno","deg_in_sign","long_deg","casa","elemento","modalita","ruler"]]

        st.subheader(f"Ciao {nome.split()[0].capitalize()} 👋")
        st.info(f"Dati calcolati per: {local_dt.strftime('%Y-%m-%d %H:%M:%S')} ({tz_name})")

        st.markdown("### Tabella posizioni planetarie")
        st.dataframe(df_display)

        # --- Interpretazione fluida
        def interpretazione_fluida(r):
            pname = r["pianeta"]
            sign = r["segno"]
            deg = r["deg_in_sign"]
            casa = r["casa"]
            elemento = r["elemento"]
            modalita = r["modalita"]
            ruler = r["ruler"]
            meaning = PLANET_MEANINGS.get(pname.split()[0], PLANET_MEANINGS.get(pname, ""))

            frase = f"Il {pname.lower()} si trova nel segno del {sign}, a {deg:.2f}°, "
            frase += f"nella casa {casa}. " if casa else "in una posizione non assegnata a una casa specifica. "
            if meaning:
                frase += f"Questo suggerisce: {meaning} "
            frase += f"Il segno è di elemento {elemento.lower()}, con modalità {modalita.lower()}, governato da {ruler}."
            return frase

        st.markdown("### Interpretazione fluida dei pianeti")
        for r in results:
            st.write(interpretazione_fluida(r))
