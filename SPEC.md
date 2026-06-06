# ME4 TestSimulator — Projektspezifikation (CIO)

> **CIO Reference**: ITIL 4 Service Value System — Design & Transition
> **COBIT 2019**: BAI03 (Managed Solutions Identification & Build)
> **bB Tag**: DEV, ARCHITECTURE
> **Version**: 1.1 — erweitert um Recording-Mechanismus, Action-Types, Selector-Strategie, Error-Handling, SMproducer-Integration

## 1. Executive Summary

ME4 TestSimulator ist ein Macro-basierter UI-Test-Automat, der menschliche Interaktion mit Web-UIs aufzeichnet und reproduziert. Primäres Ziel: Automatisierte Regressionstests für ME4-Services (insb. SMproducer 3.0), die ohne manuelle Eingriffe auskommen — außer an definierten Entscheidungspunkten (Human-in-the-Loop).

**Kernkomponenten:**
- **Macro-Recorder**: Zeichnet User-Interaktionen im Browser auf (element-basiert, nicht positionsbasiert)
- **Macro-Player**: Spielt aufgezeichnete Makros ab — mit Auto-Wait, Retry und Recovery
- **SMproducer-Autorun**: Vordefinierte Workflows für SMproducer-Tests (Quelle → Analyse → Entscheidungspunkt)

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
- `schema.py` — Makro-Validierung (Validation-Layer)
- `cli.py` — CLI-Interface (Presentation-Layer)

### DEC-005: i18n ab Tag 1

Gemäß ME4 i18n Standard (siehe `me4-i18n-developer-guide.md`):
- `manifest.json` mit Sprachdefinitionen
- `i18n/` Ordner mit `de.json`, `en.json`
- CLI-Output per `--lang de|en` steuerbar
- Default: `de` (ME4-Primärsprache)
- Flags: en=🇬🇧 (nicht 🇺🇸!), de=🇩🇪

### DEC-006: Macro-Recording-Mechanismus (CDP-basiert)

**Wie Recording funktioniert:**

1. TestSimulator startet einen Playwright-Browser mit CDP (Chrome DevTools Protocol)
2. Recording-Mode injiziert einen Event-Listener in die Seite via `page.add_init_script()`
3. Folgende DOM-Events werden abgefangen und in Makro-Schritte übersetzt:

| DOM-Event | → Action-Type | Erfasste Daten |
|-----------|--------------|----------------|
| `click` | `click` | Target-Element, Selector, Position |
| `dblclick` | `dblclick` | Target-Element, Selector |
| `input` / `change` | `type` | Target-Input, eingegebener Text, Selector |
| `change` (select) | `select` | Select-Element, gewählter Wert, Selector |
| `mouseenter` | `hover` | Target-Element, Selector |
| `scroll` | `scroll` | Scroll-Position (X/Y) |
| Navigation (URL-Change) | `navigate` | Neue URL |
| `keydown` (global shortcuts) | `keypress` | Tastenkombination |

4. Selector-Generierung erfolgt automatisch nach DEC-008 (Selector-Strategie)
5. Der Benutzer interagiert NORMAL mit der Seite — TestSimulator zeichnet im Hintergrund auf
6. Recording endet per `Ctrl+C` oder `--max-steps N`

**Technische Umsetzung:**
```python
# recorder.py (vereinfacht)
async def start_recording(page, output_file):
    steps = []
    await page.add_init_script("""
        document.addEventListener('click', (e) => {
            window.__ts_recordEvent('click', e.target);
        });
        document.addEventListener('input', (e) => {
            window.__ts_recordEvent('input', e.target, e.target.value);
        });
        // ... weitere Events
    """)
    await page.expose_function('__ts_recordEvent', 
        lambda event_type, element_data, value=None: 
            steps.append(build_step(event_type, element_data, value))
    )
    # Warte auf Recording-Ende
    await wait_for_stop_signal()
    save_macro(steps, output_file)
```

### DEC-007: Vollständiger Action-Type-Katalog

