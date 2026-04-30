"""
Cliente CRM — integração com NanoCare Receitas API.

Endpoint base:  {NANOCARE_API_URL}/integrations/recipes
Autenticação:   Authorization: Bearer {NANOCARE_API_TOKEN}

Busca suportada:
  - UUID      → GET /integrations/recipes/{uuid}
  - CPF       → GET /integrations/recipes?cpf=12345678900
  - Nome      → GET /integrations/recipes?patientName=Maria

Modos em ordem de prioridade:
  1. NanoCare API (token oficial)
  2. Sessão web — ReceitaFace (workaround legado)
  3. Mock (desenvolvimento sem credenciais)
"""

import asyncio
import html
import re
from typing import Any

import httpx
from loguru import logger

from config.settings import settings

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_RECIPES_PATH = "/integrations/recipes"

# Status que permitem prosseguir para pagamento
_ACTIVE_STATUS = {"active"}

# Mapeamento de status → código de erro interno
_STATUS_ERRORS: dict[str, str] = {
    "expired":   "recipe_expired",
    "used":      "recipe_used",
    "cancelled": "recipe_cancelled",
    "pending":   "recipe_pending",
    "blocked":   "recipe_blocked",
}

# ---------------------------------------------------------------------------
# Mock — apenas em desenvolvimento
# ---------------------------------------------------------------------------

MOCK_RECIPES = [
    {
        "id": "RX-MOCK-001",
        "patient": "Maria Silva",
        "cpf": "11122233344",
        "formula": "Progesterona 100mg + DHEA 25mg",
        "dosage": "1 capsula/dia pela manha",
    },
    {
        "id": "RX-MOCK-002",
        "patient": "Joao Souza",
        "cpf": "98765432100",
        "formula": "Melatonina 3mg",
        "dosage": "1 capsula a noite",
    },
    {
        "id": "RX-MOCK-003",
        "patient": "Ana Lima",
        "cpf": "12312312312",
        "formula": "Vitamina D 2000 UI",
        "dosage": "1 capsula/dia",
    },
]


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------


