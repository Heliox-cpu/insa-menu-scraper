#!/usr/bin/env python3
"""
Lanceur principal du serveur web self-hosted INSA Lyon Menu.
"""

from insa_menu.server import start_server

if __name__ == "__main__":
    start_server(port=8080, host="0.0.0.0")
