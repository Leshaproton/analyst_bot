def message_id_batches(latest_message_id: int, limit: int = 1000,
                       batch_size: int = 100) -> list[list[int]]:
    """Return recent Telegram message IDs split into API-sized batches."""
    if latest_message_id < 1 or limit < 1 or not 1 <= batch_size <= 100:
        return []
    first = max(1, latest_message_id - limit + 1)
    message_ids = list(range(first, latest_message_id + 1))
    return [message_ids[index:index + batch_size] for index in range(0, len(message_ids), batch_size)]
