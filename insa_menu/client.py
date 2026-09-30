"""
Client HTTP pour l'API officielle des restaurants de l'INSA Lyon.
"""

from __future__ import annotations
import base64
import datetime
import hashlib
import json
import logging
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_API_BASE = "https://menu-restaurants.insa-lyon.fr/API/public/v1/"
FALLBACK_BDE_URL = "https://utils.bde-insa-lyon.fr/menu/data/menu.json"
AUTH_SECRET = "85RrNDhZ9wz9"


def _create_ssl_context(verify: bool = True) -> ssl.SSLContext:
    """Crée un contexte SSL robuste, avec fallback certifi / unverified si nécessaire sur macOS."""
    if not verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass

    try:
        return ssl.create_default_context()
    except Exception:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


class InsaMenuClient:
    """
    Client pour communiquer avec l'API REST des restaurants de l'INSA Lyon (LiveSoft / Salamandre).
    Gère la signature temporelle MD5 requise pour l'en-tête d'authentification Basic UTok.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_API_BASE,
        timeout: int = 15,
        secret: str = AUTH_SECRET,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.secret = secret
        self._ssl_ctx = _create_ssl_context(verify=True)

    def _generate_auth_header(self) -> str:
        """
        Génère le header Basic Auth dynamique requis par l'API :
        Basic base64("UTok:" + md5(YYYYMMDDHHmm + secret))
        """
        now_str = datetime.datetime.now().strftime("%Y%m%d%H%M")
        token_src = f"{now_str}{self.secret}"
        token_hash = hashlib.md5(token_src.encode("utf-8")).hexdigest()
        token_auth = base64.b64encode(f"UTok:{token_hash}".encode("utf-8")).decode("ascii")
        return f"Basic {token_auth}"

    def _request(self, endpoint: str, binary: bool = False) -> Any:
        """Effectue une requête GET authentifiée vers l'API avec fallback SSL."""
        url = self.base_url + endpoint.lstrip("/")
        headers = {
            "Authorization": self._generate_auth_header(),
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        req = urllib.request.Request(url, headers=headers)

        def _do_open(ctx):
            with urllib.request.urlopen(req, context=ctx, timeout=self.timeout) as response:
                content = response.read()
                if binary:
                    return content
                return json.loads(content.decode("utf-8"))

        try:
            return _do_open(self._ssl_ctx)
        except urllib.error.URLError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                logger.warning("Vérification SSL échouée sur macOS, bascule sur SSL sans vérification locale.")
                self._ssl_ctx = _create_ssl_context(verify=False)
                return _do_open(self._ssl_ctx)
            logger.error("Erreur réseau lors de la requête %s: %s", url, e)
            raise
        except Exception as e:
            logger.error("Erreur lors de la requête %s: %s", url, e)
            raise

    def get_groups(self) -> List[Dict[str, Any]]:
        """Récupère les groupes d'établissements (L'Olivier, Pied du Saule, Le Restaurant INSA)."""
        return self._request("GroupeEtablissements")

    def get_etablissements(self, group_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère la liste des établissements actifs."""
        if group_id:
            return self._request(f"Etablissements/{group_id}")
        return self._request("Etablissements")

    def get_convives(self, eta_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère les types de convives (ex: Adulte)."""
        if eta_id:
            return self._request(f"Convives/{eta_id}")
        return self._request("Convives")

    def get_menus(self, eta_id: Optional[str] = None, con_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère la liste des services / formules repas."""
        if eta_id and con_id:
            return self._request(f"Menus/{eta_id}/{con_id}")
        return self._request("Menus")

    def get_allergens(self) -> List[Dict[str, Any]]:
        """Récupère le dictionnaire des allergènes officiels."""
        return self._request("Allergenes")

    def get_parameters(self) -> List[Dict[str, Any]]:
        """Récupère les dates d'ouverture et paramètres de la semaine en cours."""
        return self._request("Parametrage")

    def get_dish_detail(self, fit_id: str, con_id: str = "1") -> Dict[str, Any]:
        """
        Récupère la fiche technique complète d'un plat :
        ingrédients, allergènes détaillés, origines des viandes, photos et labels.
        """
        return self._request(f"Plat/{fit_id}/{con_id}")

    def get_semaine(
        self,
        eta_id: str,
        con_id: str,
        men_id: str,
        date_str: str,
    ) -> Dict[str, Any]:
        """
        Récupère les menus d'une semaine pour un établissement, un convive,
        un service (déjeuner/dîner) et une date (YYYY-MM-DD).
        """
        return self._request(f"Semaine/{eta_id}/{con_id}/{men_id}/{date_str}")

    def get_semaine_all(
        self,
        eta_id: str,
        con_id: str,
        men_id: str,
    ) -> Dict[str, Any]:
        """Récupère la semaine complète au format mobile (tous les jours dispos)."""
        return self._request(f"SemaineAll/{eta_id}/{con_id}/{men_id}")

    def get_pdf(
        self,
        eta_id: str,
        con_id: str,
        men_id: str,
        date_str: str,
    ) -> bytes:
        """Télécharge le fichier PDF officiel du menu de la semaine."""
        return self._request(f"Pdf/{eta_id}/{con_id}/{men_id}/{date_str}/PDF", binary=True)

    def get_bde_fallback(self) -> Dict[str, Any]:
        """Récupère les menus mis en cache par INSA-Utils / BDE INSA."""
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(FALLBACK_BDE_URL, headers=headers)
        with urllib.request.urlopen(req, context=self._ssl_ctx, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))
