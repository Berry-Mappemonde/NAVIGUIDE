#!/usr/bin/env python3
import json
import unittest
from pathlib import Path
import importlib.util

SPEC = importlib.util.spec_from_file_location(
    "ask",
    Path(__file__).with_name("simulator-preview-ask.py"),
)
ask = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ask)


class AskOpen(unittest.TestCase):
    def test_missing_open_phrase(self):
        self.assertTrue(ask.asks_open({"prompt": "l'appli ne s'ouvre toujours pas"}))
        self.assertTrue(ask.asks_open({"prompt": "réouvre l'appli"}))
        self.assertTrue(ask.asks_open({"prompt": "ouvre le simulateur"}))

    def test_unrelated(self):
        self.assertFalse(ask.asks_open({"prompt": "il n'y a pas de cardinale pour courant"}))


if __name__ == "__main__":
    raise SystemExit(unittest.main())
