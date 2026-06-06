# ME4 TestSimulator — Projektspezifikation (CIO)

> **CIO Reference**: ITIL 4 Service Value System — Design & Transition
> **COBIT 2019**: BAI03 (Managed Solutions Identification & Build)
> **bB Tag**: DEV, ARCHITECTURE

## 1. Executive Summary

ME4 TestSimulator ist ein Macro-basierter UI-Test-Automat, der menschliche Interaktion mit Web-UIs aufzeichnet und reproduziert. Primäres Ziel: Automatisierte Regressionstests für ME4-Services (insb. SMproducer 3.0), die ohne manuelle Eingriffe auskommen — außer an definierten Entscheidungspunkten (Human-in-the-Loop).

## 2. CIO-Architektur-Entscheidungen

### DEC-001: Playwright als primärer Web-Automation-Provider

| Kriterium | Playwright | Selenium | PyAutoGUI (nur) |
|-----------|-----------|----------|------------------|
| Element-Selektoren | ✅ CSS/XPath/Text/Role | ✅ | ❌ nur Koordinaten |
| Auto-Wait | ✅ built-in | ✅ (mit Explicit Wait) | ❌ sleep() nötig |
| Headless | ✅ | ✅ | ❌ |
| Page-State lesen | ✅ `page.text_content()` | ✅ | ❌ |
| CI/CD-tauglich | ✅ | ✅ | ❌ (braucht Display) |
| Cross-Browser | ✅ Chromium/Firefox/WebKit | ✅ | N/A |
| ME4-Erfahrung | ✅ SMproducer nutzt bereits Playwright | ⚠️ | ❌ |

**Entscheidung**: Playwright als primärer Provider. PyAutoGUI NUR für Nicht-Browser-UIs (Desktop-Tools).

### DEC-002: JSON-Makroformat mit Schema-Validierung

```json
{
  "version": "1.0",
  "metadata": {
    "name": "smproducer-full-workflow",
    "created": "2026-06-06T18:30:00Z",
    "browser": "chromium",
    "viewport": {"width": 1920, "height": 1080}
  },
  "steps": [
    {
      "id": 1,
      "action": "navigate",
      "url": "http://localhost:5173",
      "description": "Öffne SMproducer"
    },
    {
      "id": 2,
      "action": "click",
      "selector": "button[data-testid='new-project']",
      "description": "Neues Projekt starten"
    }
  ]
}
```

**Entscheidung**: JSON (nicht YAML) — Parsing ohne Zusatzabhängigkeit, direkt in Python `json` Modul, Playwright-native test fixtures nutzbar.

### DEC-003: CLI-first Architektur

- **Phase 1**: CLI (`testsimulator record|replay|autorun`)
- **Phase 2**: REST-API (FastAPI) für Remote-Triggering
- **Phase 3**: Web-UI (optional, nur bei Bedarf)

**Entscheidung**: CLI-first — minimale Abhängigkeiten, direkte Einbindung in CI/CD, kein Server-Management nötig.

### DEC-004: Service-orientierte interne Architektur

Auch als Einzeltool folgt TestSimulator dem ME4-SOA-Pattern:
- `recorder.py` — Recording-Service (Capture-Layer)
- `player.py` — Replay-Service (Execution-Layer)
- `webdriver.py` — Browser-Abstraktion (Playwright-Wrapper)
- `autorun.py` — SMproducer-spezifische Workflows (Orchestration-Layer)
- `cli.py` — CLI-Interface (Presentation-Layer)

### DEC-005: i18n ab Tag 1

Gemäß ME4 i18n Standard (siehe `me4-i18n-developer-guide.md`):
- `manifest.json` mit Sprachdefinitionen
- `i18n/` Ordner mit `de.json`, `en.json`
- CLI-Output per `--lang de|en` steuerbar
- Default: `de` (ME4-Primärsprache)

## 3. Technologie-Stack (durch CIO freigegeben)

| Komponente | Technologie | Version | Begründung |
|-----------|-------------|---------|------------|
| Runtime | Python | 3.11+ | ME4-Standard, auf TOWER installiert |
| Web-Automation | Playwright | ≥1.45 | Element-basiert, Headless, CI-ready |
| Fallback-Automation | PyAutoGUI | ≥0.9 | Nur für Desktop-UI-Tests |
| Schema-Validierung | jsonschema | ≥4.20 | JSON-Makroformat prüfen |
| CLI-Framework | click | ≥8.1 | Schlank, typsicher, ME4-erprobt |
| Testing | pytest + pytest-playwright | aktuell | Playwright-Integration für E2E |
| Linting | ruff | aktuell | ME4-Standard |
| Type-Checking | mypy | aktuell | Optional aber empfohlen |

