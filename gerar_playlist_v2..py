# -*- coding: utf-8 -*-
import urllib.request
import json
import ssl
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configurações do Portal fornecido
PORTAL_URL = "http://foxbleu.pro"
MAC_ADDRESS = "00:1A:79:74:8F:27"
FICHEIRO_SAIDA_XML = "lista_portal.xml"
UA = "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 sb2 embedded Safari/533.3"

def requisicao_portal(action, params="", token=None):
    """Efetua pedidos POST/GET à API do Stalker Portal."""
    url = f"{PORTAL_URL}?type=itv&action={action}&{params}"
    headers = {
        'User-Agent': UA,
        'Cookie': f'mac={MAC_ADDRESS}'
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
        
    try:
        req = urllib.request.Request(url, headers=headers)
        contexto_ssl = ssl._create_unverified_context()
        with urllib.request.urlopen(req, context=contexto_ssl, timeout=15) as resposta:
            return json.loads(resposta.read().decode('utf-8', errors='ignore'))
    except Exception as e:
        print(f"Erro na ação '{action}': {e}")
        return None

def obter_canais_e_gerar_xml():
    print(f"A autenticar no portal com o MAC: {MAC_ADDRESS}...")
    
    # 1. Handshake para obter o Token de Acesso
    dados_token = requisicao_portal("handshake")
    if not dados_token or 'js' not in dados_token:
        print("Falha na autenticação. O MAC pode estar expirado ou bloqueado por IP.")
        return
        
    token = dados_token['js'].get('token')
    
    # 2. Obter todos os canais de TV
    print("A descarregar lista de canais...")
    dados_canais = requisicao_portal("get_all_channels", token=token)
    
    if not dados_canais or 'js' not in dados_canais or 'data' not in dados_canais['js']:
        print("Não foi possível carregar a lista de canais.")
        return
        
    canais = dados_canais['js']['data']
    
    # 3. Criar a estrutura XML base
    root = ET.Element("channels")
    canais_convertidos = 0
    
    print("A converter dados para o formato XML estruturado...")
    for canal in canais:
        nome = canal.get('name', 'Canal Sem Nome').strip()
        cmd = canal.get('cmd', '').strip()
        grupo = canal.get('tv_genre_id', 'Geral') # ID ou categoria interna do portal
        logo = canal.get('logo', '')
        
        # Limpar prefixos de emuladores do link de stream (ex: ffrt, ffmpeg)
        if " " in cmd and cmd.startswith(("ffrt", "ffmpeg")):
            link_stream = cmd.split(" ")[-1]
        else:
            link_stream = cmd
            
        # Apenas processa links de vídeo válidos
        if link_stream.startswith("http"):
            item = ET.SubElement(root, "item")
            ET.SubElement(item, "title").text = nome
            ET.SubElement(item, "link").text = link_stream
            ET.SubElement(item, "thumbnail").text = logo
            ET.SubElement(item, "genre").text = str(grupo)
            canais_convertidos += 1
            
    # 4. Formatar o XML com indentação limpa
    xml_string = ET.tostring(root, encoding="utf-8")
    xml_bonito = minidom.parseString(xml_string).toprettyxml(indent="    ")
    
    # 5. Guardar o ficheiro final
    with open(FICHEIRO_SAIDA_XML, "w", encoding="utf-8") as f:
        f.write(xml_bonito)
        
    print(f"\nSucesso! {canais_convertidos} canais gravados em '{FICHEIRO_SAIDA_XML}'.")

if __name__ == "__main__":
    obter_canais_e_gerar_xml()
