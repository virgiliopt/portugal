# -*- coding: utf-8 -*-
import json
import urllib.request
import ssl
import re

URL_ESTRUTURA = "https://raw.githubusercontent.com/virgiliopt/portugal/refs/heads/main/iptv.m3u"
URL_EPG = "https://githubusercontent.com"
FICHEIRO_SAIDA = "lista_final.m3u"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def obter_html(url):
    """Descarrega o conteúdo de qualquer URL (JSON, M3U ou XML)."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        contexto_ssl = ssl._create_unverified_context()
        with urllib.request.urlopen(req, context=contexto_ssl, timeout=15) as resposta:
            return resposta.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Erro ao aceder a {url}: {e}")
        return ""

def extrair_m3u_externo(conteudo_m3u, grupo_padrao):
    """Processa blocos de playlists M3U externas e injeta o grupo correto."""
    linhas = conteudo_m3u.splitlines()
    blocos_canais = []
    info_atual = None
    
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        if linha.startswith("#EXTINF"):
            # Força ou adiciona a categoria baseada no menu do seu JSON
            if "group-title=" not in linha:
                linha = linha.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{grupo_padrao}"')
            info_atual = linha
        elif linha.startswith("http") and info_atual:
            blocos_canais.append(f"{info_atual}\n{linha}\n")
            info_atual = None
            
    return blocos_canais

def converter_xml_para_m3u(conteudo_xml, grupo_padrao):
    """Converte estruturas simples de ficheiros XML (padrão Kodi) para formato M3U."""
    blocos_canais = []
    # Expressão regular simples para capturar tags <item> habituais em builds Kodi
    itens = re.findall(r'<item>(.*?)</item>', conteudo_xml, re.DOTALL)
    
    for item in itens:
        title = re.search(r'<title>(.*?)</title>', item)
        link = re.search(r'<link>(.*?)</link>', item)
        thumbnail = re.search(r'<thumbnail>(.*?)</thumbnail>', item)
        
        if title and link:
            nome = title.group(1).strip()
            url_stream = link.group(1).strip()
            logo = thumbnail.group(1).strip() if thumbnail else ""
            
            # Filtra links que sejam apenas ficheiros de texto/scripts expansíveis
            if url_stream.startswith("http") and not url_stream.endswith(('.xml', '.json')):
                linha = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{grupo_padrao}",{nome}\n{url_stream}\n'
                blocos_canais.append(linha)
                
    return blocos_canais

def processar_tudo():
    print("A descarregar o ficheiro de estrutura...")
    conteudo_json = obter_html(URL_ESTRUTURA)
    if not conteudo_json:
        return
        
    try:
        dados = json.loads(conteudo_json)
        estrutura = dados.get("ESTRUTURA", [])
    except Exception as e:
        print(f"Erro ao decodificar JSON: {e}")
        return

    with open(FICHEIRO_SAIDA, "w", encoding="utf-8") as f_saida:
        # Cabeçalho padrão aceito pelas Smart TVs
        f_saida.write(f'#EXTM3U x-tvg-url="{URL_EPG}"\n\n')
        
        for item in estrutura:
            nome_grupo = item.get("nome", "Geral")
            url_fonte = item.get("url", "")
            
            if not url_fonte:
                continue
                
            print(f"A processar categoria: {nome_grupo}...")
            conteudo_fonte = obter_html(url_fonte)
            
            if not conteudo_fonte:
                continue
            
            # Identifica o tipo de conteúdo da fonte e converte para linhas M3U
            if "#EXTM3U" in conteudo_fonte or "get.php" in url_fonte:
                canais = extrair_m3u_externo(conteudo_fonte, nome_grupo)
                for canal in canais:
                    f_saida.write(canal)
            elif "<item>" in conteudo_fonte or "<channel>" in conteudo_fonte:
                canais = converter_xml_para_m3u(conteudo_fonte, nome_grupo)
                for canal in canais:
                    f_saida.write(canal)
            else:
                # Caso seja uma API Jellyfin/Emby (como os itens Filmes/Disney no seu JSON)
                # Requer tratamento JSON específico para extrair os streams de vídeo locais.
                if "Items?" in url_fonte:
                    try:
                        dados_jelly = json.loads(conteudo_fonte)
                        for filme in dados_jelly.get("Items", []):
                            f_nome = filme.get("Name")
                            f_id = filme.get("Id")
                            # Constrói o link direto de streaming do Jellyfin
                            base_jelly = url_fonte.split("/Items")[0]
                            api_key = url_fonte.split("api_key=")[1].split("&")[0]
                            f_url = f"{base_jelly}/Videos/{f_id}/stream?static=true&api_key={api_key}"
                            
                            f_saida.write(f'#EXTINF:-1 group-title="{nome_grupo}",{f_nome}\n{f_url}\n\n')
                    except:
                        pass

    print(f"\nConcluído! O ficheiro '{FICHEIRO_SAIDA}' está pronto para ser usado na Smart TV.")

if __name__ == "__main__":
    processar_tudo()
