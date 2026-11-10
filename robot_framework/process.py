"""
OpenOrchestrator-proces: behandler ét reminder-kø-element ad gangen.
Frameworket henter elementet og sætter status (DONE ved succes, FAILED ved fejl).
"""
import html
import json
import smtplib
from email.message import EmailMessage
import os 
from cryptography.fernet import Fernet, InvalidToken
from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection
from OpenOrchestrator.database.queues import QueueElement

MAX_ALDER_SEKUNDER = 7 * 24 * 60 * 60   # beskeder ældre end 7 dage sendes ikke

SMTP_SERVER = "smtp.adm.aarhuskommune.dk"
SMTP_PORT = 25
AFSENDER = "GodkendTimeregistreringAutomail@aarhus.dk"

# Sæt til False, når mails skal ud til de rigtige ledere.
# Når True, sendes alle mails til konstanten 'balas' i stedet.
TESTKOERSEL = False


def _formater_timer(timer: float) -> str:
    tekst = f"{timer:.2f}".rstrip("0").rstrip(".")
    return tekst.replace(".", ",")


def _byg_mail(modtager: str, navn: str, timer: float, orchestrator_connection) -> EmailMessage:
    timer_tekst = _formater_timer(timer)
    navn_html = html.escape(navn or "")

    msg = EmailMessage()
    msg["To"] = modtager
    msg["From"] = AFSENDER
    msg["Subject"] = f"Påmindelse: {timer_tekst} timer afventer din godkendelse"
    link_html = html.escape(orchestrator_connection.get_constant("OekonomiPowerBI").value, quote=True)
    link_tekst_html = html.escape("Ikke godkendte timer")
    kontakt_html = html.escape(orchestrator_connection.get_constant("OekonomiMail").value, quote=True)

    msg.set_content(
        f"""
        <html>
        <body>
            <p>Hej {navn_html}</p>
            <p>Du mangler at godkende <b>{timer_tekst} timer</b> for nogle af dine medarbejdere.</p>
            <p>Timeregistreringen er generelt vigtig i Teknik og Miljø, da den danner baggrund
               for medarbejdernes flex, indberetning af sygdom og ferie. I nogle tilfælde danner
               den også grundlag for fordelingsregnskaber og fakturering til kunder.</p>
            <p>Du kan se et udtræk af de manglende timer her (data trukket kl. 05.00):
               <a href="{link_html}">{link_tekst_html}</a></p>
            <p>Denne mail er autogenereret på baggrund af udtræk af de ikke-godkendte timer.<br>
               Såfremt du har spørgsmål, er du velkommen til at kontakte Økonomi på mail til
               <a href="mailto:{kontakt_html}">{kontakt_html}</a></p>
        </body>
        </html>
        """,
        subtype="html",
    )
    return msg


# pylint: disable-next=unused-argument
def process(orchestrator_connection: OrchestratorConnection, queue_element: QueueElement | None = None) -> None:
    """Sender én reminder-mail ud fra ét kø-element."""
    orchestrator_connection.log_trace("Running process.")

    if queue_element is None:
        orchestrator_connection.log_info("Intet kø-element – intet at sende.")
        return

    noegle = orchestrator_connection.get_credential("TimerReminderNoegle").password
    fernet = Fernet(noegle.encode("ascii"))

    try:
        indhold = fernet.decrypt(queue_element.data.encode("ascii"), ttl=MAX_ALDER_SEKUNDER)
    except InvalidToken:
        raise ValueError(
            f"{queue_element.reference}: kunne ikke dekrypteres "
            "(forkert nøgle, ændret eller ældre end 7 dage)"
        ) from None
    besked = json.loads(indhold.decode("utf-8"))

    modtager = besked["email"]
    if TESTKOERSEL:
        modtager = orchestrator_connection.get_constant("balas").value
        print(f"🧪 TESTKØRSEL: mail sendes til {modtager}")

    msg = _byg_mail(modtager, besked["navn"], besked["timer"], orchestrator_connection)
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as smtp:
        smtp.send_message(msg)

    orchestrator_connection.log_info(
        f"{queue_element.reference}: {'test-mail' if TESTKOERSEL else 'mail'} sendt"
    )