| Action | JSON-Parameter | Playwright-API | Beschreibung |
|--------|---------------|----------------|-------------|
| `navigate` | `url: str` | `page.goto(url)` | URL aufrufen |
| `click` | `selector: str` | `page.click(selector)` | Element klicken |
| `dblclick` | `selector: str` | `page.dblclick(selector)` | Doppelklick |
| `type` | `selector: str, text: str` | `page.fill(selector, text)` | Text in Input-Feld |
| `select` | `selector: str, value: str` | `page.select_option(selector, value)` | Dropdown-Auswahl |
| `hover` | `selector: str` | `page.hover(selector)` | Maus über Element |
| `scroll` | `x: int, y: int` | `page.evaluate('window.scrollTo(x,y)')` | Scrollen |
| `keypress` | `key: str` | `page.keyboard.press(key)` | Tastendruck |
| `wait` | `ms: int \| selector: str` | `page.wait_for_timeout(ms)` oder `page.wait_for_selector(sel)` | Warten (Zeit / Element) |
| `assert` | `type: str, selector?: str, value?: str` | `page.text_content()` etc. | Assertion (text/visible/value/url) |
| `check` | `selector: str` | `page.check(selector)` | Checkbox aktivieren |
| `uncheck` | `selector: str` | `page.uncheck(selector)` | Checkbox deaktivieren |
| `upload` | `selector: str, file: str` | `page.set_input_files(selector, file)` | Datei-Upload |
| `screenshot` | `path: str` | `page.screenshot(path=path)` | Screenshot |
| `checkpoint` | `message: str` | — (pausiert) | Human-in-the-Loop Haltepunkt |
| `evaluate` | `script: str` | `page.evaluate(script)` | Beliebiges JS ausführen |

**Assert-Types:**
- `text`: Prüft Text-Inhalt eines Elements (`page.text_content(selector) == value`)
- `visible`: Prüft Sichtbarkeit (`page.is_visible(selector)`)
- `hidden`: Prüft Unsichtbarkeit (`page.is_hidden(selector)`)
- `value`: Prüft Input-Wert (`page.input_value(selector) == value`)
- `url`: Prüft aktuelle URL (`page.url == value`)
- `title`: Prüft Seitentitel (`await page.title() == value`)
- `count`: Prüft Element-Anzahl (`len(await page.query_selector_all(sel)) == value`)

### DEC-008: Selector-Strategie (Priority-Based)

**Prioritäts-Reihenfolge bei der Selector-Generierung:**

1. `data-testid` — Bevorzugt (explizit für Testing vorgesehen, stabil)
2. `id` — Eindeutig (wenn vorhanden und stabil)
3. `aria-label` — Accessibility-Label (robust, mehrsprachig)
4. `name` — Input-Name-Attribut
5. CSS-Klasse + Tag-Kombination — `button.primary` (wenn eindeutig)
6. Text-Inhalt — `text=Neues Projekt` (nur für statische Texte)
7. XPath — Letzte Wahl (positionsbasiert, instabil)

**Implementierung im Recorder:**
```python
def generate_selector(element_data: dict) -> dict:
    """Erzeugt Primary-Selector + Fallbacks aus Element-Metadaten."""
    selectors = []
    
    if element_data.get('data-testid'):
        selectors.append({'type': 'testid', 'value': f"[data-testid='{element_data['data-testid']}']"})
    if element_data.get('id'):
        selectors.append({'type': 'id', 'value': f"#{element_data['id']}"})
    if element_data.get('aria-label'):
        selectors.append({'type': 'aria', 'value': f"[aria-label='{element_data['aria-label']}']"})
    # ... weitere Strategien
    
    return {
        'primary': selectors[0],
        'fallbacks': selectors[1:],
        'element_tag': element_data.get('tag'),
        'element_text': element_data.get('text', '')[:50],
    }
```

**Im Makro-JSON:**
```json
{
  "id": 2,
  "action": "click",
  "selector": {
    "primary": {"type": "testid", "value": "[data-testid='new-project']"},
    "fallbacks": [
      {"type": "css", "value": "button.btn-primary"},
      {"type": "text", "value": "text=Neues Projekt"}
    ]
  },
  "description": "Neues Projekt starten"
}
```

### DEC-009: Wait-Strategie

**Drei Wait-Level:**

| Level | Strategie | Anwendung |
|-------|----------|-----------|
| **Auto-Wait** (Default) | Playwright actionability checks | Vor jedem `click`, `type`, `select` |
| **Smart-Wait** | `page.wait_for_load_state('networkidle')` | Nach `navigate` |
| **Explicit-Wait** | `wait` Action im Makro | Benutzerdefinierte Wartezeiten |
| **Condition-Wait** | `wait: {selector: "...", timeout: 5000}` | Auf bestimmtes Element warten |

**Timeout-Konfiguration:**
- Default Action-Timeout: 30s (pro Schritt)
- Default Navigation-Timeout: 60s
- Konfigurierbar per `--timeout N`

### DEC-010: Fehlerbehandlung & Recovery

**Error-Handling-Strategie pro Schritt (konfigurierbar):**

| Modus | Flag | Verhalten |
|-------|------|----------|
| `strict` (Default) | — | Schritt scheitert → Makro bricht ab (Exit 1) |
| `retry` | `--on-error retry` | Schritt scheitert → wiederhole bis zu 3x mit 1s Backoff |
| `skip` | `--on-error skip` | Schritt scheitert → logge Fehler, fahre mit nächstem Schritt fort |
| `checkpoint` | `--on-error checkpoint` | Schritt scheitert → pausiere für manuellen Eingriff |

