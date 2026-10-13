# Konsolowe menu w Pythonie sterowane XML (PyAppsRunner)

Aplikacja konsolowa wyświetlająca wielopoziomowe, tekstowe menu zbudowane z
pliku `menu.xml` i uruchamiająca wskazane skrypty Pythona **w tym samym
procesie**. Docelowa platforma: Linux; testowana także na Windows.
Wymagania: Python >= 3.9, wyłącznie biblioteka standardowa (pytest tylko do testów).

## Uruchomienie

```bash
python main.py                 # menu z <katalog_aplikacji>/menu.xml
python main.py --config ścieżka/do/menu.xml
python main.py --base-dir KATALOG   # katalog bazowy dla ścieżek ze XML-a
                                    # (domyślnie: katalog, w którym leży main.py)
```

Wymagana jest interaktywna konsola (stdin musi być terminalem). Przy przekierowanym
stdin program kończy się z kodem 3 i komunikatem na stderr. Kody wyjścia:
`0` - normalne zakończenie / Ctrl+C w menu, `2` - błąd konfiguracji XML,
`3` - brak terminala interaktywnego.

## Uruchomienie testów

```bash
pip install -r requirements-dev.txt   # instaluje pytest
python -m pytest -q                   # pełny zestaw testów (TDD: każdy krok miał zielone)
```

Testy zależne od platformy (np. pseudoterminal `pty`) są pomijane na systemach,
na których się nie wykonają (`pytest.mark.skipif`).

## Klawisze

| Klawisz  | Działanie                                          |
|----------|----------------------------------------------------|
| `a`      | w górę (nawigacja cykliczna - z pierwszej pozycji na ostatnią) |
| `z`      | w dół (cyklicznie)                                 |
| `Enter`  | zatwierdź (wejście do podmenu / uruchom skrypt / wyjście) |
| `Ctrl+C` | w menu: czyste zakończenie (kod 0); w trakcie skryptu: przerwanie i powrót do menu; podczas pauzy "Naciśnij Enter...": kończy tylko pauzę |

Na końcu każdej listy jest pozycja systemowa: **Wyjście** w menu głównym,
**Wstecz** w podmenu (nie pochodzi z XML). Powrót `Wstecz` przywraca zaznaczenie
zapisane przed wejściem w podmenu. Pozostałe klawisze są ignorowane; sekwencje
strzałek/ESC traktuje się jak "pozostałe".

## Format menu.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<menu title="Menu główne">
  <item name="Pozdrowienie" dir="scripts/basic" file="hello.py"/>
  <folder name="Narzędzia">
    <item name="Demo powrotu" dir="scripts/tools" file="exit_to_root_demo.py"/>
    <folder name="Zaawansowane">
      <item name="Test błędu" dir="scripts/basic" file="error_demo.py"/>
    </folder>
  </folder>
</menu>
```

Reguły:

- element główny `<menu>`; atrybut `title` opcjonalny (domyślnie "Menu główne");
- `<item name dir file/>` - wszystkie trzy atrybuty wymagane i niepuste,
  `<item>` nie może mieć dzieci, `file` musi kończyć się na `.py` (bez rozróżniania wielkości liter);
- `<folder name>` może zawierać foldery i itemy w dowolnej głębokości; pusty folder dozwolony;
- kolejność elementów XML = kolejność pozycji menu;
- `dir` jest ścieżką względną względem katalogu bazowego (dopuszczany separator `\`,
  zamieniany na `/`); wynik musi leżeć wewnątrz katalogu bazowego (ochrona przed `../`);
- nieznane elementy = błąd konfiguracji, nieznane atrybuty są ignorowane;
- komunikaty błędów zawierają numer linii, gdy jest dostępny.

Istnienie pliku skryptu sprawdzane jest w momencie uruchomienia (nie przy wczytywaniu
XML) - menu działa mimo brakującego skryptu, użytkownik dostaje komunikat po wyborze pozycji.

## Kontrakt wywoływanego skryptu

Skrypt to zwykły plik `.py` zawierający funkcję na poziomie modułu:

```python
def run(ctx) -> int | None:
    ...
```

1. **Wartość zwracana:** `None` lub `0` = sukces; inna liczba całkowita = błąd
   (menu pokaże kod). Wartości nie-całkowite (np. tekst, bool) to naruszenie kontraktu.
2. **Powrót do menu** = zwykłe zakończenie `run()`. Dopuszczalne także:
   `sys.exit(n)` (traktowane jak `return n`) oraz `Ctrl+C` (anulowanie - traktowane
   jako "Przerwano.", nie jest błędem).
3. Kod na poziomie modułu poza `run()` powinien być bez efektów ubocznych
   (import ma być czysty); każde uruchomienie to świeże wykonanie pliku
   (moduł jest usuwany z `sys.modules` po zakończeniu).
4. Skrypt używa zwykłych `print()` / `input()` - terminal jest w trybie normalnym;
   wyjątki skryptu są łapane (traceback na stderr) i nie wyłączają menu.
5. Katalog skryptu jest na czas działania dodawany do początku `sys.path`
   (skrypt może importować moduły leżące obok siebie). Skrypt NIE zmienia
   katalogu roboczego procesu.

Minimalny szablon:

```python
def run(ctx):
    print("Moja akcja")
    return 0
