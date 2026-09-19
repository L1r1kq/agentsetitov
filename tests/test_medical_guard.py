from agentse.medical_guard import critique_report, is_health_fact, strip_diagnosis


def test_blocks_diagnosis_wording():
    issues = critique_report("кашель", "У вас пневмония, примите 500 мг")
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