**Recovery-Features:**
- **Screenshot on failure**: `--screenshot-on-fail` speichert Screenshot bei jedem Fehler
- **Video-Aufzeichnung**: `--record-video` zeichnet kompletten Testlauf als Video auf
- **Trace-Datei**: Playwright Trace (.zip) für Debugging via `playwright show-trace`
- **Resume**: `--resume-from STEP_ID` setzt ab bestimmtem Schritt fort

**Makro-JSON mit Error-Config:**
```json
{
  "metadata": {
    "error_strategy": "retry",
    "max_retries": 3,
    "retry_delay_ms": 1000,
    "screenshot_on_fail": true
  }
}
```

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
│   ├── recorder.py                  # Macro-Aufzeichnung (CDP-basiert)
│   ├── player.py                    # Macro-Wiedergabe
│   ├── webdriver.py                 # Playwright-Browser-Manager
│   ├── autorun.py                   # SMproducer-Workflows
│   ├── schema.py                    # JSON-Makro-Validierung
│   ├── selectors.py                 # Selector-Strategie + Generator
│   ├── i18n.py                      # i18n-Loader
│   └── cli.py                       # click-basierte CLI
├── macros/                          # Beispiel-Makros
│   └── .gitkeep
├── tests/
│   ├── __init__.py
│   ├── test_recorder.py
│   ├── test_player.py
│   ├── test_schema.py
│   ├── test_selectors.py
│   └── conftest.py                  # pytest + pytest-playwright fixtures
└── .github/
    └── workflows/
        └── ci.yml                   # GitHub Actions CI
```

## 5. SMproducer-Integration — Autorun-Kontrakt

### Workflow: Quelle → Analyse → Entscheidungspunkt

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ TestSimulator│────▶│   SMproducer    │────▶│ Entscheidungspunkt│
│ (Autorun)    │     │  (localhost:5173)│     │  (Human-in-Loop) │
└─────────────┘     └─────────────────┘     └──────────────────┘
```

**Schritt-für-Schritt-Ablauf:**

1. **Kanal wählen**: TestSimulator navigiert zu SMproducer, klickt Kanal
2. **Neues Projekt**: Klick "Neues Projekt" → Projektname eingeben
3. **Quelle hinzufügen**: YouTube-URL einfügen, Quelle starten
4. **Analyse abwarten**: Polling auf "Analyse abgeschlossen"-Indikator (Selector: `[data-status='complete']`)
5. **STOPP — Entscheidungspunkt**: TestSimulator pausiert, zeigt verfügbare Themen an
6. **Benutzer-Input**: Mensch wählt Themen aus / verwirft / priorisiert
7. **Fortsetzen**: TestSimulator fährt mit Workflow fort (nächste Quelle oder Export)

**Checkpoint-Mechanismus:**
```json
{
  "id": 5,
  "action": "checkpoint",
  "message": "Themen auswählen — Test pausiert bis ENTER",
  "checkpoint_id": "topic-selection",
  "resume_condition": "user_confirm"
}
```

**Resume nach Checkpoint:**
```bash
# Test läuft bis zum Entscheidungspunkt, dann:
[TEST] Checkpoint 'topic-selection' erreicht.
[TEST] Bitte Themen manuell auswählen, dann ENTER drücken...

# Nach ENTER:
[TEST] Checkpoint bestätigt — fahre fort mit Schritt 6...
```

### SMproducer UI-Konventionen (für stabile Selektoren)

Damit TestSimulator zuverlässig funktioniert, MÜSSEN folgende `data-testid`-Attribute in SMproducer vorhanden sein:

| Element | data-testid | Priorität |
|---------|------------|-----------|
| Neues-Projekt-Button | `new-project` | CRITICAL |
| Quelltyp-Dropdown | `source-type` | CRITICAL |
| URL-Input | `source-url` | CRITICAL |
| Quelle-starten-Button | `source-start` | CRITICAL |
| Analyse-Status | `analysis-status` | CRITICAL |
| Themen-Container | `topic-list` | CRITICAL |
| Thema-Checkbox | `topic-item-{id}` | HIGH |
| Thema-auswählen-Button | `topic-confirm` | CRITICAL |
| Nächste-Quelle-Button | `next-source` | HIGH |
| Export-Button | `export-project` | MEDIUM |

**SMproducer-Autorun-Button (Gegenstück):**
- SMproducer Header bekommt einen "Autorun"-Button
- Button sendet Start-Signal an TestSimulator (via CLI-Aufruf oder HTTP)
- TestSimulator übernimmt, SMproducer agiert passiv

## 6. Implementierungs-Phasen (Child Tasks)