## 4. Projektstruktur

```
ME4-TestSimulator/
├── README.md
├── SPEC.md                          # Diese Datei
├── requirements.txt
├── pyproject.toml                   # Projekt-Metadaten + Tool-Config
├── i18n/
│   ├── manifest.json
│   ├── de.json
│   └── en.json
├── testsimulator/
│   ├── __init__.py
│   ├── recorder.py                  # Macro-Aufzeichnung (Playwright)
│   ├── player.py                    # Macro-Wiedergabe
│   ├── webdriver.py                 # Playwright-Browser-Manager
│   ├── autorun.py                   # SMproducer-Workflows
│   ├── schema.py                    # JSON-Makro-Validierung
│   ├── i18n.py                      # i18n-Loader
│   └── cli.py                       # click-basierte CLI
├── macros/                          # Beispiel-Makros
│   └── .gitkeep
├── tests/
│   ├── __init__.py
│   ├── test_recorder.py
│   ├── test_player.py
│   ├── test_schema.py
│   └── conftest.py                  # pytest + pytest-playwright fixtures
└── .github/
    └── workflows/
        └── ci.yml                   # GitHub Actions CI
```

## 5. Implementierungs-Phasen (Child Tasks)

### Phase 1: Core Framework (est. 4h)
- [ ] `pyproject.toml` + `requirements.txt` + Projekt-Setup
- [ ] `webdriver.py` — Playwright Browser Lifecycle (launch, context, page)
- [ ] `schema.py` — JSON-Makroformat + jsonschema-Validierung
- [ ] `i18n.py` + i18n-Dateien (de/en)

### Phase 2: Recorder (est. 3h)
- [ ] `recorder.py` — Click/Input/Navigate Recording via Playwright
- [ ] Makro als JSON speichern
- [ ] Browser-Interception für Recording (page.on('click'), etc.)

### Phase 3: Player (est. 3h)
- [ ] `player.py` — JSON-Makro ausführen
- [ ] Schritt-für-Schritt-Execution mit Auto-Wait
- [ ] Fehlerbehandlung + Retry-Logik

### Phase 4: CLI (est. 2h)
- [ ] `cli.py` — `record`, `replay`, `autorun` Kommandos
- [ ] `--lang` Flag für i18n
- [ ] Exit-Codes (0=success, 1=test-failed, 2=error)

### Phase 5: SMproducer Autorun (est. 3h)
- [ ] `autorun.py` — SMproducer-spezifische Makros
- [ ] Workflow: Quelle → Thema-Auswahl → STOP (Human-in-the-Loop)
- [ ] Checkpoint-System für Resume

### Phase 6: Testing & CI (est. 2h)
- [ ] pytest Test-Suite
- [ ] GitHub Actions CI mit Playwright
- [ ] Beispiel-Makros im `macros/` Ordner

## 6. Qualitäts-Gates (CIO Review)

| Gate | Kriterium | Prüfmethode |
|------|----------|-------------|
| G1: Code | ruff linting 0 errors | `ruff check .` |
| G2: Tests | ≥80% Coverage Core-Module | `pytest --cov` |
| G3: i18n | Alle CLI-Strings in i18n-Dateien | `python -m testsimulator.i18n --validate` |
| G4: Schema | Beispiel-Makro valide gegen Schema | `python -m testsimulator.schema --validate macros/*.json` |
| G5: Docs | README aktuell, Docstrings auf Englisch | manuell |

## 7. Sicherheitsrichtlinien

- **Kein Recording von Credentials**: Makros enthalten KEINE Passwörter/API-Keys
- **Read-only Browser-Profile**: TestSimulator nutzt isoliertes Browser-Profil
- **Kein Internet-Zugriff im Headless-Mode**: `--isolated` Flag blockiert externe Requests
- **Exit-Code-Policy**: Failed Assertion → Exit 1 (nicht 0 — für CI)

## 8. Offene Fragen (für CEO-Konsent)

1. **Desktop-UI-Testing**: PyAutoGUI-Komponente jetzt oder später?
   → CIO-Empfehlung: Phase 2 (nach Playwright-Core stable)
2. **REST-API**: Jetzt mitplanen oder reines CLI?
   → CIO-Empfehlung: CLI-first, REST-API als separates Projekt (ME4-TestSimulator-API)
