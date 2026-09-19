from agentse.medical_guard import critique_report, has_red_flag, is_health_fact, strip_diagnosis
from agentse.report import compose_reference_report, is_blank_answer


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
    report = compose_reference_report(
        "Температура 38.2 и сухой кашель, одышки нет, грудь не болит",
        ["fever_cough.md: ОРВИ-подобные жалобы в справочнике"],
        [{"text": "жар и кашель", "meta": {"file": "knowledge/fever_cough.md"}}],
    )
    assert "не диагноз" in report.lower() or "справочн" in report.lower()
    assert "fever_cough" in report
    assert "103" not in report
