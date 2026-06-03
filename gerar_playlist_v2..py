# -*- coding: utf-8 -*-
import urllib.request
import json
import ssl
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configurações do Portal e Repositório
PORTAL_URL = "http://foxbleu.pro"
MAC_ADDRESS = "00:1A:79:74:8F:27"
FICHEIRO_SAIDA_XML = "lista_final.xml"
UA = "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 sb2 embedded Safari/533.3"

def requisicao_portal(action, params="", token=None):
    """Efetua pedidos POST/GET seguros à API do Stalker Portal."""
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

def processar_e_gerar_xml():
    print(f"A ligar ao Stalker Portal através do MAC: {MAC_ADDRESS}...")
    
    # 1. Efetuar o Handshake inicial para obter o Token
    dados_token = requisicao_portal("handshake")
    if not dados_token or 'js' not in dados_token:
        print("Falha crítica: O endereço MAC pode estar expirado ou o portal bloqueou a ligação.")
        return
        
    token = dados_token['js'].get('token')
    
    # 2. Descarregar os canais disponíveis na conta
    print("A obter lista de canais do servidor...")
    dados_canais = requisicao_portal("get_all_channels", token=token)
    
    if not dados_canais or 'js' not in dados_canais or 'data' not in dados_canais['js']:
        print("Erro: Não foi possível ler a árvore de canais.")
        return
        
    canais = dados_canais['js']['data']
    
    # 3. Construir a estrutura XML limpa
    root = ET.Element("channels")
    total_convertidos = 0
    
    print("A estruturar dados para o padrão XML...")
    for canal in canais:
        nome = canal.get('name', 'Canal Sem Nome').strip()
        cmd = canal.get('cmd', '').strip()
        grupo = canal.get('tv_genre_id', 'Geral')
        logo = canal.get('logo', '')
        
        # Limpar comandos e argumentos internos do player do portal (ex: ffrt, ffmpeg)
        if " " in cmd and cmd.startswith(("ffrt", "ffmpeg")):
            link_stream = cmd.split(" ")[-1]
        else:
            link_stream = cmd
            
        # Filtra apenas links de transmissão HTTP válidos
        if link_stream.startswith("http"):
            item = ET.SubElement(root, "item")
            ET.SubElement(item, "title").text = nome
            ET.SubElement(item, "link").text = link_stream
            ET.SubElement(item, "thumbnail").text = logo
            ET.SubElement(item, "genre").text = str(grupo)
            total_convertidos += 1
            
    # 4. Formatar e indentar o ficheiro XML
    xml_string = ET.tostring(root, encoding="utf-8")
    xml_bonito = minidom.parseString(xml_string).toprettyxml(indent="    ")
    
    # 5. Exportar ficheiro final
    with open(FICHEIRO_SAIDA_XML, "w", encoding="utf-8") as f:
        f.write(xml_bonito)
        
    print(f"\n[Sucesso] O script concluiu a tarefa!")
    print(f"Ficheiro guardado em: '{FICHEIRO_SAIDA_XML}' contendo {total_convertidos} canais estruturados.")

if __name__ == "__main__":
    processar_e_gerar_xml()
