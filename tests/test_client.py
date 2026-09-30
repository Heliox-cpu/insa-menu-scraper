"""
Tests unitaires pour le client InsaMenuClient (génération d'authentification et structure).
"""

import base64
import unittest
from insa_menu.client import InsaMenuClient, AUTH_SECRET


class TestInsaMenuClient(unittest.TestCase):
    def test_auth_header_format(self):
        client = InsaMenuClient(secret=AUTH_SECRET)
        auth_header = client._generate_auth_header()

        self.assertTrue(auth_header.startswith("Basic "))
        b64_part = auth_header.split(" ")[1]
        decoded = base64.b64decode(b64_part).decode("ascii")

        self.assertTrue(decoded.startswith("UTok:"))
        token_hash = decoded.split(":")[1]
        self.assertEqual(len(token_hash), 32)  # Longueur d'un MD5 hex standard

    def test_live_groups(self):
        """Teste l'appel direct à l'API officielle."""
        client = InsaMenuClient()
        groups = client.get_groups()
        self.assertIsInstance(groups, list)
        self.assertGreaterEqual(len(groups), 2)
        group_names = [g.get("NomGrpEta") for g in groups]
        self.assertTrue(any("INSA" in name for name in group_names))


if __name__ == "__main__":
    unittest.main()
