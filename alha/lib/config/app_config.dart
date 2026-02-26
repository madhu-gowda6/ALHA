class AppConfig {
  static const String apiGatewayUrl = String.fromEnvironment(
    'API_GW_URL',
    defaultValue: 'https://placeholder.execute-api.us-east-1.amazonaws.com',
  );

  static const String albDns = String.fromEnvironment(
    'ALB_DNS',
    defaultValue: 'placeholder.us-east-1.elb.amazonaws.com',
  );

  static String get wsUrl => 'wss://$albDns/ws';

  static const String cognitoClientId = String.fromEnvironment(
    'COGNITO_CLIENT_ID',
    defaultValue: '',
  );

  static const String cognitoUserPoolId = String.fromEnvironment(
    'COGNITO_USER_POOL_ID',
    defaultValue: '',
  );
}