class CRMClient:
    def __init__(self) -> None:
        # --- Modo 1: NanoCare API oficial ---
        self.nanocare_url = (settings.nanocare_api_url or "").rstrip("/")
        self.nanocare_token = (settings.nanocare_api_token or "").strip()

        # --- Modo 2: sessão web (legado) ---
        self.use_session = settings.receitaface_use_session
        self.session_cookie = settings.receitaface_session_cookie
        self.csrf_token = settings.receitaface_csrf_token
        self.base_url = (settings.receitaface_base_url or "").rstrip("/")
        self.list_path = settings.receitaface_list_path
        self.details_path = settings.receitaface_details_path
        self.referer_path = settings.receitaface_referer_path
        self.page_length = settings.receitaface_page_length

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _use_mock(self) -> bool:
        return settings.receitaface_mock_enabled or (
            settings.app_env == "development"
            and not self.nanocare_token
            and not self.session_cookie
        )

    def _use_session_mode(self) -> bool:
        return bool(self.use_session or self.session_cookie)

    @property
    def _recipes_base(self) -> str:
        return f"{self.nanocare_url}{_RECIPES_PATH}"

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.nanocare_token}"}

    @staticmethod
    def _digits(value: str) -> str:
        return re.sub(r"\D", "", value)

    @staticmethod
    def _map_recipe(data: dict) -> dict:
        """Mapeia detalhe da NanoCare API para o formato interno do agente."""
        patient = data.get("patient") or {}
        return {
            "id": str(data.get("id", "")),
            "patient": (patient.get("name") or "Paciente nao identificado").strip(),
            "cpf": (patient.get("cpf") or "").strip(),
            "formula": (data.get("formula") or "Formula nao identificada").strip(),
            "dosage": (data.get("dosage") or "Posologia nao informada").strip(),
            "status": data.get("status", ""),
            "prescriber": ((data.get("prescriber") or {}).get("name") or "").strip(),
            "expires_at": data.get("expires_at"),
        }

    # ------------------------------------------------------------------
    # Modo 1: NanoCare API oficial
    # ------------------------------------------------------------------

    async def _fetch_by_id(self, recipe_id: str) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self._recipes_base}/{recipe_id}",
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        if not data.get("found"):
            return {"found": False, "recipe": None}

        recipe_data = data["recipe"]
        return self._check_status_and_return(recipe_data)

    async def _search_list(self, params: dict[str, str]) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                self._recipes_base,
                headers=self._auth_headers(),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def _search_and_fetch(self, params: dict[str, str]) -> dict:
        data = await self._search_list(params)

        if not data.get("found"):
            return {"found": False, "recipe": None}

        recipes: list[dict] = data.get("recipes", [])
        if not recipes:
            return {"found": False, "recipe": None}

        # Prioriza receitas ativas
        active = [r for r in recipes if r.get("status") == "active"]

        if not active:
            first_status = recipes[0].get("status", "")
            error = _STATUS_ERRORS.get(first_status, f"recipe_{first_status}")
            logger.info(f"[CRM] Receitas encontradas mas nenhuma ativa — status={first_status}")
            return {"found": False, "recipe": None, "error": error}

        # Pega a mais recente dentre as ativas (API já retorna ordenado por data desc)
        return await self._fetch_by_id(str(active[0]["id"]))

    def _check_status_and_return(self, recipe_data: dict) -> dict:
        status = recipe_data.get("status", "")
        if status not in _ACTIVE_STATUS:
            error = _STATUS_ERRORS.get(status, f"recipe_{status}")
            logger.info(f"[CRM] Receita {recipe_data.get('id')} — status={status}")
            return {"found": False, "recipe": None, "error": error}

        recipe = self._map_recipe(recipe_data)
        logger.info(f"[CRM] Receita ativa: {recipe['id']} — {recipe['patient']}")
        return {"found": True, "recipe": recipe}

    async def _search_nanocare(self, query: str) -> dict:
        clean = query.strip()

        if _UUID_RE.match(clean):
            return await self._fetch_by_id(clean)

        digits = self._digits(clean)
        if len(digits) == 11:
            return await self._search_and_fetch({"cpf": digits})

        return await self._search_and_fetch({"patientName": clean})

    # ------------------------------------------------------------------
    # Modo 2: sessão web — ReceitaFace (legado)
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_text(value: str) -> str:
        text = re.sub(r"<[^>]+>", " ", value)
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def _build_session_headers(self, accept: str) -> dict[str, str]:
        headers = {
            "Accept": accept,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}{self.referer_path}",
        }
        if self.session_cookie:
            headers["Cookie"] = self.session_cookie
        if self.csrf_token:
            headers["X-CSRF-Token"] = self.csrf_token
        return headers

    def _build_datatables_params(self, query: str) -> dict[str, Any]:
        column_names = ["id", "prescritor", "created_at", "finalization_date",
                        "paciente", "valor_total", "situacao", "atendente", ""]
        params: dict[str, Any] = {
            "draw": "1", "start": "0", "length": str(self.page_length),
            "search[value]": query, "search[regex]": "false",
            "order[0][column]": "0", "order[0][dir]": "asc", "order[0][name]": "",
        }
        for idx, name in enumerate(column_names):
            params[f"columns[{idx}][data]"] = name
            params[f"columns[{idx}][name]"] = ""
            params[f"columns[{idx}][searchable]"] = "true"
            params[f"columns[{idx}][orderable]"] = "false" if idx == 8 else "true"
            params[f"columns[{idx}][search][value]"] = ""
            params[f"columns[{idx}][search][regex]"] = "false"
        return params

    def _select_best_row(self, rows: list[dict], query: str) -> dict | None:
        if not rows:
            return None
        q = (query or "").strip().lower()
        q_digits = self._digits(q)
        for row in rows:
            row_id = str(row.get("id", "")).lower()
            paciente = str(row.get("paciente", "")).lower()
            if q and (q == row_id or q in paciente):
                return row
            if q_digits and q_digits == self._digits(str(row.get("paciente", ""))):
                return row
        return rows[0]

    def _extract_recipe_from_html(self, recipe_id: str, details_html: str, fallback_row: dict | None) -> dict:
        patient_match = re.search(r"Paciente:\s*<span[^>]*>(.*?)</span>", details_html, re.IGNORECASE | re.DOTALL)
        if patient_match:
            patient = self._clean_text(patient_match.group(1))
        else:
            patient_line = re.search(r"Paciente:\s*([^<\n]+)", details_html, re.IGNORECASE)
            patient = self._clean_text(patient_line.group(1)) if patient_line else "Paciente nao identificado"

        item_titles = [
            self._clean_text(m)
            for m in re.findall(r"<h4[^>]*class=\"[^\"]*font-semibold[^\"]*\"[^>]*>(.*?)</h4>", details_html, re.IGNORECASE | re.DOTALL)
        ]
        item_titles = [t for t in item_titles if t and not t.lower().startswith("nenhum")]
        dosage_lines = [
            self._clean_text(m)
            for m in re.findall(r"<p[^>]*class=\"[^\"]*text-sm[^\"]*\"[^>]*>(.*?)</p>", details_html, re.IGNORECASE | re.DOTALL)
        ]
        dosage_lines = [line for line in dosage_lines if line and not line.lower().startswith("tipo:")]

        formula = " + ".join(item_titles[:3]) if item_titles else "Formula nao identificada"
        dosage = dosage_lines[0] if dosage_lines else "Posologia nao informada"
        if fallback_row:
            patient = patient or str(fallback_row.get("paciente", ""))
        return {"id": str(recipe_id), "patient": patient, "formula": formula, "dosage": dosage, "cpf": ""}

    async def _search_recipe_via_session(self, query: str) -> dict:
        list_headers = self._build_session_headers("application/json, text/javascript, */*; q=0.01")
        detail_headers = self._build_session_headers("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        list_params = self._build_datatables_params(query)

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            list_resp = await client.get(f"{self.base_url}{self.list_path}", headers=list_headers, params=list_params)
            list_resp.raise_for_status()
            if "application/json" not in list_resp.headers.get("content-type", "").lower():
                return {"found": False, "recipe": None, "error": "session_expired"}

            list_payload = list_resp.json()
            rows = list_payload.get("data", [])
            row = self._select_best_row(rows, query)
            if not row:
                return {"found": False, "recipe": None}

            recipe_id = str(row.get("id", "")).strip()
            if not recipe_id:
                return {"found": False, "recipe": None}

            details_resp = await client.get(
                f"{self.base_url}{self.details_path}",
                headers=detail_headers,
                params={"id": recipe_id},
            )
            details_resp.raise_for_status()
            if "text/html" not in details_resp.headers.get("content-type", "").lower():
                return {"found": False, "recipe": None, "error": "session_expired"}

            recipe = self._extract_recipe_from_html(recipe_id, details_resp.text, row)
            return {"found": True, "recipe": recipe}

    # ------------------------------------------------------------------
    # Modo 3: mock
    # ------------------------------------------------------------------

    async def _mock_search_recipe(self, query: str) -> dict:
        if settings.receitaface_mock_delay_ms > 0:
            await asyncio.sleep(settings.receitaface_mock_delay_ms / 1000)

        q = (query or "").strip()
        q_lower = q.lower()
        q_digits = self._digits(q)

        if q_lower in {"timeout", "simular timeout", "simular_timeout"}:
            logger.warning("[MOCK CRM] timeout scenario")
            return {"found": False, "recipe": None, "error": "timeout"}

        if q_lower in {"indisponivel", "simular indisponivel", "simular_indisponivel"}:
            logger.warning("[MOCK CRM] service_unavailable scenario")
            return {"found": False, "recipe": None, "error": "service_unavailable"}

        for recipe in MOCK_RECIPES:
            if (
                q_lower == recipe["id"].lower()
                or q_lower in recipe["patient"].lower()
                or (q_digits and q_digits == recipe["cpf"])
            ):
                logger.info(f"[MOCK CRM] matched: {recipe['id']}")
                return {"found": True, "recipe": {k: v for k, v in recipe.items() if k != "cpf"}}

        logger.info("[MOCK CRM] no match")
        return {"found": False, "recipe": None}

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    async def search_recipe(self, query: str) -> dict:
        if self._use_mock():
            return await self._mock_search_recipe(query)

        try:
            if self.nanocare_token:
                return await self._search_nanocare(query)
            if self._use_session_mode():
                return await self._search_recipe_via_session(query)
            logger.error("[CRM] Nenhuma autenticação configurada (NANOCARE_API_TOKEN vazio)")
            return {"found": False, "recipe": None, "error": "service_unavailable"}

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            logger.error(f"[CRM] HTTP {status} na busca de receita")
            if status in {401, 403}:
                return {"found": False, "recipe": None, "error": "unauthorized"}
            if status in {429, 500, 502, 503, 504}:
                return {"found": False, "recipe": None, "error": "service_unavailable"}
            return {"found": False, "recipe": None}
        except httpx.TimeoutException:
            logger.error("[CRM] Timeout na busca de receita")
            return {"found": False, "recipe": None, "error": "timeout"}
        except Exception as exc:
            logger.error(f"[CRM] Erro inesperado: {exc}")
            return {"found": False, "recipe": None}


crm_client = CRMClient()
