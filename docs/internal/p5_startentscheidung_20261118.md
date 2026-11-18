# P5 starten oder warten?

Stand: 18.11.2026, 16:26. Kein Lauf gestartet, kein Prozess verändert.

## Kurzantwort

Technisch lässt sich P5 jetzt starten. Ich rate davon ab, und ohne ausdrückliche
Freigabe starte ich ihn nicht: Nachtlauf und Nachzug laufen, ein dritter Lauf am
selben Gateway würde alle drei verlangsamen und die Laufzeiten unvergleichbar
machen. Die Wache startet P5 von selbst, sobald die Bedingungen erfüllt sind.

## Stand der Läufe

| Was | Zustand |
|---|---|
| Nachtlauf `yun699_8000_alle_20261117` (PID 3952) | läuft, 1.986 Zeilen, letzte Zeile vor 16 s |
| Nachzug-Steuerung (PID 2153) | wartet auf den Hauptlauf, Sperre lebt |
| Startwache (PID 5032) | „belegt, P5 wuerde warten", Takt 60 s |
| P5 (`runs/yun699_p5_24000_20261118`) | Verzeichnis existiert nicht, nie gestartet |

Zustandsprüfung ausschließlich über `yun_full/starte_p5_wenn_frei.sh --pruefen`.

## Was seit dem letzten Bericht dazukam

Sprint 46 (Commit `f05928a`, „P5: gate Auswertung mit Positivkontrolle"):

- Die Positivkontrolle läuft jetzt unmittelbar vor der echten Auswertung
  (`yun_full/werte_p5_mit_kontrolle.sh`).
- Die Auswertung verweigert ohne frische Erfolgsmarke **und** passenden Nonce
  (Exit 3, kein Bericht). Der Nonce bindet Marke und Auswertung an denselben
  Durchlauf, damit keine Marke aus einem fremden Lauf autorisiert.
- Jeder unklare Ausgang der Kontrolle blockiert die Auswertung (Exit 4).
  Es gibt keinen Schalter, der das umgeht.
- „P5 fertig" wird nur noch protokolliert, wenn wirklich ein Bericht entstanden
  ist — sonst hätte eine gescheiterte Auswertung jeden späteren Lauf blockiert.
- 373 Tests in `public_benchmark/tests` grün, darunter acht isolierte Tests des
  Wrappers und sechs für die Markenprüfung.

Für die Frage „starten oder warten" ändert das nichts am Zeitpunkt, aber am
Risiko: Ein Bericht kann ab jetzt nur noch aus einer geprüften Rechnung entstehen,
egal ob die Wache oder ein Handstart ihn auslöst.

## Vier Gründe gegen einen Handstart jetzt

1. **Drei Läufe am selben Gateway.** Der Nachtlauf belegt qwen, der Nachzug will
   danach 140 glm-Records mit 24.000 Tokens nachziehen. P5 käme dazu; alle drei
   teilen dieselbe Rate-Limit-Decke. Wartezeiten und Backoffs verfälschen die
   Laufzeiten, die du später mit der Ausgangslage vergleichen willst.
2. **Widerspruch zur eigenen Vorgabe.** Der P5-Auftrag verlangt „Der Hauptlauf darf
   nicht gestört werden" und einen Start erst nach Nachtlauf und Nachzug. Ein
   Handstart ist genau die Umgehung, die die Wache verhindern soll.
3. **Doppelter Start droht.** Die Wache (PID 5032) läuft weiter und würde später
   ein zweites Mal ansetzen. Die Sperre im Run-Verzeichnis weist den zweiten
   Prozess ab, das erzeugt aber nur Lärm. Sauber ginge es nur, wenn die Wache
   vorher beendet wird.
4. **Kosten.** 103 Records, bis zu drei Versuche je Record, 24.000 Tokens
   Budget — der teuerste Lauf, den dieses Repo bisher gefahren hat. Dafür sollte
   der Nachtlauf nicht parallel laufen.

## Was ein Handstart voraussetzen würde

Zwei Entscheidungen, die sich nicht rückgängig machen lassen:

1. P5 jetzt starten, obwohl Nachtlauf und Nachzug laufen.
2. Die Wache dafür beenden (PID 5032), damit sie nicht später ein zweites Mal
   ansetzt.

Reihenfolge wäre: Wache stoppen, P5 mit den 103 ids gegen `yun699.jsonl` starten,
Fortschritt nach `runs/p5_lauf_20261118.log` mitschreiben, danach
`werte_p5_mit_kontrolle.sh` für den Bericht.

## Was automatisch passiert

Die Wache startet P5, sobald drei Bedingungen gleichzeitig gelten: kein
Extraktionsprozess für den Nachtlauf, der Prozess aus `nachzug.lock` lebt nicht
mehr, und 180 Sekunden lang keine neue Zeile an `predictions.jsonl`. Danach läuft
die Positivkontrolle, dann die Auswertung; die Artefakte landen in
`iterativ/ergebnisse/p5_auswertung_20261118.{json,md}`.

Die Frist der Wache endet um **03:45** (720 Minuten ab 15:45). Läuft sie ab, ohne
dass die Bedingungen erfüllt sind, startet sie nichts und schreibt „ABBRUCH" ins
Protokoll — dann wäre ein neuer Start nötig, nicht ein Handstart mitten hinein.

## Unsicherheiten

- Wie lange der Nachtlauf noch braucht, ist offen; der qwen-Block hing zuletzt bei
  rund 543 von 699 Records.
- Der laufende Wachen-Prozess hat die Textfassung von vor Sprint 46 geladen. Er
  kann die Auswertung ohne Nonce aufrufen; die verweigert dann mit Exit 3, es
  entsteht also kein ungeprüfter Bericht. Ein sauberer Durchlauf mit Kontrolle
  kommt erst beim nächsten Start der Wache.
- Der Tokenzähler erfasst den laufenden Nachtlauf nicht (der Prozess hat den
  Harness vor dem Einbau geladen). P5 würde vollständig gezählt.

## Empfehlung

Warten. Der Nutzen eines Starts jetzt ist null — gleiche ids, gleicher Prompt,
gleiches Budget —, der Preis ist ein verrauschtes Messumfeld. Wenn Zeitdruck
besteht, ist es ehrlicher, den Nachzug zu verschieben, als drei Läufe zu
überlappen. Andernfalls gilt: nichts tun, bis die Wache meldet.
