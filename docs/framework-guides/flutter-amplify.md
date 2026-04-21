# Flutter + Amplify + Challenge Tokens

## The Problem

Flutter apps using AWS Amplify make API calls through API Gateway. If API Gateway has WAF challenge rules, the native HTTP client can't render or solve HTML challenges.

## Solution

### 1. Use AWS WAF Mobile SDK

AWS WAF provides a mobile SDK that handles token acquisition natively:

```dart
// Add aws-waf-token to your API requests
final token = await WafTokenProvider.getToken();
final response = await http.get(
  Uri.parse('https://api.yoursite.com/data'),
  headers: {'x-aws-waf-token': token},
);
```

### 2. WebView fallback for interactive challenges

If the WAF requires an interactive challenge, present it in a WebView:

```dart
if (response.statusCode == 403) {
  final token = await Navigator.push(context,
    MaterialPageRoute(builder: (_) => ChallengeWebView(url: apiUrl)),
  );
  // Retry with token
}
```

### 3. Exempt mobile API paths

Configure your API Gateway to use a separate WAF rule group for mobile endpoints that uses token validation instead of interactive challenges.

## Verification

```bash
# Test your API endpoint
challenge-validator test https://api.yoursite.com/mobile --token <waf-token>
```
