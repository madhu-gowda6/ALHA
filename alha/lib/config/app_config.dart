class AppConfig {
  static const String apiGatewayUrl = String.fromEnvironment(
    'API_GW_URL',
    defaultValue: 'https://nwgfpoh71m.execute-api.us-east-1.amazonaws.com/prod',
  );

  static const String albDns = String.fromEnvironment(
    'ALB_DNS',
    defaultValue: 'alha-alb-1820780785.us-east-1.elb.amazonaws.com',
  );

  static String get wsUrl {
    if (Uri.base.scheme == 'https') {
      // On HTTPS (CloudFront), route WebSocket through CloudFront /ws behavior
      // so the browser never makes a mixed-content ws:// request.
      return 'wss://${Uri.base.host}/ws';
    }
    return 'ws://$albDns/ws';
  }

  static const String cognitoClientId = String.fromEnvironment(
    'COGNITO_CLIENT_ID',
    defaultValue: '',
  );

  static const String cognitoUserPoolId = String.fromEnvironment(
    'COGNITO_USER_POOL_ID',
    defaultValue: '',
  );
}
