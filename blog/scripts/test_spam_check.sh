#!/bin/bash

# Replace with your actual Gemini API key
export GEMINI_API_KEY=""

if [[ "$GEMINI_API_KEY" == "YOUR_GEMINI_API_KEY" ]]; then
  echo "Please replace 'YOUR_GEMINI_API_KEY' in the script with your actual Gemini API key."
  exit 1
fi

# --- Test Case 1: Spam Comment ---
echo "--- Testing Spam Comment ---"
SPAM_TITLE="New Comment on Your Post"
SPAM_BODY="name: Best Pharmacy\nemail: spam@example.com\nwebsite: http://buy-viagra-online.com\nmessage: Great post! Check out our amazing deals at http://buy-viagra-online.com"

# Use a heredoc for the JSON payload to avoid escaping issues
json_payload=$(cat <<EOF
{
  "contents": [
    {
      "parts": [
        {
          "text": "The following pull request is a comment on a blog post. It contains a name, email, optional website, and a message. Please determine if it is spam. Pay close attention to any links, as they may be for spam purposes even if the message itself seems innocent. Answer with only the word 'spam' or 'not_spam'.\n\nTitle: ${SPAM_TITLE}\n\nBody: ${SPAM_BODY}"
        }
      ]
    }
  ]
}
EOF
)

response=$(curl -s -X POST -H "Content-Type: application/json" -d "$json_payload" "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}")

echo "Raw API Response:"
echo "$response"

result=$(echo "$response" | jq -r '.candidates[0].content.parts[0].text')
echo "API Response: $result"

if [[ "$result" == "spam" ]]; then
  echo "✅ Test Passed: Correctly identified as spam."
else
  echo "❌ Test Failed: Did not identify as spam."
fi


# --- Test Case 2: Not Spam Comment ---
echo "\n--- Testing Not Spam Comment ---"
NOT_SPAM_TITLE="New Comment on Your Post"
NOT_SPAM_BODY="name: Jane Doe\nemail: jane.doe@example.com\nwebsite: \nmessage: This is a really insightful post. Thanks for sharing your thoughts!"

# Use a heredoc for the JSON payload to avoid escaping issues
json_payload=$(cat <<EOF
{
  "contents": [
    {
      "parts": [
        {
          "text": "The following pull request is a comment on a blog post. It contains a name, email, optional website, and a message. Please determine if it is spam. Pay close attention to any links, as they may be for spam purposes even if the message itself seems innocent. Answer with only the word 'spam' or 'not_spam'.\n\nTitle: ${NOT_SPAM_TITLE}\n\nBody: ${NOT_SPAM_BODY}"
        }
      ]
    }
  ]
}
EOF
)

response=$(curl -s -X POST -H "Content-Type: application/json" -d "$json_payload" "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}")

echo "Raw API Response:"
echo "$response"

result=$(echo "$response" | jq -r '.candidates[0].content.parts[0].text')
echo "API Response: $result"

if [[ "$result" == "not_spam" ]]; then
  echo "✅ Test Passed: Correctly identified as not spam."
else
  echo "❌ Test Failed: Did not identify as not spam."
fi