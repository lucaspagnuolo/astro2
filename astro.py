# app_astrologia.py
# Requisiti:
# pip install streamlit pyswisseph geopy timezonefinder pytz
import streamlit as st
from datetime import datetime, time
import pytz
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
import swisseph as swe
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
def calc_positions(dt_utc, lat, lon):
   # dt_utc: timezone-aware datetime in UTC
   # swisseph expects UT in julian day
   year = dt_utc.year
   month = dt_utc.month
   day = dt_utc.day
   hour = dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600
   jd_ut = swe.julday(year, month, day, hour, swe.GREG_CAL)
   # Sun
   sun = swe.calc_ut(jd_ut, swe.SUN)[0][0]  # longitude degrees
   # Moon
   moon = swe.calc_ut(jd_ut, swe.MOON)[0][0]
   # Houses -> returns (cusps, ascmc) where ascmc[0] is ascendant
   cusps, ascmc = swe.houses(jd_ut, lat, lon)
   asc = ascmc[0]  # ascendant longitude degrees
   return sun, moon, asc
# --- Streamlit UI
st.title("📜 Mini-app Astrologica — Sole, Ascendente, Luna")
st.write("Inserisci i tuoi dati di nascita per ottenere segno zodiacale, ascendente, Luna e una breve analisi del carattere.")
with st.form("astro_form"):
   nome = st.text_input("Nome e cognome", placeholder="Es: Mario Rossi")
   luogo = st.text_input("Luogo di nascita (città, paese). Se preferisci puoi inserire latitudine/longitudine sotto", placeholder="Es: Roma, Italia")
   col1, col2 = st.columns(2)
   with col1:
       lat_in = st.text_input("Facoltativo - Latitudine (es. 41.90)", value="")
   with col2:
       lon_in = st.text_input("Facoltativo - Longitudine (es. 12.49)", value="")
   date_of_birth = st.date_input("Data di nascita", min_value=date(1900,1,1))
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
       local_dt = local.localize(naive_dt)
       dt_utc = local_dt.astimezone(pytz.utc)
       # imposta percorso ephemeris (opzionale) - puoi cambiare se hai ephem files locali
       # swe.set_ephe_path('/path/to/ephe')  # opzionale
       try:
           sun_deg, moon_deg, asc_deg = calc_positions(dt_utc, lat, lon)
       except Exception as e:
           st.error(f"Errore durante il calcolo astronomico: {e}")
           st.stop()
       # ottieni segni
       sun_sign, sun_deg_in_sign, sun_idx = deg_to_sign(sun_deg)
       moon_sign, moon_deg_in_sign, moon_idx = deg_to_sign(moon_deg)
       asc_sign, asc_deg_in_sign, asc_idx = deg_to_sign(asc_deg)
       # element & modality
       sun_element = get_element(sun_sign)
       asc_element = get_element(asc_sign)
       moon_element = get_element(moon_sign)
       sun_mod = get_modality(sun_sign)
       # messaggio principale
       st.subheader(f"Ciao {nome.split()[0].capitalize()} 👋")
       st.markdown(f"**In base alle informazioni date ti confermo che tu sei:**")
       st.info(f"**Segno solare:** {sun_sign}  —  **Ascendente:** {asc_sign}  —  **Luna:** {moon_sign}")
       # dettagli tecnici
       with st.expander("Dettagli tecnici (coordinate, data/ora, gradi)"):
           st.write(f"Luogo risolto: {address}")
           st.write(f"Coordinate: {lat:.5f}, {lon:.5f}")
           st.write(f"Fuso orario rilevato: {tz_name}")
           st.write(f"Data/ora locali: {local_dt.strftime('%Y-%m-%d %H:%M:%S')}")
           st.write(f"Data/ora UTC: {dt_utc.strftime('%Y-%m-%d %H:%M:%S')}")
           st.write(f"Sole: {sun_deg:.4f}° ({sun_sign} {sun_deg_in_sign:.2f}°)")
           st.write(f"Luna: {moon_deg:.4f}° ({moon_sign} {moon_deg_in_sign:.2f}°)")
           st.write(f"Ascendente: {asc_deg:.4f}° ({asc_sign} {asc_deg_in_sign:.2f}°)")
       # Ulteriori caratteristiche sintetiche
       st.markdown("### Altre caratteristiche sintetiche")
       st.write(f"- Elemento solare: **{sun_element}**")
       st.write(f"- Modalità solare: **{sun_mod}**")
       st.write(f"- Pianeta dominante (rulership) del Sole: **{RULERS.get(sun_sign,'-')}**")
       # Analisi del carattere: combinazione Sole / Ascendente / Luna
       st.markdown("### Analisi del carattere e possibili scenari")
       def describe_sign(sign):
           desc = {
               "Ariete":"impulsivo, energico, iniziatore. Ama le sfide e agisce con coraggio.",
               "Toro":"stabile, pratico, amante del comfort e della sicurezza. Paziente e testardo.",
               "Gemelli":"curioso, comunicativo, adattabile. Mente vivace e talvolta dispersiva.",
               "Cancro":"sensibile, protettivo, emotivo. Forte legame con la famiglia.",
               "Leone":"fiero, creativo, desidera attenzione e riconoscimento. Generoso.",
               "Vergine":"analitico, preciso, orientato al servizio. Attento ai dettagli.",
               "Bilancia":"armonico, relazionale, cerca equilibrio e bellezza. Diplomazia.",
               "Scorpione":"intenso, profondo, trasformativo. Misterioso e determinato.",
               "Sagittario":"ottimista, amante della libertà, esploratore filosofico.",
               "Capricorno":"ambizioso, disciplinato, realistico. Cerca struttura e status.",
               "Acquario":"originale, progressista, mentale. Valori collettivi e indipendenza.",
               "Pesci":"sensibile, empatico, fantasioso. Spesso spirituale o idealista."
           }
           return desc.get(sign,"")
       # Componi testo
       sun_text = describe_sign(sun_sign)
       asc_text = describe_sign(asc_sign)
       moon_text = describe_sign(moon_sign)
       st.markdown(f"**Sole in {sun_sign}:** {sun_text}")
       st.markdown(f"**Ascendente in {asc_sign}:** {asc_text} (come maschera sociale/primo impatto)")
       st.markdown(f"**Luna in {moon_sign}:** {moon_text} (reazioni emotive e bisogni interiori)")
       # Integrazione: come si combinano
       st.write("---")
       st.write("**Integrazione sintetica:**")
       combo = (
           f"Con il Sole in **{sun_sign}** avrai energia e orientamento tipici di quel segno; "
           f"l'Ascendente in **{asc_sign}** descrive come ti presenti al mondo e può addolcire/modificare "
           f"l'impressione solare; infine la Luna in **{moon_sign}** guida i tuoi bisogni emotivi e le reazioni automatiche."
       )
       st.write(combo)
       # Scenari pratici
       st.markdown("**Possibili scenari/pratiche**")
       st.write("- *Lavoro:* considera il desiderio/valore indicato dal tuo Sole come bussola professionale; l'Ascendente mostra come ti vendi socialmente; la Luna indica l'ambiente emotivo in cui ti senti a tuo agio.")
       st.write("- *Relazioni:* la Luna descrive l'intimità emotiva; ascendente e Venere/pianeti in casa relazioni indicano lo stile d'amore.")
       st.write("- *Sfide tipiche:* conflitti tra desiderio (Sole) e sicurezza emotiva (Luna) o tra immagine sociale (Asc) e bisogni interiori (Luna).")
       # Consigli pratici personalizzati
       st.markdown("**Consigli pratici**")
       st.write(f"- Sfrutta il tuo elemento solare (**{sun_element}**) per scegliere attività energizzanti coerenti.")
       st.write(f"- Se senti tensioni: prova a riconoscere quando agisci per l'immagine (Ascendente) e quando agisci per bisogno emotivo (Luna).")
       st.write("- Cura il sonno e i rituali emotivi: la Luna è molto sensibile ai ritmi quotidiani.")
       st.success("Analisi completata — ricorda che questa è una sintesi generale: un tema natale completo prende in considerazione tutte le case e i pianeti.")
       st.caption("Se vuoi, posso generare un report testuale più lungo o una lista di punti di forza/area di crescita basata sui tre fattori principali (Sole, Luna, Asc.).")
