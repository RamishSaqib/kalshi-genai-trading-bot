import pytest
from unittest.mock import patch
from grok_client import GrokClient

def test_analyze_market_success():
    client = GrokClient("api_key")
    mock_response = {
        "choices": [{
            "message": {
                "content": "{\"ticker\": \"ABC\", \"explanation\": \"Good logic\"}"
            }
        }]
    }
    
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response
        
        result = client.analyze_market({"ticker": "ABC"})
        assert result["ticker"] == "ABC"
        assert result["explanation"] == "Good logic"

def test_analyze_market_null():
    client = GrokClient("api_key")
    mock_response = {
        "choices": [{
            "message": {
                "content": "{\"ticker\": null, \"explanation\": null}"
            }
        }]
    }
    
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response
        
        result = client.analyze_market({"ticker": "ABC"})
        assert result["ticker"] is None


def test_analyze_market_includes_rules_in_prompt():
    """Test that rules_primary, rules_secondary, yes_sub_title, no_sub_title are included in prompt."""
    client = GrokClient("api_key")
    mock_response = {
        "choices": [{
            "message": {
                "content": '{"ticker": "ABC", "side": "yes", "explanation": "Good based on rules"}'
            }
        }]
    }

    market_data = {
        "ticker": "ABC",
        "title": "Will X happen?",
        "subtitle": "Test subtitle",
        "category": "Test",
        "yes_ask": 50,
        "rules_primary": "The market resolves YES if X happens by Dec 31.",
        "rules_secondary": "Settlement based on official announcement.",
        "yes_sub_title": "X will happen",
        "no_sub_title": "X will not happen",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        result = client.analyze_market(market_data)

        # Verify the prompt contains market rules
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        user_message = payload["messages"][1]["content"]

        assert "The market resolves YES if X happens by Dec 31." in user_message
        assert "Settlement based on official announcement." in user_message
        assert "X will happen" in user_message  # yes_sub_title
        assert "X will not happen" in user_message  # no_sub_title
        assert result["ticker"] == "ABC"


def test_analyze_market_works_without_rules():
    """Test backwards compatibility - analyze_market works when rules are not present."""
    client = GrokClient("api_key")
    mock_response = {
        "choices": [{
            "message": {
                "content": '{"ticker": "DEF", "side": "no", "explanation": "No good trade"}'
            }
        }]
    }

    # Market data without any rules fields
    market_data = {
        "ticker": "DEF",
        "title": "Will Y happen?",
        "subtitle": "Another subtitle",
        "category": "Other",
        "yes_ask": 75,
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        result = client.analyze_market(market_data)

        # Should work fine without rules
        assert result["ticker"] == "DEF"
        assert result["side"] == "no"

        # Verify the prompt doesn't have empty "Market Rules:" section
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        user_message = payload["messages"][1]["content"]

        # Should not have rules section when no rules provided
        assert "Market Rules:" not in user_message
