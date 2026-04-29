import asyncio
import html
import re
from typing import Any

import httpx
from loguru import logger

from config.settings import settings

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


class CRMClient:
    def __init__(self):
        # Official API mode (Bearer token).
        self.base_url = settings.receitaface_base_url or settings.medipharma_base_url
        self.token = settings.receitaface_token or settings.medipharma_token
        self.search_path = settings.receitaface_recipe_search_path
        self.query_param = settings.receitaface_query_param

        # Temporary session mode (cookie/csrf + panel endpoints).
        self.use_session = settings.receitaface_use_session
        self.session_cookie = settings.receitaface_session_cookie
        self.csrf_token = settings.receitaface_csrf_token
        self.list_path = settings.receitaface_list_path
        self.details_path = settings.receitaface_details_path
        self.referer_path = settings.receitaface_referer_path
        self.page_length = settings.receitaface_page_length

    def _use_mock(self) -> bool:
        return settings.receitaface_mock_enabled or (
            settings.app_env == "development" and not self.token and not self.session_cookie
        )

    def _use_session_mode(self) -> bool:
        return bool(self.use_session or self.session_cookie)

    @staticmethod
    def _digits(value: str) -> str:
        return "".join(ch for ch in value if ch.isdigit())

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
        # Mirrors the panel pattern to improve compatibility with ReceitaFace DataTables backend.
        column_names = [
            "id",
            "prescritor",
            "created_at",
            "finalization_date",
            "paciente",
            "valor_total",
            "situacao",
            "atendente",
            "",
        ]

        params: dict[str, Any] = {
            "draw": "1",
            "start": "0",
            "length": str(self.page_length),
            "search[value]": query,
            "search[regex]": "false",
            "order[0][column]": "0",
            "order[0][dir]": "asc",
            "order[0][name]": "",
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
            self._clean_text(match)
            for match in re.findall(r"<h4[^>]*class=\"[^\"]*font-semibold[^\"]*\"[^>]*>(.*?)</h4>", details_html, re.IGNORECASE | re.DOTALL)
        ]
        item_titles = [title for title in item_titles if title and not title.lower().startswith("nenhum")]

        dosage_lines = [
            self._clean_text(match)
            for match in re.findall(r"<p[^>]*class=\"[^\"]*text-sm[^\"]*\"[^>]*>(.*?)</p>", details_html, re.IGNORECASE | re.DOTALL)
        ]
        dosage_lines = [line for line in dosage_lines if line and not line.lower().startswith("tipo:")]

        formula = " + ".join(item_titles[:3]) if item_titles else "Formula nao identificada no detalhe"
        dosage = dosage_lines[0] if dosage_lines else "Posologia nao informada"

        if fallback_row:
            patient = patient or str(fallback_row.get("paciente", ""))

        return {
            "id": str(recipe_id),
            "patient": patient,
            "formula": formula,
            "dosage": dosage,
        }

    async def _search_recipe_via_session(self, query: str) -> dict:
        list_headers = self._build_session_headers("application/json, text/javascript, */*; q=0.01")
        detail_headers = self._build_session_headers("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        list_params = self._build_datatables_params(query)

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            list_resp = await client.get(f"{self.base_url}{self.list_path}", headers=list_headers, params=list_params)
            list_resp.raise_for_status()
            content_type = list_resp.headers.get("content-type", "").lower()
            if "application/json" not in content_type:
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
            details_content_type = details_resp.headers.get("content-type", "").lower()
            if "text/html" not in details_content_type:
                return {"found": False, "recipe": None, "error": "session_expired"}

            recipe = self._extract_recipe_from_html(recipe_id, details_resp.text, row)
            return {"found": True, "recipe": recipe}

    async def _search_recipe_via_token(self, query: str) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.base_url}{self.search_path}",
                headers={"Authorization": f"Bearer {self.token}"},
                params={self.query_param: query},
            )
            resp.raise_for_status()
            return resp.json()

    async def _mock_search_recipe(self, query: str) -> dict:
        if settings.receitaface_mock_delay_ms > 0:
            await asyncio.sleep(settings.receitaface_mock_delay_ms / 1000)

        q = (query or "").strip()
        q_lower = q.lower()
        q_digits = self._digits(q)

        if q_lower in {"timeout", "simular timeout", "simular_timeout"}:
            logger.warning("[MOCK CRM] timeout scenario requested")
            return {"found": False, "recipe": None, "error": "timeout"}

        if q_lower in {"indisponivel", "simular indisponivel", "simular_indisponivel"}:
            logger.warning("[MOCK CRM] service_unavailable scenario requested")
            return {"found": False, "recipe": None, "error": "service_unavailable"}

        for recipe in MOCK_RECIPES:
            id_match = q_lower == recipe["id"].lower()
            name_match = q_lower in recipe["patient"].lower()
            cpf_match = bool(q_digits) and q_digits == recipe["cpf"]
            if id_match or name_match or cpf_match:
                logger.info(f"[MOCK CRM] recipe matched: {recipe['id']}")
                return {
                    "found": True,
                    "recipe": {
                        "id": recipe["id"],
                        "patient": recipe["patient"],
                        "formula": recipe["formula"],
                        "dosage": recipe["dosage"],
                    },
                }

        logger.info("[MOCK CRM] no recipe matched")
        return {"found": False, "recipe": None}

    async def search_recipe(self, query: str) -> dict:
        if self._use_mock():
            return await self._mock_search_recipe(query)

        try:
            if self._use_session_mode():
                return await self._search_recipe_via_session(query)
            return await self._search_recipe_via_token(query)
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            logger.error(f"CRM search_recipe failed with status {status}: {e}")
            if status in {401, 403}:
                return {"found": False, "recipe": None, "error": "session_expired"}
            if status in {429, 500, 502, 503, 504}:
                return {"found": False, "recipe": None, "error": "upstream_unavailable"}
            return {"found": False, "recipe": None}
        except httpx.TimeoutException as e:
            logger.error(f"CRM search_recipe timeout: {e}")
            return {"found": False, "recipe": None, "error": "timeout"}
        except Exception as e:
            logger.error(f"CRM search_recipe failed: {e}")
            return {"found": False, "recipe": None}


crm_client = CRMClient()
