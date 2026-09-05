"""
Logistics Automation Pipeline — SOMAP Backend
==============================================

Este script simula a automação de roteirização e despacho logístico:
1. Lê dados operacionais (Motorista e lista de coletas/entregas).
2. Autentica no SOMAP Backend (`/api/auth/login`) para obter o Token JWT.
3. Calcula a rota percorrida leg-a-leg via `pgRouting` (`/api/v1/routes`).
4. Gera relatórios consolidados de despacho e mensagem com link do Google Maps para o Motorista.

Uso:
    python3 -m scripts.logistics_automation
    ou
    python3 scripts/logistics_automation.py
"""

import asyncio
import os
import json
import httpx
from typing import List, Dict, Any

# Configurações do Backend (Lê do ambiente ou usa padrão local)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@somap.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "somap@2025")

# MASSA DE DADOS FICTÍCIA DA OPERAÇÃO
MOCK_OPERATIONAL_PAYLOAD: Dict[str, Any] = {
    "date": "2026-07-25",
    "driver": {
        "name": "Carlos Silva",
        "phone": "+55 41 99999-8888",
        "vehicle": "Caminhão Baú",
        "available_window": "08:30 às 11:30"
    },
    "origin_hq": {
        "name": "Centro de Distribuição / Sede",
        "address": "Av. do Batel, 1325 — Batel, Curitiba/PR",
        "coords": [-49.2838, -25.4428]  # [longitude, latitude]
    },
    "pickups": [
        {
            "id": 1,
            "item": "Sofá Retrátil 3 Lugares",
            "donor": "Maria Silva",
            "address": "Rua Bento Viana, Água Verde, Curitiba",
            "coords": [-49.2785, -25.4520]
        },
        {
            "id": 2,
            "item": "Mesa de Jantar 6 Cadeiras",
            "donor": "Roberto Santos",
            "address": "Rua Itacolomi, Portão, Curitiba",
            "coords": [-49.2930, -25.4715]
        },
        {
            "id": 3,
            "item": "Armário de Casal Desmontado",
            "donor": "Família Souza",
            "address": "Alameda Princesa Izabel, Bigorrilho, Curitiba",
            "coords": [-49.2955, -25.4350]
        }
    ]
}

