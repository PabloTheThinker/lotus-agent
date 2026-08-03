from lotus.speech.thread_flow import (
    last_assistant_question,
    thread_flow_directive,
)


def test_extracts_last_lotus_question():
    history = [
        {"role": "user", "content": "i fucked up"},
        {
            "role": "assistant",
            "content": "Okay — rough send. What were you reaching for when you texted?",
        },
    ]
    q = last_assistant_question(history)
    assert "reaching" in q.lower()


def test_thread_receives_answer():
    history = [
        {
            "role": "assistant",
            "content": "What were you reaching for — loneliness, anger, wanting them to know?",
        }
    ]
    block = thread_flow_directive(
        "loneliness mostly. i just didn't want to feel alone in it.",
        history=history,
    )
    assert "RECEIVE" in block
    assert "re-ask" in block.lower() or "NOT re-ask" in block


def test_gateway_includes_thread_when_history():
    from lotus.speech.gateway import gateway_block

    text = gateway_block(
        "mostly loneliness i guess",
        history=[
            {
                "role": "assistant",
                "content": "What were you reaching for when you hit send?",
            }
        ],
    )
    assert "THREAD" in text
    assert "RECEIVE" in text
