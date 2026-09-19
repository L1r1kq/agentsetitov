from agentse.medical_guard import critique_report, has_red_flag, is_health_fact, strip_diagnosis
from agentse.report import compose_reference_report, is_blank_answer, looks_like_dump, select_cards


def test_blocks_diagnosis_wording():
    issues = critique_report("кашель", "У вас пневмония, примите 500 мг амоксициллина")
    assert issues


def test_red_flag_requires_help():
    issues = critique_report("давящая боль в груди", "Подождите дома, само пройдёт. Справочный отчёт.")
    assert any("красн" in i for i in issues)


def test_disclaimer_injected():
    text = strip_diagnosis("Кашель часто разбирают в карточке fever_cough.")
    assert "не диагноз" in text.lower() or "справочн" in text.lower()


def test_phi_not_memory():
    assert is_health_fact("температура 38 и кашель три дня")
    assert not is_health_fact("пользователь просит ответы короче")


def test_negated_chest_is_not_red_flag():
    assert not has_red_flag("Температура 38.2 и кашель, одышки нет, грудь не болит")
    assert has_red_flag("Давящая боль в груди и холодный пот")


def test_blank_json_and_fallback_report():
    assert is_blank_answer("{}")
    assert looks_like_dump("knowledge/INDEX.md knowledge/a knowledge/b knowledge/c")
    assert select_cards("Температура 38.2 и сухой кашель, одышки нет") == ["fever_cough.md"]
    report = compose_reference_report(
        "Температура 38.2 три дня и сухой кашель, одышки нет, грудь не болит"
    )
    assert "не диагноз" in report.lower()
    assert "abdominal" not in report
    assert "Каталог справочника" not in report
    assert "ОРВИ" in report
    assert "103" not in report
