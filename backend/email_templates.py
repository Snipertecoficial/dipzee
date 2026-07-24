"""Localized transactional email templates (welcome + password reset).

The backend has no i18next, so copy lives here keyed by locale (pt/en/es/fr),
falling back to English. Emails use a single branded, inline-styled HTML shell
(email clients strip <style>/external CSS, so everything is inline). Keep this
in sync with the app's brand colors in frontend/src/index.css.
"""

_BRAND_NAVY = "#1A1F4D"
_BRAND_MINT = "#16E0A3"
_TEXT = "#0F1424"
_MUTED = "#5B6478"
_CANVAS = "#F6F8FB"

_FALLBACK = "en"

STRINGS = {
    "welcome": {
        "en": {
            "subject": "Welcome to Dipzee",
            "heading": "Welcome to Dipzee, {name}!",
            "body": "Your account is ready. Dipzee turns four numbers into one clear Opportunity Score, so you know what to buy, hold or sell in seconds.",
        },
        "pt": {
            "subject": "Bem-vindo ao Dipzee",
            "heading": "Bem-vindo ao Dipzee, {name}!",
            "body": "Sua conta está pronta. A Dipzee transforma quatro números em um Opportunity Score claro, para você saber o que comprar, manter ou vender em segundos.",
        },
        "es": {
            "subject": "Bienvenido a Dipzee",
            "heading": "¡Bienvenido a Dipzee, {name}!",
            "body": "Tu cuenta está lista. Dipzee convierte cuatro números en un Opportunity Score claro, para que sepas qué comprar, mantener o vender en segundos.",
        },
        "fr": {
            "subject": "Bienvenue sur Dipzee",
            "heading": "Bienvenue sur Dipzee, {name} !",
            "body": "Votre compte est prêt. Dipzee transforme quatre chiffres en un Score d'opportunité clair, pour savoir quoi acheter, conserver ou vendre en quelques secondes.",
        },
    },
    "reset": {
        "en": {
            "subject": "Reset your password — Dipzee",
            "heading": "Reset your password",
            "body": "Click the button below to create a new password. This link expires in {ttl} minutes.",
            "cta": "Create new password",
            "ignore": "If you didn't request this, you can safely ignore this email.",
            "fallback": "If the button doesn't work, copy and paste this link into your browser:",
        },
        "pt": {
            "subject": "Redefinir sua senha — Dipzee",
            "heading": "Redefinir sua senha",
            "body": "Clique no botão abaixo para criar uma nova senha. Este link expira em {ttl} minutos.",
            "cta": "Criar nova senha",
            "ignore": "Se você não pediu isso, pode ignorar este e-mail com segurança.",
            "fallback": "Se o botão não funcionar, copie e cole este link no seu navegador:",
        },
        "es": {
            "subject": "Restablece tu contraseña — Dipzee",
            "heading": "Restablece tu contraseña",
            "body": "Haz clic en el botón de abajo para crear una nueva contraseña. Este enlace caduca en {ttl} minutos.",
            "cta": "Crear nueva contraseña",
            "ignore": "Si no solicitaste esto, puedes ignorar este correo con seguridad.",
            "fallback": "Si el botón no funciona, copia y pega este enlace en tu navegador:",
        },
        "fr": {
            "subject": "Réinitialisez votre mot de passe — Dipzee",
            "heading": "Réinitialisez votre mot de passe",
            "body": "Cliquez sur le bouton ci-dessous pour créer un nouveau mot de passe. Ce lien expire dans {ttl} minutes.",
            "cta": "Créer un nouveau mot de passe",
            "ignore": "Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet e-mail.",
            "fallback": "Si le bouton ne fonctionne pas, copiez-collez ce lien dans votre navigateur :",
        },
    },
}


def _norm_locale(locale: str | None) -> str:
    loc = (locale or "").strip().lower()[:2]
    return loc if loc in ("en", "pt", "es", "fr") else _FALLBACK


def _shell(heading: str, paragraphs: list[str], cta_label: str | None = None,
           cta_url: str | None = None, small_notes: list[str] | None = None) -> str:
    rows = "".join(
        f'<tr><td style="color:{_MUTED};font-size:15px;line-height:1.6;padding:6px 0;">{p}</td></tr>'
        for p in paragraphs
    )
    if cta_label and cta_url:
        rows += (
            f'<tr><td style="padding:12px 0 6px;">'
            f'<a href="{cta_url}" style="display:inline-block;background:{_BRAND_NAVY};color:#ffffff;'
            f'text-decoration:none;font-weight:600;padding:12px 22px;border-radius:10px;font-size:15px;">'
            f'{cta_label}</a></td></tr>'
        )
    for note in (small_notes or []):
        rows += f'<tr><td style="color:#98A2C0;font-size:12px;line-height:1.5;padding:8px 0 0;">{note}</td></tr>'
    return (
        f'<div style="background:{_CANVAS};padding:28px 0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #E6E9F0;">'
        f'<tr><td style="background:{_BRAND_NAVY};padding:18px 28px;">'
        f'<span style="color:#ffffff;font-weight:700;font-size:20px;letter-spacing:-0.02em;">Dipzee</span>'
        f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{_BRAND_MINT};margin-left:6px;vertical-align:middle;"></span>'
        f'</td></tr>'
        f'<tr><td style="padding:28px 28px 6px;">'
        f'<h1 style="margin:0 0 4px;color:{_TEXT};font-size:22px;letter-spacing:-0.02em;">{heading}</h1>'
        f'</td></tr>'
        f'<tr><td style="padding:0 28px 20px;"><table role="presentation" cellpadding="0" cellspacing="0" width="100%">{rows}</table></td></tr>'
        f'<tr><td style="padding:14px 28px;border-top:1px solid #E6E9F0;color:#98A2C0;font-size:12px;line-height:1.5;">'
        f'Dipzee — educational information and automated signals, not personalized financial advice.'
        f'</td></tr>'
        f'</table></div>'
    )


def welcome_email(display_name: str, locale: str | None = None) -> tuple[str, str]:
    s = STRINGS["welcome"][_norm_locale(locale)]
    return s["subject"], _shell(s["heading"].format(name=display_name), [s["body"]])


def reset_email(link: str, ttl_minutes: int, locale: str | None = None) -> tuple[str, str]:
    s = STRINGS["reset"][_norm_locale(locale)]
    html = _shell(
        s["heading"],
        [s["body"].format(ttl=ttl_minutes)],
        cta_label=s["cta"],
        cta_url=link,
        small_notes=[f'{s["fallback"]}<br><a href="{link}" style="color:{_BRAND_NAVY};word-break:break-all;">{link}</a>', s["ignore"]],
    )
    return s["subject"], html
