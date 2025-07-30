import requests
import json
import time

# CONFIGURAÇÕES DO APP
CLIENT_ID = "6980494754793784"
CLIENT_SECRET = "ORwhdIq9XM3sotwnK406q6bj2cAgf1xJ"
TOKEN_FILE = "access_token.json"

def carregar_tokens():
    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Arquivo de token não encontrado.")
        return None

def salvar_tokens(dados_token):
    with open(TOKEN_FILE, "w") as f:
        json.dump(dados_token, f, indent=4)
    print("💾 Tokens atualizados com sucesso.")

def renovar_token(refresh_token):
    url = "https://api.mercadolibre.com/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(url, data=payload, headers=headers)

    if response.status_code == 200:
        novo_token = response.json()
        print("✅ Novo access token gerado.")
        salvar_tokens(novo_token)
        return novo_token["access_token"]
    else:
        print("❌ Erro ao renovar token:", response.status_code)
        print(response.text)
        return None

def obter_access_token():
    tokens = carregar_tokens()
    if not tokens:
        return None

    # Simulação de verificação de expiração (aqui você pode usar o campo "expires_in")
    expirado = True  # forçamos renovação sempre nesse exemplo

    if expirado:
        print("🔄 Token expirado, tentando renovar...")
        return renovar_token(tokens["refresh_token"])
    else:
        return tokens["access_token"]

# EXEMPLO DE USO
if __name__ == "__main__":
    token = obter_access_token()
    if token:
        print("🔐 Access Token atual:", token)
