import json

import pytest

from app import create_app


@pytest.fixture(scope="module")
def client():
    """Create a Flask test client with the full presidio app."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert b"Presidio service is up" in resp.data


# ---------------------------------------------------------------------------
# Analyze – English
# ---------------------------------------------------------------------------


class TestAnalyzeEnglish:
    def test_person_and_email(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "My name is John Smith and my email is john@example.com",
                "language": "en",
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        entity_types = {r["entity_type"] for r in results}
        assert "PERSON" in entity_types
        assert "EMAIL_ADDRESS" in entity_types

    def test_phone_number(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "Call me at 212-555-1234",
                "language": "en",
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        entity_types = {r["entity_type"] for r in results}
        assert "PHONE_NUMBER" in entity_types

    def test_credit_card(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "My credit card number is 4111111111111111",
                "language": "en",
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        entity_types = {r["entity_type"] for r in results}
        assert "CREDIT_CARD" in entity_types

    def test_url_and_ip(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "Visit https://example.com from 192.168.1.1",
                "language": "en",
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        entity_types = {r["entity_type"] for r in results}
        assert "URL" in entity_types
        assert "IP_ADDRESS" in entity_types

    def test_iban(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "My IBAN is DE89370400440532013000",
                "language": "en",
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        entity_types = {r["entity_type"] for r in results}
        assert "IBAN_CODE" in entity_types

    def test_no_pii(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "The weather is nice today",
                "language": "en",
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        assert results == []

    def test_batch_texts(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": [
                    "My name is Alice",
                    "Call 212-555-0000",
                ],
                "language": "en",
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        assert isinstance(results, list)
        assert len(results) == 2
        assert any(r["entity_type"] == "PERSON" for r in results[0])
        assert any(r["entity_type"] == "PHONE_NUMBER" for r in results[1])

    def test_score_threshold(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "My name is John Smith and my email is john@example.com",
                "language": "en",
                "score_threshold": 0.99,
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        for r in results:
            assert r["score"] >= 0.99

    def test_specific_entities(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "My name is John Smith and my email is john@example.com",
                "language": "en",
                "entities": ["EMAIL_ADDRESS"],
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        entity_types = {r["entity_type"] for r in results}
        assert "EMAIL_ADDRESS" in entity_types
        assert "PERSON" not in entity_types


# ---------------------------------------------------------------------------
# Analyze – German
# ---------------------------------------------------------------------------


class TestAnalyzeGerman:
    def test_email(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "Meine E-Mail ist hans@beispiel.de",
                "language": "de",
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        entity_types = {r["entity_type"] for r in results}
        assert "EMAIL_ADDRESS" in entity_types

    def test_person(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "Der Patient heißt Hans Müller und wohnt in Berlin",
                "language": "de",
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        entity_types = {r["entity_type"] for r in results}
        assert "PERSON" in entity_types
        assert "LOCATION" in entity_types

    def test_iban(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "Meine IBAN ist DE89370400440532013000",
                "language": "de",
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        entity_types = {r["entity_type"] for r in results}
        assert "IBAN_CODE" in entity_types

    def test_credit_card(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "Meine Kreditkarte ist 4111111111111111",
                "language": "de",
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        entity_types = {r["entity_type"] for r in results}
        assert "CREDIT_CARD" in entity_types

    def test_phone_number(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "Ruf mich an unter +49 30 123456",
                "language": "de",
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        entity_types = {r["entity_type"] for r in results}
        assert "PHONE_NUMBER" in entity_types

    def test_url(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "Besuche https://beispiel.de für mehr Informationen",
                "language": "de",
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        entity_types = {r["entity_type"] for r in results}
        assert "URL" in entity_types

    def test_no_pii(self, client):
        resp = client.post(
            "/analyze",
            json={
                "text": "Das Wetter ist heute schön",
                "language": "de",
            },
        )
        assert resp.status_code == 200
        results = json.loads(resp.data)
        assert results == []


# ---------------------------------------------------------------------------
# Analyze – Error cases
# ---------------------------------------------------------------------------


class TestAnalyzeErrors:
    def test_missing_text(self, client):
        resp = client.post(
            "/analyze",
            json={"language": "en"},
        )
        assert resp.status_code == 500

    def test_missing_language(self, client):
        resp = client.post(
            "/analyze",
            json={"text": "Hello John"},
        )
        assert resp.status_code == 500

    def test_unsupported_language(self, client):
        resp = client.post(
            "/analyze",
            json={"text": "Hello", "language": "xx"},
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Recognizers & Supported Entities
# ---------------------------------------------------------------------------


class TestRecognizers:
    def test_recognizers_default(self, client):
        resp = client.get("/recognizers")
        assert resp.status_code == 200
        names = json.loads(resp.data)
        assert isinstance(names, list)
        assert len(names) > 0

    def test_recognizers_english(self, client):
        resp = client.get("/recognizers?language=en")
        assert resp.status_code == 200
        names = json.loads(resp.data)
        assert "SpacyRecognizer" in names
        assert "EmailRecognizer" in names

    def test_recognizers_german(self, client):
        resp = client.get("/recognizers?language=de")
        assert resp.status_code == 200
        names = json.loads(resp.data)
        assert "SpacyRecognizer" in names
        assert "EmailRecognizer" in names


class TestSupportedEntities:
    def test_supported_entities_default(self, client):
        resp = client.get("/supportedentities")
        assert resp.status_code == 200
        entities = json.loads(resp.data)
        assert isinstance(entities, list)
        assert "PERSON" in entities
        assert "EMAIL_ADDRESS" in entities

    def test_supported_entities_english(self, client):
        resp = client.get("/supportedentities?language=en")
        assert resp.status_code == 200
        entities = json.loads(resp.data)
        assert "PERSON" in entities
        assert "CREDIT_CARD" in entities

    def test_supported_entities_german(self, client):
        resp = client.get("/supportedentities?language=de")
        assert resp.status_code == 200
        entities = json.loads(resp.data)
        assert "PERSON" in entities
        assert "EMAIL_ADDRESS" in entities
        assert "IBAN_CODE" in entities


# ---------------------------------------------------------------------------
# Anonymize
# ---------------------------------------------------------------------------


class TestAnonymize:
    def test_anonymize_english(self, client):
        # First analyze to get results
        analyze_resp = client.post(
            "/analyze",
            json={
                "text": "My name is John Smith and my email is john@example.com",
                "language": "en",
            },
        )
        analyzer_results = json.loads(analyze_resp.data)

        resp = client.post(
            "/anonymize",
            json={
                "text": "My name is John Smith and my email is john@example.com",
                "analyzer_results": analyzer_results,
            },
        )
        assert resp.status_code == 200
        result = json.loads(resp.data)
        assert (
            result["text"]
            == "My name is <PERSON> and my email is <EMAIL_ADDRESS>"
        )

    def test_anonymize_german(self, client):
        text = "Meine E-Mail ist hans@beispiel.de"
        analyze_resp = client.post(
            "/analyze",
            json={
                "text": text,
                "language": "de",
            },
        )
        analyzer_results = json.loads(analyze_resp.data)

        resp = client.post(
            "/anonymize",
            json={
                "text": text,
                "analyzer_results": analyzer_results,
            },
        )
        assert resp.status_code == 200
        result = json.loads(resp.data)
        assert result["text"] == "Meine E-Mail ist <EMAIL_ADDRESS>"

    def test_anonymize_with_custom_operator(self, client):
        analyze_resp = client.post(
            "/analyze",
            json={
                "text": "My name is John Smith",
                "language": "en",
            },
        )
        analyzer_results = json.loads(analyze_resp.data)

        resp = client.post(
            "/anonymize",
            json={
                "text": "My name is John Smith",
                "analyzer_results": analyzer_results,
                "anonymizers": {
                    "PERSON": {"type": "replace", "new_value": "<REDACTED>"}
                },
            },
        )
        assert resp.status_code == 200
        result = json.loads(resp.data)
        assert result["text"] == "My name is <REDACTED>"

    def test_anonymize_empty_results(self, client):
        resp = client.post(
            "/anonymize",
            json={
                "text": "The weather is nice",
                "analyzer_results": [],
            },
        )
        assert resp.status_code == 200
        result = json.loads(resp.data)
        assert result["text"] == "The weather is nice"

    def test_anonymize_missing_body(self, client):
        resp = client.post(
            "/anonymize",
            content_type="application/json",
            data="",
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Anonymizers / Deanonymizers listings
# ---------------------------------------------------------------------------


class TestAnonymizersListing:
    def test_anonymizers(self, client):
        resp = client.get("/anonymizers")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert isinstance(data, list)
        assert "replace" in data
        assert "hash" in data

    def test_deanonymizers(self, client):
        resp = client.get("/deanonymizers")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Deanonymize
# ---------------------------------------------------------------------------


class TestDeanonymize:
    def test_deanonymize(self, client):
        key = "WmZq4t7w!z%C&F)J"

        # Step 1: encrypt via anonymize
        analyze_resp = client.post(
            "/analyze",
            json={"text": "My name is John", "language": "en"},
        )
        analyzer_results = json.loads(analyze_resp.data)

        encrypt_resp = client.post(
            "/anonymize",
            json={
                "text": "My name is John",
                "analyzer_results": analyzer_results,
                "anonymizers": {
                    "DEFAULT": {"type": "encrypt", "key": key},
                },
            },
        )
        assert encrypt_resp.status_code == 200
        encrypted = json.loads(encrypt_resp.data)
        encrypted_text = encrypted["text"]

        # Build deanonymize input from the anonymize response items
        anonymizer_results = []
        for item in encrypted.get("items", []):
            anonymizer_results.append(
                {
                    "start": item["start"],
                    "end": item["end"],
                    "entity_type": item["entity_type"],
                    "text": item["text"],
                    "operator": item["operator"],
                }
            )

        # Step 2: decrypt via deanonymize
        resp = client.post(
            "/deanonymize",
            json={
                "text": encrypted_text,
                "deanonymizers": {
                    "DEFAULT": {"type": "decrypt", "key": key},
                },
                "anonymizer_results": anonymizer_results,
            },
        )
        assert resp.status_code == 200
        result = json.loads(resp.data)
        assert "text" in result
        assert "John" in result["text"]

    def test_deanonymize_missing_body(self, client):
        resp = client.post(
            "/deanonymize",
            content_type="application/json",
            data="",
        )
        assert resp.status_code == 400