```

### Kontekst `ctx` (dataclass `ScriptContext`)

| Pole | Znaczenie |
|------|-----------|
| `base_dir: Path` | katalog bazowy aplikacji |
| `script_path: Path` | pełna ścieżka uruchamianego pliku |
| `script_dir: Path` | katalog, w którym leży skrypt |
| `menu_path: tuple[str, ...]` | nazwy folderów prowadzących do pozycji (bez roota), np. `("Narzędzia", "Zaawansowane")` |
| `skip_pause: bool = False` | `True` -> po skrypcie nie ma pauzy "Naciśnij Enter..." |

Metody:

- `ctx.exit_to_root()` - po zakończeniu menu wraca do menu głównego (zamiast na poziom, z którego uruchomiono skrypt);
- `ctx.pause(message=...)` - pauza dla użytkownika w trakcie skryptu (`input`; EOF ignorowany).

Po zakończeniu skryptu program pokazuje "Naciśnij Enter, aby wrócić do menu"
(chyba że `skip_pause=True`) i wraca na ten sam poziom z tym samym zaznaczeniem.

## Przykładowe skrypty

- `scripts/basic/hello.py` - powitanie + wypisanie kontekstu;
- `scripts/basic/error_demo.py` - celowy wyjątek (demonstracja obsługi błędów);
- `scripts/tools/exit_to_root_demo.py` - demonstracja `ctx.exit_to_root()`.

## Decyzje projektowe

### Ze specyfikacji (Krok 0)

1. Katalog bazowy = katalog `main.py`; nadpisywalny przez `--base-dir`.
2. Nawigacja cykliczna w górę i w dół.
3. Pozycje systemowe: "Wyjście" (root) / "Wstecz" (podmenu), zawsze na końcu listy.
4. Skrypty uruchamiane w tym samym procesie (`importlib`); błędy skryptu nie wyłączają menu.
5. Po skrypcie powrót na poziom, z którego go uruchomiono; opcjonalnie `ctx.exit_to_root()`.
6. Pauza "Naciśnij Enter..." po skrypcie, chyba że `skip_pause=True`.
7. Ctrl+C w menu = czyste wyjście (kod 0); Ctrl+C w skrypcie = przerwanie i powrót do menu.

### Własne decyzje agenta

1. **bool jako wartość zwracana** - traktowany jak naruszenie kontraktu
   (`run() powinno zwrócić int lub None`), mimo że `True/False` są podtypami `int` w Pythonie;
   analogicznie przy `sys.exit(True)` kod wynosi 1.
2. **Numery linii w błędach XML** - parser (ElementTree) nie udostępnia numera linii dla
   błędów semantycznych, więc nadbudowano nad nim śledzenie: skanowanie surowego tekstu
   regexem + podklasa `ET.TreeBuilder` zapisująca linię rozpoczęcia każdego tagu.
   Komunikaty kończą się przyrostkiem ", linia N"; gdy numer jest niedostępny - bez niego.
3. **Pauza także po błędach** (błąd uruchomienia skryptu, brak pliku, ścieżka poza bazą)
   - żeby użytkownik zdążył przeczytać komunikat; pomijana tylko przy `skip_pause=True`
   (ustawianym przez sam skrypt, więc nie dotyczy błędów przed jego wykonaniem).
4. **Ctrl+C / EOF podczas pauzy** kończy tylko pauzę i wraca do menu (nie zabija aplikacji).
5. **Klawisze OTHER są ignorowane** - ekran jest przerysowywany, ale stan się nie zmienia;
   sekwencje ucieczki (strzałki) też mapują na OTHER.
6. **Renderer:** okno pozycji = `max(1, height - 5)` linii; gdy lista nie mieści się w
   oknie, ukryte strony oznaczają wiersze "  ..."; dla bardzo małych okien (width < 10,
   height < 6) brak wyjątków - wyświetlany jest co najmniej jeden wiersz pozycji.
7. **`FakeKeyReader`** znajduje się w `menu_app/testing.py` (dozwolone przez specyfikację:
   "w tests/ lub w menu_app/testing.py") - poza katalogiem testów, bo to część interfejsu DI;
   po wyczerpaniu listy rzuca `AssertionError`, zabezpieczając testy przed pętlą nieskończoną.
8. **Dodatkowy plik `tests/test_smoke.py`** - minimalny test importów wymagany przez
   Definition of Done Kroku 1 (zbiór testów musi być zbieralny, gdy logika jeszcze nie istnieje).
9. **Kody wyjścia z `main()`:** 2 = błąd konfiguracji XML, 3 = stdin nie jest terminalem
   i nie wstrzyknięto czytnika klawiszy (np. uruchomienie pod CI bez TTY).
10. **Windows:** stdout przełączany na UTF-8 (`reconfigure`, gdy metoda dostępna),
    kody ANSI włączane przez `SetConsoleMode` (ctypes); przy przekierowanym stdout
    niepowodzenie jest cicho ignorowane. Na POSIX `enable_ansi()` nic nie robi.
11. **Nazwa modułu skryptu** = `menu_script_<sha256(ścieżki)[:16]>` - unikalna dla pliku,
    dzięki czemu dwa różne skrypty o tej samej nazwie w różnych katalogach nie kolizują;
    po każdym uruchomieniu moduł jest usuwany z `sys.modules`.