class LogisticsAutomationService:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")

    async def authenticate(self, client: httpx.AsyncClient) -> str:
        """Autentica na API do SOMAP Backend e retorna o Token JWT."""
        login_url = f"{self.base_url}/api/auth/login"
        payload = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        
        response = await client.post(login_url, json=payload)
        if response.status_code != 200:
            raise RuntimeError(f"Falha ao autenticar no SOMAP Backend: {response.text}")
        
        data = response.json()
        token = data.get("token")
        if not token:
            raise RuntimeError("Token JWT não retornado pela API.")
        return token

    async def calculate_leg_route(self, client: httpx.AsyncClient, token: str, start: List[float], end: List[float]) -> Dict[str, Any]:
        """Calcula o menor caminho entre dois pontos usando o motor pgRouting da API."""
        route_url = f"{self.base_url}/api/v1/routes"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "start_point": start,
            "end_point": end
        }
        
        response = await client.post(route_url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return {"success": False, "message": response.text, "total_cost": 0.0}

    def generate_google_maps_url(self, origin: List[float], pickups: List[Dict[str, Any]]) -> str:
        """Gera URL direta com múltiplos waypoints para o Google Maps Navigation."""
        points = [origin] + [p["coords"] for p in pickups] + [origin]
        path_str = "/".join([f"{coords[1]},{coords[0]}" for coords in points])
        return f"https://www.google.com/maps/dir/{path_str}"

    async def run_pipeline(self, payload: Dict[str, Any] = MOCK_OPERATIONAL_PAYLOAD) -> Dict[str, Any]:
        """Executa a automação completa do início ao fim."""
        print("🚀 [Logistics Pipeline] Iniciando automação de roteirização...")
        print(f"📌 Motorista: {payload['driver']['name']} | Data: {payload['date']}")
        print(f"📌 Total de Paradas: {len(payload['pickups'])}")
        print("-" * 60)

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Autenticação
            print("🔑 Autenticando no SOMAP Backend...")
            token = await self.authenticate(client)
            print("✅ Autenticado com sucesso! Token JWT recebido.")
            print("-" * 60)

            # 2. Construção dos trechos (Legs)
            stops = [payload["origin_hq"]] + payload["pickups"] + [payload["origin_hq"]]
            total_cost_agg = 0.0
            leg_details = []

            print("🗺️ Calculando trechos otimizados via pgRouting...")
            for i in range(len(stops) - 1):
                from_stop = stops[i]
                to_stop = stops[i+1]
                
                from_name = from_stop.get("name") or from_stop.get("address")
                to_name = to_stop.get("name") or to_stop.get("address")
                
                route_res = await self.calculate_leg_route(
                    client, token, from_stop["coords"], to_stop["coords"]
                )
                
                cost = route_res.get("total_cost") or 0.0
                total_cost_agg += cost
                
                leg_details.append({
                    "leg": i + 1,
                    "from": from_name,
                    "to": to_name,
                    "cost": cost,
                    "success": route_res.get("success", False)
                })
                print(f"  └─ Trecho {i+1}: {from_name} ➔ {to_name} (Custo/Distância: {cost:.2f})")

            # 3. Gerar Links e Saídas
            gmaps_url = self.generate_google_maps_url(payload["origin_hq"]["coords"], payload["pickups"])

            # 4. Formatar Relatório de Gestão
            management_report = f"""
============================================================
📊 RELATÓRIO OPERACIONAL DE ROTAS — LOGÍSTICA SOMAP
============================================================
Data da Operação : {payload['date']}
Motorista        : {payload['driver']['name']} ({payload['driver']['phone']})
Veículo          : {payload['driver']['vehicle']}
Janela           : {payload['driver']['available_window']}
------------------------------------------------------------
RESUMO DAS ROTAS (Calculado pelo SOMAP Backend):
- Quantidade de Paradas : {len(payload['pickups'])}
- Custo Topológico Total: {total_cost_agg:.2f}
- Trajeto Completo       : Origem ➔ {len(payload['pickups'])} Pontos ➔ Origem
------------------------------------------------------------
ITINERÁRIO DETALHADO:
1. [ORIGEM]  {payload['origin_hq']['name']} ({payload['origin_hq']['address']})
"""
            for idx, p in enumerate(payload["pickups"], start=2):
                management_report += f"{idx}. [PARADA]  {p['item']} — {p['donor']} ({p['address']})\n"
            management_report += f"{len(payload['pickups'])+2}. [RETORNO] {payload['origin_hq']['name']}\n"
            management_report += f"""------------------------------------------------------------
🗺️ Link do Mapa no WebGIS SOMAP : {API_BASE_URL}/docs
📍 Link Navegação Google Maps    : {gmaps_url}
============================================================
"""

            # 5. Formatar Mensagem para o Motorista
            driver_whatsapp_msg = f"""
🚚 *LOGÍSTICA SOMAP — Rota do Dia ({payload['date']})*

Olá, *{payload['driver']['name'].split()[0]}*!
Sua rota para os atendimentos de hoje foi calculada com sucesso pelo nosso sistema geográfico.

📋 *Sua Agenda de Hoje ({payload['driver']['available_window']}):*
1. 🏢 *Saída*: {payload['origin_hq']['name']}
"""
            for idx, p in enumerate(payload["pickups"], start=2):
                driver_whatsapp_msg += f"{idx}. 📦 *Parada*: {p['item']} ({p['address']})\n"
            driver_whatsapp_msg += f"{len(payload['pickups'])+2}. 🏢 *Retorno*: {payload['origin_hq']['name']}\n\n"
            driver_whatsapp_msg += f"📲 *Clique no link abaixo para iniciar a navegação no Google Maps:*\n{gmaps_url}\n\n"
            driver_whatsapp_msg += "Bom trabalho! Tenha um ótimo trajeto! 🙏"

            print("\n" + management_report)
            print("📱 [MENSAGEM PARA O MOTORISTA]:")
            print(driver_whatsapp_msg)

            return {
                "success": True,
                "total_cost": total_cost_agg,
                "management_report": management_report,
                "driver_whatsapp_msg": driver_whatsapp_msg,
                "google_maps_url": gmaps_url,
                "legs": leg_details
            }

async def main():
    service = LogisticsAutomationService()
    await service.run_pipeline()

if __name__ == "__main__":
    asyncio.run(main())
