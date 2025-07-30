import requests
import json
from datetime import datetime, timedelta, timezone, date
from dateutil import parser
from collections import defaultdict
import os
# --- CONFIGURAÇÕES ---

# Configurações do Mercado Livre (OAuth e API)
CLIENT_ID = "6980494754793784"
CLIENT_SECRET = "ORwhdIq9XM3sotwnK406q6bj2cAgf1xJ"
#TOKEN_FILE = "access_token.json"  # arquivo local do token
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "access_token.json")
BASE_URL = "https://api.mercadolibre.com/"
SELLER_ID = "632182619"
LIMIT = 51
MAX_TOTAL = 5000

# Configurações do UltraMsg (envio WhatsApp)
ULTRAMSG_TOKEN = "d0grrqj11objkhe8"
NUMERO_DESTINO = "+5515998401519"


# --- FUNÇÕES DE GERENCIAMENTO DE TOKEN ---

def carregar_tokens():
    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Arquivo de token não encontrado.")
        return None

def salvar_tokens(dados_token):
    dados_token["created_at"] = datetime.now(timezone.utc).isoformat()
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

def token_expirado(token_data):
    try:
        criado_em = datetime.fromisoformat(token_data["created_at"])
        expira_em = criado_em + timedelta(seconds=token_data["expires_in"])
        return datetime.now(timezone.utc) >= expira_em
    except Exception:
        return True  # Se faltar info, considera expirado

def obter_access_token():
    tokens = carregar_tokens()
    if not tokens:
        return None

    if token_expirado(tokens):
        print("🔄 Token expirado, tentando renovar...")
        return renovar_token(tokens["refresh_token"])
    else:
        print("⏳ Token ainda válido.")
        return tokens["access_token"]


# --- FUNÇÕES DE CONSULTA E RESUMO ---

def get_orders(access_token, offset=0):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    url = f"{BASE_URL}orders/search"
    params = {
        "seller": SELLER_ID,
        "limit": LIMIT,
        "offset": offset
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def paginate_orders(access_token):
    all_orders = []
    offset = 0

    while True:
        data = get_orders(access_token, offset)
        pedidos = data.get("results", [])

        if not pedidos:
            break

        all_orders.extend(pedidos)

        if len(pedidos) < LIMIT or len(all_orders) >= MAX_TOTAL:
            break

        offset += LIMIT

    if len(all_orders) > MAX_TOTAL:
        all_orders = all_orders[:MAX_TOTAL]

    return all_orders

def gerar_resumo_e_mensagem(pedidos):
    hoje = date.today()

    faturamento_hoje = 0.0
    pedidos_aprovados_hoje = 0
    produtos_faturamento = defaultdict(float)
    produtos_quantidade = defaultdict(int)

    for pedido in pedidos:
        pagamentos = pedido.get("payments", [])
        for pagamento in pagamentos:
            if pagamento.get("status") == "approved":
                data_aprov_str = pagamento.get("date_approved")
                if data_aprov_str:
                    data_aprov = parser.isoparse(data_aprov_str).date()
                    if data_aprov == hoje:
                        faturamento_hoje += pedido.get("total_amount", 0.0)
                        pedidos_aprovados_hoje += 1

                        for item in pedido.get("order_items", []):
                            nome = item.get("item", {}).get("title", "Desconhecido")
                            quantidade = item.get("quantity", 1)
                            preco_unitario = item.get("unit_price", 0.0)
                            produtos_faturamento[nome] += quantidade * preco_unitario
                            produtos_quantidade[nome] += quantidade
                break

    ticket_medio = faturamento_hoje / pedidos_aprovados_hoje if pedidos_aprovados_hoje > 0 else 0.0
    top_3_produtos = sorted(produtos_faturamento.items(), key=lambda x: x[1], reverse=True)[:3]

    faturamento_formatado = f"R$ {faturamento_hoje:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    ticket_medio_formatado = f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    mensagem = f"""📊 *Resumo Mercado Livre – {hoje.strftime('%d/%m/%Y')}*

✅ *Faturamento:* {faturamento_formatado}
🛍 *Pedidos:* {pedidos_aprovados_hoje} 
🎟 *Ticket Médio:* {ticket_medio_formatado}

🔝 *Mais vendidos:*
"""

    for nome, _ in top_3_produtos:
        quantidade = produtos_quantidade[nome]
        mensagem += f"\n- {nome} ({quantidade} un.)"

    mensagem += "\n\n📈 Veja o dashboard:\nhttps://app.powerbi.com/view?r=eyJrIjoiMGY2NzExOGYtMjJlMi00MTA1LTg4MDktMDQyMDFiMjAyY2Y2IiwidCI6Ijg5OWQ1NWYxLWEzNGYtNDNlNS05MTg0LTI0ZGE4YjM5MGJhZSJ9"

    return mensagem

# --- FUNÇÃO DE ENVIO DE MENSAGEM ---

def enviar_mensagem(token_ultramsg, numero_destino, mensagem):
    url = "https://api.ultramsg.com/instance135947/messages/chat"
    payload = {
        "token": token_ultramsg,
        "to": numero_destino,
        "body": mensagem
    }
    response = requests.post(url, json=payload)
    print("Status envio mensagem:", response.status_code)
    print(response.text)

# --- FLUXO PRINCIPAL ---

def main():
    access_token = obter_access_token()
    if not access_token:
        print("❌ Não foi possível obter token válido. Abortando.")
        return

    pedidos = paginate_orders(access_token)
    mensagem = gerar_resumo_e_mensagem(pedidos)
    enviar_mensagem(ULTRAMSG_TOKEN, NUMERO_DESTINO, mensagem)

if __name__ == "__main__":
    main()
