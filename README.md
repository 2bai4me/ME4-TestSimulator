# ME4 TestSimulator

Macro-basierter UI-Test-Simulator für ME4 — Record/Replay mit Element-Erkennung.

## Konzept

Ein externes Tool, das menschliche Interaktion mit Web-UIs simuliert:
- **Record**: Zeichnet Mausklicks, Tastatureingaben und UI-Element-Interaktionen auf
- **Replay**: Spielt aufgezeichnete Makros ab
- **Script**: Führt programmierte Testabläufe aus (element-basiert, nicht positionsbasiert)
- **Autorun**: Automatisiert SMproducer-Workflows von Quelle bis Entscheidungspunkt

## Technologie-Stack

- **PyAutoGUI**: Low-level Maus/Tastatur-Steuerung (positionsbasiert)
- **Playwright**: Web-Element-Interaktion (element-basiert, zuverlässiger)
- **Python 3.11+**: Steuerungslogik und CLI

## Warum Playwright statt nur PyAutoGUI?

- Element-Selektoren statt Bildschirmkoordinaten → unabhängig von Fenstergröße
- Wartet automatisch auf Elemente (kein `sleep()`)
- Kann Page-State auslesen (Texte, Werte, Attribut-Präsenz)
- Headless-Modus für CI/CD

## Projektstruktur

```
ME4-TestSimulator/
├── README.md
├── requirements.txt
├── testsimulator/
│   ├── __init__.py
│   ├── recorder.py      # Macro-Aufzeichnung
│   ├── player.py        # Macro-Wiedergabe
│   ├── webdriver.py     # Playwright-Browser-Steuerung
│   ├── autorun.py       # SMproducer-spezifische Workflows
│   └── cli.py           # Kommandozeilen-Interface
├── macros/              # Gespeicherte Makros (JSON)
└── tests/               # Test-Suiten
```

## SMproducer Autorun Workflow

1. Öffne SMproducer (http://localhost:5173)
2. Wähle Kanal
3. Starte neues Projekt
4. Füge YouTube-Quelle ein
5. **STOPP bei Entscheidungspunkt**: Thema-Auswahl (Step 3)
6. Warte auf Benutzer-Input
7. Fahre fort nach Benutzer-Entscheidung
