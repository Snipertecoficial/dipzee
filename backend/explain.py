"""Localized plain-language explanations and alert messages (EN/FR/PT/ES)."""

CLASSIFICATION_LABELS = {
    "en": {"strong_buy": "Strong Buy", "buy": "Buy", "hold": "Hold", "reduce": "Reduce", "sell": "Sell"},
    "fr": {"strong_buy": "Achat fort", "buy": "Acheter", "hold": "Conserver", "reduce": "R\u00e9duire", "sell": "Vendre"},
    "pt": {"strong_buy": "Compra forte", "buy": "Comprar", "hold": "Manter", "reduce": "Reduzir", "sell": "Vender"},
    "es": {"strong_buy": "Compra fuerte", "buy": "Comprar", "hold": "Mantener", "reduce": "Reducir", "sell": "Vender"},
}


def _pct(x):
    return f"{x * 100:.0f}%"


def build_explanation(asset: dict, locale: str = "en") -> str:
    locale = locale if locale in CLASSIFICATION_LABELS else "en"
    name = asset.get("name") or asset.get("ticker")
    price = asset.get("price")
    low = asset.get("low_52w")
    target = asset.get("target_mean")
    dy = asset.get("dividend_yield") or 0.0
    score = asset.get("score")
    cls = asset.get("classification", "hold")
    label = CLASSIFICATION_LABELS[locale].get(cls, cls)

    # range position above low
    above_low = None
    if price and low and low > 0:
        above_low = (price - low) / low
    upside = None
    if target and price and price > 0 and target > 0:
        upside = (target - price) / price

    above_low_s = _pct(above_low) if above_low is not None else "\u2014"
    upside_s = _pct(upside) if upside is not None else "\u2014"
    dy_s = f"{dy * 100:.1f}%"

    templates = {
        "en": (
            f"{name} scores {score}/100 ({label}). It trades about {above_low_s} above its 52-week low, "
            f"with roughly {upside_s} upside to the analyst target and a {dy_s} dividend yield."
        ),
        "fr": (
            f"{name} obtient {score}/100 ({label}). Le titre se n\u00e9gocie environ {above_low_s} au-dessus de son plus bas de 52 semaines, "
            f"avec un potentiel d'environ {upside_s} jusqu'\u00e0 l'objectif des analystes et un rendement de dividende de {dy_s}."
        ),
        "pt": (
            f"{name} pontua {score}/100 ({label}). Est\u00e1 sendo negociada cerca de {above_low_s} acima da m\u00ednima de 52 semanas, "
            f"com potencial de aproximadamente {upside_s} at\u00e9 o alvo dos analistas e um dividend yield de {dy_s}."
        ),
        "es": (
            f"{name} obtiene {score}/100 ({label}). Cotiza alrededor de {above_low_s} por encima de su m\u00ednimo de 52 semanas, "
            f"con un potencial de aproximadamente {upside_s} hasta el objetivo de los analistas y una rentabilidad por dividendo del {dy_s}."
        ),
    }
    return templates[locale]


