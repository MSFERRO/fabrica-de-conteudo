import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import settings

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

def run_auth_flow():
    """
    Roda o fluxo OAuth 2.0 interativo para obter credenciais de acesso do YouTube.
    """
    print("=" * 60)
    print("     AUTENTICAÇÃO OAUTH 2.0 - FÁBRICA DE CONTEÚDO YOUTUBE")
    print("=" * 60)
    
    print("\nEste script gerará o token de acesso de longo prazo (refresh_token).")
    index_str = input("Qual o índice da credencial que deseja autenticar? (Pressione Enter para padrão): ").strip()
    
    if index_str:
        client_secrets_file = settings.CONFIG_DIR / f"client_secrets_{index_str}.json"
        credentials_file = settings.CONFIG_DIR / f"youtube_credentials_{index_str}.json"
    else:
        client_secrets_file = settings.CONFIG_DIR / "client_secrets.json"
        credentials_file = settings.CONFIG_DIR / "youtube_credentials.json"
        
    print(f"\nProcurando arquivo de segredos do cliente em: {client_secrets_file}")
    
    if not client_secrets_file.exists():
        print(f"\n⚠️ ERRO: O arquivo {client_secrets_file.name} não foi encontrado!")
        print("Você deve baixar este arquivo no console do Google Cloud (GCP) em API e Serviços > Credenciais > ID do cliente OAuth 2.0.")
        print(f"Salve o arquivo na pasta do projeto como: {client_secrets_file}")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secrets_file), 
        scopes=SCOPES
    )
    
    print("\nIniciando o servidor local para autenticação...")
    print("Um navegador deve se abrir para que você conceda as permissões ao canal do YouTube.")
    
    try:
        credentials = flow.run_local_server(
            port=0, 
            authorization_prompt_message="Acesse o link a seguir para autorizar a aplicação: {url}",
            success_message="Autenticação concluída com sucesso! Você já pode fechar esta aba do navegador."
        )
        
        with open(credentials_file, "w") as f:
            f.write(credentials.to_json())
            
        print("\n" + "=" * 60)
        print("🎉 SUCESSO!")
        print(f"Credenciais salvas com sucesso em: {credentials_file}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Ocorreu um erro durante a autenticação OAuth: {e}")

if __name__ == "__main__":
    run_auth_flow()