### Phase 1: Core Framework (est. 4h)
- [ ] `pyproject.toml` + `requirements.txt` + Projekt-Setup
- [ ] `webdriver.py` — Playwright Browser Lifecycle (launch, context, page)
- [ ] `schema.py` — JSON-Makroformat + jsonschema-Validierung
- [ ] `i18n.py` + i18n-Dateien (de/en, Flags: 🇬🇧🇩🇪)

### Phase 2: Recorder (est. 3h)
- [ ] `selectors.py` — Selector-Strategie und -Generator
- [ ] `recorder.py` — Click/Input/Navigate Recording via CDP
- [ ] Event-Handler: click, input, change, scroll, navigation
- [ ] Makro als JSON speichern mit Selector-Fallbacks
- [ ] Recorder-Test: manuell aufnehmen, JSON-Ausgabe prüfen

### Phase 3: Player (est. 3h)
- [ ] `player.py` — JSON-Makro ausführen
- [ ] Schritt-für-Schritt-Execution mit Auto-Wait
- [ ] Selector-Fallback: Primary → Fallback-1 → Fallback-2 → Fehler
- [ ] Fehlerbehandlung: strict/retry/skip/checkpoint Modi
- [ ] Screenshot-on-Fail + Trace-Datei

### Phase 4: CLI (est. 2h)
- [ ] `cli.py` — `record`, `replay`, `autorun` Kommandos
- [ ] `--lang de|en` Flag für i18n
- [ ] `--on-error strict|retry|skip|checkpoint`
- [ ] `--screenshot-on-fail`, `--record-video`, `--trace`
- [ ] `--resume-from STEP_ID`
- [ ] Exit-Codes (0=success, 1=test-failed, 2=error)

### Phase 5: SMproducer Autorun (est. 3h)
- [ ] `autorun.py` — SMproducer-spezifische Makros
- [ ] Workflow: Quelle → Thema-Auswahl → STOP (Human-in-the-Loop)
- [ ] Checkpoint-System für Resume
- [ ] SMproducer: `data-testid`-Attribute in UI einbauen (separater E-Task)

### Phase 6: Testing & CI (est. 2h)
- [ ] pytest Test-Suite (recorder, player, schema, selectors)
- [ ] GitHub Actions CI mit Playwright (headless)
- [ ] Beispiel-Makros im `macros/` Ordner
- [ ] Integrationstest: SMproducer-Durchlauf aufzeichnen + abspielen

## 7. Qualitäts-Gates (CIO Review)

| Gate | Kriterium | Prüfmethode |
|------|----------|-------------|
| G1: Code | ruff linting 0 errors | `ruff check .` |
| G2: Tests | ≥80% Coverage Core-Module | `pytest --cov` |
| G3: i18n | Alle CLI-Strings in i18n-Dateien | `python -m testsimulator.i18n --validate` |
| G4: Schema | Beispiel-Makro valide gegen Schema | `python -m testsimulator.schema --validate macros/*.json` |
| G5: i18n-Flags | en=🇬🇧, de=🇩🇪 (nicht 🇺🇸) | `check-i18n-flags.py` |
| G6: Docs | README aktuell, Docstrings auf Englisch | manuell |

## 8. Sicherheitsrichtlinien

- **Kein Recording von Credentials**: Makros enthalten KEINE Passwörter/API-Keys
- **Read-only Browser-Profile**: TestSimulator nutzt isoliertes Browser-Profil
- **Kein Internet-Zugriff im Headless-Mode**: `--isolated` Flag blockiert externe Requests
- **Exit-Code-Policy**: Failed Assertion → Exit 1 (nicht 0 — für CI)
- **Screenshot-Sicherheit**: Screenshots werden NUR lokal gespeichert, nie automatisch versendet
- **Makro-Integrität**: SHA256-Hash des Makros wird bei Ausführung geloggt für Audit-Trail

## 9. Offene Fragen (für CEO-Konsent)

1. **Desktop-UI-Testing**: PyAutoGUI-Komponente jetzt oder später?
   → CIO-Empfehlung: Phase 2 (nach Playwright-Core stable)
2. **REST-API**: Jetzt mitplanen oder reines CLI?
   → CIO-Empfehlung: CLI-first, REST-API als separates Projekt (ME4-TestSimulator-API)
3. **Aufzeichnungs-UI**: Browser-Extension für Recording oder reines CLI?
   → CIO-Empfehlung: CLI-only für v1.0, Extension prüfen wenn CLI-Recording zu umständlich
4. **SMproducer data-testid**: Wer baut die data-testid-Attribute ein?
   → CIO-Empfehlung: SMproducer-Team (E-Task), TestSimulator dokumentiert nur die Erwartungen (siehe Section 5)
