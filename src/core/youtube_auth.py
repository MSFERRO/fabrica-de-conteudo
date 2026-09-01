import os
import sys
import json
import httpx
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import settings

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

received_code = None

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global received_code
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        if "code" in params:
            received_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
            <html>
                <head><title>Sucesso!</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #2e7d32;">🎉 Autenticação Concluída com Sucesso!</h1>
                    <p style="font-size: 18px;">As credenciais do canal foram recebidas. Você já pode fechar esta aba e voltar ao terminal.</p>
                </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("Código de autorização não encontrado.".encode("utf-8"))

    def log_message(self, format, *args):
        # Silencia logs padrão do HTTP server
        pass

def run_auth_flow():
    global received_code
    print("=" * 60)
    print("     AUTENTICACAO OAUTH 2.0 - FABRICA DE CONTEUDO")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        index_str = sys.argv[1].strip()
    else:
        index_str = input("\nQual o indice da credencial que deseja autenticar? (1 ou 2): ").strip()
        
    client_secrets_file = settings.CONFIG_DIR / f"client_secrets_{index_str}.json"
    credentials_file = settings.CONFIG_DIR / f"youtube_credentials_{index_str}.json"
    
    if not client_secrets_file.exists():
        print(f"\nERRO: O arquivo {client_secrets_file.name} nao foi encontrado na pasta config!")
        return
        
    with open(client_secrets_file, "r", encoding="utf-8") as f:
        secrets_data = json.load(f)
        
    client_info = secrets_data.get("installed") or secrets_data.get("web", {})
    client_id = client_info.get("client_id")
    client_secret = client_info.get("client_secret")
    redirect_uri = "http://localhost:8080/"
    
    scope_str = " ".join(SCOPES)
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={urllib.parse.quote(client_id)}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        f"response_type=code&"
        f"scope={urllib.parse.quote(scope_str)}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    
    auth_url_file = settings.CONFIG_DIR / "auth_url.txt"
    with open(auth_url_file, "w", encoding="utf-8") as f:
        f.write(auth_url)
        
    print(f"\nLink de autenticacao gerado:")
    print(auth_url)
    
    try:
        os.system(f'cmd.exe /c start "" "{auth_url}"')
    except Exception:
        pass
        
    print(f"\nServidor aguardando autorizacao em {redirect_uri} ...")
    server = HTTPServer(("localhost", 8080), OAuthHandler)
    
    while received_code is None:
        server.handle_request()
        
    print("\nCodigo de autorizacao recebido! Trocando por refresh token...")
    
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": received_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    resp = httpx.post(token_url, data=data)
    token_data = resp.json()
    
    if "error" in token_data:
        print(f"\nErro ao obter token: {token_data}")
        return
        
    credentials_payload = {
        "token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_uri": token_url,
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": SCOPES
    }
    
    with open(credentials_file, "w", encoding="utf-8") as f:
        json.dump(credentials_payload, f, indent=2)
        
    print("\n" + "=" * 60)
    print(f"SUCESSO! Credenciais salvas em: {credentials_file.name}")
    print("=" * 60)

if __name__ == "__main__":
    run_auth_flow()
