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
    final wsScheme = Uri.base.scheme == 'https' ? 'wss' : 'ws';
    return '$wsScheme://$albDns/ws';
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
