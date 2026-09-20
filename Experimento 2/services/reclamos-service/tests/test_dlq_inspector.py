from app.dlq_inspector import dlq_status, peek_messages


class FakeSqsClient:
    def __init__(self, *, attributes: dict[str, dict[str, str]], batches: list[list[dict[str, str]]]) -> None:
        self._attributes = attributes
        self._batches = list(batches)
        self.receive_calls = 0

    def get_queue_attributes(self, *, QueueUrl: str, AttributeNames: list[str]) -> dict:
        del AttributeNames
        return {"Attributes": self._attributes[QueueUrl]}

    def receive_message(self, *, QueueUrl: str, MaxNumberOfMessages: int, VisibilityTimeout: int) -> dict:
        del QueueUrl, MaxNumberOfMessages
        assert VisibilityTimeout == 0, "DLQ peeks must never hide messages from other readers"
        self.receive_calls += 1
        if not self._batches:
            return {"Messages": []}
        return {"Messages": self._batches.pop(0)}


def test_dlq_status_reports_both_queues() -> None:
    client = FakeSqsClient(
        attributes={
            "entrada-dlq": {"ApproximateNumberOfMessages": "3"},
            "pagos-dlq": {"ApproximateNumberOfMessages": "0"},
        },
        batches=[],
    )

    counts = dlq_status(client, entrada_dlq_url="entrada-dlq", pagos_dlq_url="pagos-dlq")

    assert counts == {"entrada_parametrica_dlq": 3, "ordenes_pagos_dlq": 0}


def test_peek_messages_never_deletes_and_stops_when_queue_is_drained() -> None:
    client = FakeSqsClient(
        attributes={},
        batches=[
            [{"MessageId": "m1", "Body": "{}"}, {"MessageId": "m2", "Body": "{}"}],
            [],
        ],
    )

    messages = peek_messages(client, "entrada-dlq", limit=10)

    assert [message.message_id for message in messages] == ["m1", "m2"]
    assert client.receive_calls == 2


def test_peek_messages_respects_the_requested_limit_across_batches() -> None:
    client = FakeSqsClient(
        attributes={},
        batches=[[{"MessageId": f"m{i}", "Body": "{}"} for i in range(10)]] * 3,
    )

    messages = peek_messages(client, "entrada-dlq", limit=15)

    assert len(messages) == 15
