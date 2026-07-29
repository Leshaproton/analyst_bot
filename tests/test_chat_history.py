from app.services.chat_history import message_id_batches


def test_message_ids_are_split_into_telegram_batches() -> None:
    batches = message_id_batches(250)
    assert len(batches) == 3
    assert batches[0] == list(range(1, 101))
    assert batches[-1] == list(range(201, 251))
    assert all(len(batch) <= 100 for batch in batches)


def test_only_recent_message_ids_are_selected() -> None:
    batches = message_id_batches(1500, limit=1000)
    ids = [message_id for batch in batches for message_id in batch]
    assert ids[0] == 501
    assert ids[-1] == 1500
    assert len(ids) == 1000


def test_invalid_limits_produce_no_batches() -> None:
    assert message_id_batches(0) == []
    assert message_id_batches(10, batch_size=101) == []
