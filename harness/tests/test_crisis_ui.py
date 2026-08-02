from lotus.guardrails import crisis_ui_payload


def test_crisis_ui_payload_spanish_gb():
    es = crisis_ui_payload("es", "GB")
    assert es["lang"] == "es"
    assert "Importas" in es["title"]
    assert "116 123" in es["body_html"]
    assert "iasp.info" in es["body_html"]


def test_crisis_ui_payload_fallback_region():
    us = crisis_ui_payload("zz", "XX")
    assert us["lang"] == "en"
    assert us["region"] == "US"
    assert "988" in us["body_html"]
