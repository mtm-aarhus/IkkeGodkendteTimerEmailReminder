# Timer-reminder til ledere

Sender én mail pr. leder, der har medarbejdere med ikke-godkendte timer.
Processen behandler ét kø-element ad gangen fra køen `LederTimerReminder`.

## Sådan hænger det sammen

1. **Køopretter** (MTM-processen) henter ikke-godkendte timer fra SAP, finder hver
   medarbejders personaleleder og lægger ét krypteret kø-element pr. leder i køen.
   Det sker kun om onsdagen.
2. **Denne proces** dekrypterer elementet og sender en reminder-mail til lederen
   med navn, antal timer og link til udtrækket.

Kø-data er krypteret med Fernet, så navne og mails ikke står i klartekst i Orchestrator.
Referencen på kø-elementet indeholder ingen personoplysninger.

## Opsætning i OpenOrchestrator

| Type       | Navn                  | Indhold                                  |
|------------|-----------------------|------------------------------------------|
| Credential | `TimerReminderNoegle` | Krypteringsnøglen i password-feltet      |
| Konstant   | `OekonomiPowerBI`     | Link til udtrækket af manglende timer    |
| Konstant   | `OekonomiMail`        | Økonomis kontaktmail                     |
| Konstant   | `balas`               | Modtager af mails under testkørsel       |

Nøglen skal være den samme som den, køopretteren krypterer med.

## Testkørsel

`TESTKOERSEL = True` øverst i `process.py` sender alle mails til konstanten `balas`
i stedet for til lederne. Sæt den til `False` for at gå i drift.

Bemærk: kø-elementer behandlet i testkørsel sættes til DONE og sendes ikke igen.

## Fejlhåndtering

- Elementer ældre end 7 dage afvises og sættes til FAILED.
- Elementer, der ikke kan dekrypteres (forkert nøgle eller ændret data), sættes til FAILED.
- Fejl ved afsendelse rejses videre, så frameworket sætter elementet til FAILED.

## Krav

- Python 3.11 eller nyere
- Se `pyproject.toml` for afhængigheder (`OpenOrchestrator`, `cryptography` m.fl.)