import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
import time
import random
import pandas as pd
import base64

st.set_page_config(page_title="SRI Stealth Mode", page_icon="🕵️", layout="wide")

# --- FUNCIONES DE COMPORTAMIENTO HUMANO (Tu lógica original) ---
def human_delay(min_sec=0.5, max_sec=1.5):
    time.sleep(random.uniform(min_sec, max_sec))

def safe_click(driver, element, intentos=3):
    for i in range(intentos):
        try:
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            human_delay(0.3, 0.5)
            try:
                element.click()
                return True
            except:
                try:
                    ActionChains(driver).move_to_element(element).click().perform()
                    return True
                except:
                    driver.execute_script("arguments[0].click();", element)
                    return True
        except:
            human_delay(0.5, 1)
    return False

def human_type(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))

def get_base64_screenshot(driver):
    try: return driver.get_screenshot_as_base64()
    except: return None

# --- CREACIÓN DEL NAVEGADOR CAMUFLADO (CRÍTICO) ---
def create_driver():
    options = Options()
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # 1. User Agent de Windows (Miente al servidor diciendo que es Windows)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 2. Ocultar que es automatización
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except:
        driver = webdriver.Chrome(options=options)

    # 3. STEALTH: Simular Hardware Real
    stealth(driver,
        languages=["es-ES", "es"],
        vendor="Google Inc.",
        platform="Win32", # Decimos que somos Windows aunque seamos Linux
        webgl_vendor="Intel Inc.", # Simulamos tarjeta gráfica Intel
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    return driver

def consultar_persona(driver, nombre_busqueda, debug_mode=False):
    logs = []
    try:
        driver.get("https://srienlinea.sri.gob.ec/sri-en-linea/SriPagosWeb/ConsultaDeudasFirmesImpugnadas/Consultas/consultaDeudasFirmesImpugnadas")
        human_delay(2, 4) # Esperar que cargue el script de seguridad
        
        # Limpieza de Popups
        driver.execute_script("""
            ['noSoportado', 'advertenciaNavegador', 'disablingDiv'].forEach(id => {
                var el = document.getElementById(id);
                if (el) el.remove();
            });
            document.body.classList.remove('modal-open');
            document.querySelectorAll('.modal-backdrop, .ui-widget-overlay').forEach(el => el.remove());
        """)
        
        wait = WebDriverWait(driver, 20)
        
        # INTENTO DE CLIC EN PESTAÑA
        try:
            btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label*="apellidos y nombres"]')))
            safe_click(driver, btn)
        except:
            return {'error': 'Error pestaña Nombres', 'img': get_base64_screenshot(driver)}

        human_delay(1, 2)
        
        # INGRESAR DATOS
        try:
            input_elem = wait.until(EC.presence_of_element_located((By.ID, "busquedaRazonSocialId")))
            input_elem.clear()
            try: input_elem.click()
            except: pass
            human_type(input_elem, nombre_busqueda)
            human_delay(0.5, 1)
        except:
            return {'error': 'Error input', 'img': get_base64_screenshot(driver)}
        
        # BUSCAR BOTÓN CONSULTAR (Lógica Obsesiva Original)
        consultar_btn = None
        for intento in range(5):
            try:
                # Prioridad 1: Botón visible
                btn = driver.find_element(By.CSS_SELECTOR, "button.cyan-btn:not([disabled])")
                if btn.is_displayed():
                    consultar_btn = btn
                    break
            except: pass
            
            if not consultar_btn:
                try:
                    # Prioridad 2: Texto
                    btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Consultar')]")
                    for b in btns:
                        if b.is_displayed() and b.get_attribute('disabled') != 'true':
                            consultar_btn = b
                            break
                except: pass
            human_delay(0.5, 1)
        
        if consultar_btn:
            safe_click(driver, consultar_btn)
        else:
            input_elem.send_keys(Keys.ENTER)
        
        human_delay(3, 5) # Esperar respuesta del servidor
        
        # LECTURA FINAL
        for i in range(10):
            human_delay(1, 1.2)
            try:
                result = driver.execute_script("""
                    var text = document.body.innerText || "";
                    
                    // Detectar el error de puntaje específicamente
                    if (text.includes('Puntaje bajo') || text.includes('umbral')) {
                        return {bloqueado: true, mensaje: 'Bloqueo SRI: Puntaje Bajo 0.0'};
                    }
                    
                    if (text.includes('no generó resultados')) {
                        return {sin_resultados: true};
                    }
                    
                    var spans = document.querySelectorAll('span.titulo-consultas-1');
                    for (var i = 0; i < spans.length; i++) {
                        var txt = spans[i].textContent.trim().replace(/\\s/g, '');
                        if (/^\\d{10,13}$/.test(txt)) return {ruc: txt};
                    }
                    return null;
                """)
                
                if result:
                    if debug_mode: result['img'] = get_base64_screenshot(driver)
                    return result
            except: continue
            
        return {'sin_resultados': True, 'mensaje': 'Tiempo agotado', 'img': get_base64_screenshot(driver)}

    except Exception as e:
        return {'error': str(e)[:100], 'img': get_base64_screenshot(driver)}

# --- INTERFAZ ---
with st.sidebar:
    st.header("Config")
    debug_mode = st.checkbox("📸 Ver Capturas", value=True)

st.title("🕵️‍♂️ Consulta SRI (Stealth Mode)")
st.warning("Nota: Si sale 'Puntaje Bajo', intenta consultar 1 solo nombre a la vez.")

txt_input = st.text_area("Nombres:", height=150)

if st.button("Consultar"):
    nombres = [n.strip() for n in txt_input.split('\n') if n.strip()]
    if nombres:
        bar = st.progress(0)
        
        # Usamos un solo driver para toda la sesión para mantener "cookies"
        with st.spinner("Iniciando navegador camuflado..."):
            driver = create_driver()
        
        try:
            for i, nombre in enumerate(nombres):
                st.write(f"🔎 Buscando: **{nombre}**...")
                data = consultar_persona(driver, nombre, debug_mode)
                
                if data.get('ruc'):
                    st.success(f"✅ RUC: {data['ruc']}")
                elif data.get('bloqueado'):
                    st.error(f"⛔ {data.get('mensaje')}")
                elif data.get('sin_resultados'):
                    st.warning("⚠️ Sin resultados")
                else:
                    st.error(f"❌ Error: {data.get('error')}")
                
                if debug_mode and data.get('img'):
                    st.image(base64.b64decode(data['img']), width=500)
                
                bar.progress((i+1)/len(nombres))
        finally:
            driver.quit()