ALERT_TEMPLATES = {
    "buy_zone": {
        "en": "{ticker} entered the BUY ZONE: {price}, just {above_low} above its 52-week low. Analyst target {target} ({upside}), dividend {dy}.",
        "fr": "{ticker} est entr\u00e9 dans la ZONE D'ACHAT : {price}, seulement {above_low} au-dessus de son plus bas de 52 semaines. Objectif {target} ({upside}), dividende {dy}.",
        "pt": "{ticker} entrou na ZONA DE COMPRA: {price}, apenas {above_low} acima da m\u00ednima de 52 semanas. Alvo {target} ({upside}), dividendo {dy}.",
        "es": "{ticker} entr\u00f3 en la ZONA DE COMPRA: {price}, solo {above_low} por encima de su m\u00ednimo de 52 semanas. Objetivo {target} ({upside}), dividendo {dy}.",
    },
    "sell_zone": {
        "en": "{ticker} entered the SELL ZONE: {price}, near its 52-week high or analyst target {target}.",
        "fr": "{ticker} est entr\u00e9 dans la ZONE DE VENTE : {price}, proche de son sommet de 52 semaines ou de l'objectif {target}.",
        "pt": "{ticker} entrou na ZONA DE VENDA: {price}, perto da m\u00e1xima de 52 semanas ou do alvo {target}.",
        "es": "{ticker} entr\u00f3 en la ZONA DE VENTA: {price}, cerca de su m\u00e1ximo de 52 semanas o del objetivo {target}.",
    },
    "target_reached": {
        "en": "{ticker} reached the analyst target of {target} (now {price}).",
        "fr": "{ticker} a atteint l'objectif des analystes de {target} (maintenant {price}).",
        "pt": "{ticker} atingiu o alvo dos analistas de {target} (agora {price}).",
        "es": "{ticker} alcanz\u00f3 el objetivo de los analistas de {target} (ahora {price}).",
    },
    "price_below": {
        "en": "{ticker} dropped below {threshold}: now {price}.",
        "fr": "{ticker} est pass\u00e9 sous {threshold} : maintenant {price}.",
        "pt": "{ticker} caiu abaixo de {threshold}: agora {price}.",
        "es": "{ticker} baj\u00f3 de {threshold}: ahora {price}.",
    },
    "price_above": {
        "en": "{ticker} rose above {threshold}: now {price}.",
        "fr": "{ticker} est pass\u00e9 au-dessus de {threshold} : maintenant {price}.",
        "pt": "{ticker} subiu acima de {threshold}: agora {price}.",
        "es": "{ticker} super\u00f3 {threshold}: ahora {price}.",
    },
    "score_threshold": {
        "en": "{ticker} Opportunity Score crossed {threshold}: now {score}/100 ({label}).",
        "fr": "{ticker} : le score d'opportunit\u00e9 a franchi {threshold} : maintenant {score}/100 ({label}).",
        "pt": "{ticker}: o Opportunity Score cruzou {threshold}: agora {score}/100 ({label}).",
        "es": "{ticker}: el Opportunity Score cruz\u00f3 {threshold}: ahora {score}/100 ({label}).",
    },
    "dividend_change": {
        "en": "{ticker} dividend yield changed to {dy}.",
        "fr": "{ticker} : le rendement du dividende est pass\u00e9 \u00e0 {dy}.",
        "pt": "{ticker}: o dividend yield mudou para {dy}.",
        "es": "{ticker}: la rentabilidad por dividendo cambi\u00f3 a {dy}.",
    },
    "daily_drop": {
        "en": "{ticker} fell {drop} today to {price}.",
        "fr": "{ticker} a chut\u00e9 de {drop} aujourd'hui \u00e0 {price}.",
        "pt": "{ticker} caiu {drop} hoje para {price}.",
        "es": "{ticker} cay\u00f3 {drop} hoy a {price}.",
    },
}


def build_alert_message(alert_type: str, asset: dict, params: dict, locale: str = "en") -> str:
    locale = locale if locale in CLASSIFICATION_LABELS else "en"
    tpl = ALERT_TEMPLATES.get(alert_type, {}).get(locale)
    if not tpl:
        return f"{asset.get('ticker')}: {alert_type}"
    cur = asset.get("currency") or ""
    price = asset.get("price")
    low = asset.get("low_52w")
    target = asset.get("target_mean")
    dy = asset.get("dividend_yield") or 0.0
    score = asset.get("score")
    cls = asset.get("classification", "hold")

    def money(v):
        return f"{cur} {v:,.2f}" if v is not None else "\u2014"

    above_low = (price - low) / low if (price and low and low > 0) else None
    upside = (target - price) / price if (target and price and price > 0) else None

    return tpl.format(
        ticker=asset.get("ticker"),
        price=money(price),
        target=money(target),
        threshold=money(params.get("value")) if params.get("value") is not None else params.get("value"),
        above_low=_pct(above_low) if above_low is not None else "\u2014",
        upside=("+" + _pct(upside)) if upside is not None else "\u2014",
        dy=f"{dy * 100:.1f}%",
        score=score,
        label=CLASSIFICATION_LABELS[locale].get(cls, cls),
        drop=f"{abs(params.get('observed_drop', 0)) * 100:.1f}%",
    )
