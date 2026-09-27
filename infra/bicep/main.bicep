// Enterprise AI Playground: Azure topology for a pilot that scales to a tenant.
// Two Container Apps (web, api), PostgreSQL Flexible Server with pgvector, Azure Cache for Redis,
// Key Vault for provider keys, Log Analytics for both apps, a dynamic sessions pool for notebook code,
// and a container registry for the images built by CI.
//
// Deploy: infra/deploy.sh (wraps `az deployment group create`). Validate: `az bicep build --file infra/bicep/main.bicep`.

targetScope = 'resourceGroup'

@description('Short name used as a prefix for every resource, lowercase letters and digits only.')
@minLength(3)
@maxLength(12)
param prefix string = 'aiplay'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Environment tag: pilot, staging or production.')
@allowed(['pilot', 'staging', 'production'])
param environment string = 'pilot'

@description('Container image for the API, for example myregistry.azurecr.io/playground-api:1.0.0.')
param apiImage string

@description('Container image for the web app.')
param webImage string

@description('PostgreSQL administrator login.')
param postgresAdmin string = 'playground'

@secure()
@description('PostgreSQL administrator password.')
param postgresPassword string

@secure()
@description('Shared secret between the web app and the API (X-Internal-Key).')
param internalKey string

@secure()
@description('Auth.js session secret for the web app.')
param authSecret string

@description('Microsoft Entra ID application (client) id for sign-in. Leave empty to use seeded development users (pilot only).')
param entraClientId string = ''

@secure()
@description('Microsoft Entra ID client secret.')
param entraClientSecret string = ''

@description('Microsoft Entra ID issuer, for example https://login.microsoftonline.com/<tenant-id>/v2.0.')
param entraIssuer string = ''

@secure()
@description('Anthropic API key. Stored in Key Vault and referenced by the API.')
param anthropicApiKey string = ''

@secure()
@description('OpenAI API key.')
param openaiApiKey string = ''

@secure()
@description('Google Gemini API key.')
param geminiApiKey string = ''

@secure()
@description('DeepSeek API key.')
param deepseekApiKey string = ''

@secure()
@description('NVIDIA NIM API key (build.nvidia.com): Nemotron, Hermes and the NIM shelf.')
param nvidiaNimApiKey string = ''

@secure()
@description('Mistral API key.')
param mistralApiKey string = ''

@secure()
@description('xAI API key.')
param xaiApiKey string = ''

@secure()
@description('Groq API key.')
param groqApiKey string = ''

@secure()
@description('Fernet key that encrypts personal provider keys at rest (python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"). Required.')
param keyEncryptionKey string

@description('Minimum replicas for the API. 1 keeps the canary scheduler and checkpoints warm.')
param apiMinReplicas int = 1

var suffix = uniqueString(resourceGroup().id)
var tags = { product: 'enterprise-ai-playground', environment: environment }
var postgresName = '${prefix}-pg-${suffix}'
var databaseName = 'playground'

// ---------------------------------------------------------------- observability ----------------------------------------------------------------

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs-${suffix}'
  location: location
  tags: tags
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 30 }
}

// ---------------------------------------------------------------- registry and secrets ----------------------------------------------------------------

@description('Name of the container registry that already holds the images (deploy.sh creates it before the template runs, so images can be pushed by ACR Tasks or by the images workflow).')
param registryName string

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: registryName
}

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${prefix}-kv-${suffix}'
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 30
  }
}

var secretDefinitions = [
  { name: 'internal-key', value: internalKey }
  { name: 'auth-secret', value: authSecret }
  { name: 'postgres-password', value: postgresPassword }
  { name: 'anthropic-api-key', value: anthropicApiKey }
  { name: 'openai-api-key', value: openaiApiKey }
  { name: 'gemini-api-key', value: geminiApiKey }
  { name: 'deepseek-api-key', value: deepseekApiKey }
  { name: 'nvidia-nim-api-key', value: nvidiaNimApiKey }
  { name: 'mistral-api-key', value: mistralApiKey }
  { name: 'xai-api-key', value: xaiApiKey }
  { name: 'groq-api-key', value: groqApiKey }
  { name: 'key-encryption-key', value: keyEncryptionKey }
  { name: 'entra-client-secret', value: entraClientSecret }
]

resource secrets 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = [for s in secretDefinitions: {
  parent: vault
  name: s.name
  properties: { value: empty(s.value) ? 'unset' : s.value }
}]

// ---------------------------------------------------------------- data ----------------------------------------------------------------

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: postgresName
  location: location
  tags: tags
  sku: { name: environment == 'production' ? 'Standard_D2ds_v5' : 'Standard_B1ms', tier: environment == 'production' ? 'GeneralPurpose' : 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: postgresAdmin
    administratorLoginPassword: postgresPassword
    storage: { storageSizeGB: 32, autoGrow: 'Enabled' }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: environment == 'production' ? 'ZoneRedundant' : 'Disabled' }
    authConfig: { passwordAuth: 'Enabled', activeDirectoryAuth: 'Enabled', tenantId: subscription().tenantId }
  }
}

resource postgresExtensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-12-01-preview' = {
  parent: postgres
  name: 'azure.extensions'
  properties: { value: 'VECTOR,PG_TRGM', source: 'user-override' }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  parent: postgres
  name: databaseName
  properties: { charset: 'UTF8', collation: 'en_US.utf8' }
}

resource postgresAzureAccess 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-12-01-preview' = {
  parent: postgres
  name: 'allow-azure-services'
  properties: { startIpAddress: '0.0.0.0', endIpAddress: '0.0.0.0' }
}

// ---------------------------------------------------------------- compute ----------------------------------------------------------------

resource environmentAca 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-env-${suffix}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: { customerId: logs.properties.customerId, sharedKey: logs.listKeys().primarySharedKey }
    }
    zoneRedundant: environment == 'production'
  }
}

resource sessionsPool 'Microsoft.App/sessionPools@2024-02-02-preview' = {
  name: '${prefix}-sessions-${suffix}'
  location: location
  tags: tags
  properties: {
    poolManagementType: 'Dynamic'
    containerType: 'PythonLTS'
    scaleConfiguration: { maxConcurrentSessions: 10, readySessionInstances: environment == 'production' ? 2 : 0 }
    dynamicPoolConfiguration: { executionType: 'Timed', cooldownPeriodInSeconds: 300 }
    sessionNetworkConfiguration: { status: 'EgressDisabled' }
  }
}

// Provider keys that were supplied. Container Apps reject secrets with empty values, and an empty environment variable
// would make the catalog think a key exists; keys left unset are simply not deployed.
var providerKeys = [
  { secret: 'anthropic-api-key', env: 'ANTHROPIC_API_KEY', value: anthropicApiKey }
  { secret: 'openai-api-key', env: 'OPENAI_API_KEY', value: openaiApiKey }
  { secret: 'gemini-api-key', env: 'GEMINI_API_KEY', value: geminiApiKey }
  { secret: 'deepseek-api-key', env: 'DEEPSEEK_API_KEY', value: deepseekApiKey }
  { secret: 'nvidia-nim-api-key', env: 'NVIDIA_NIM_API_KEY', value: nvidiaNimApiKey }
  { secret: 'mistral-api-key', env: 'MISTRAL_API_KEY', value: mistralApiKey }
  { secret: 'xai-api-key', env: 'XAI_API_KEY', value: xaiApiKey }
  { secret: 'groq-api-key', env: 'GROQ_API_KEY', value: groqApiKey }
]
var presentProviderKeys = filter(providerKeys, k => !empty(k.value))

var postgresUrl = 'postgresql+psycopg://${postgresAdmin}:${postgresPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/${databaseName}?sslmode=require'

resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-api'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: environmentAca.id
    configuration: {
      ingress: { external: false, targetPort: 8000, transport: 'http', allowInsecure: false }
      registries: [{ server: registry.properties.loginServer, username: registry.name, passwordSecretRef: 'acr-password' }]
      secrets: concat([
        { name: 'acr-password', value: registry.listCredentials().passwords[0].value }
        { name: 'database-url', value: postgresUrl }
        { name: 'internal-key', value: internalKey }
        { name: 'key-encryption-key', value: keyEncryptionKey }
      ], map(presentProviderKeys, k => { name: k.secret, value: k.value }))
    }
    template: {
      containers: [{
        name: 'api'
        image: apiImage
        resources: { cpu: json('1.0'), memory: '2Gi' }
        env: concat([
          { name: 'PLAYGROUND_ENVIRONMENT', value: environment }
          { name: 'PLAYGROUND_DATABASE_URL', secretRef: 'database-url' }
          { name: 'PLAYGROUND_INTERNAL_KEY', secretRef: 'internal-key' }
          { name: 'PLAYGROUND_CORS_ORIGINS', value: '["https://${prefix}-web.${environmentAca.properties.defaultDomain}"]' }
          { name: 'PLAYGROUND_SELF_URL', value: 'https://${prefix}-web.${environmentAca.properties.defaultDomain}/api/pg' }
          { name: 'PLAYGROUND_SANDBOX_ENDPOINT', value: sessionsPool.properties.poolManagementEndpoint }
          { name: 'PLAYGROUND_CHECKPOINT_PATH', value: '/data/checkpoints.db' }
          { name: 'PLAYGROUND_KEY_ENCRYPTION_KEY', secretRef: 'key-encryption-key' }
        ], map(presentProviderKeys, k => { name: k.env, secretRef: k.secret }))
        probes: [
          { type: 'Liveness', httpGet: { path: '/health', port: 8000 }, periodSeconds: 30, timeoutSeconds: 5, initialDelaySeconds: 15, failureThreshold: 3 }
          { type: 'Readiness', httpGet: { path: '/health', port: 8000 }, periodSeconds: 10, timeoutSeconds: 5, initialDelaySeconds: 5 }
        ]
        volumeMounts: [{ volumeName: 'data', mountPath: '/data' }]
      }]
      volumes: [{ name: 'data', storageType: 'EmptyDir' }]
      scale: { minReplicas: apiMinReplicas, maxReplicas: 3, rules: [{ name: 'http', http: { metadata: { concurrentRequests: '50' } } }] }
    }
  }
}

resource web 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-web'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: environmentAca.id
    configuration: {
      ingress: { external: true, targetPort: 3000, transport: 'http', allowInsecure: false }
      registries: [{ server: registry.properties.loginServer, username: registry.name, passwordSecretRef: 'acr-password' }]
      secrets: concat([
        { name: 'acr-password', value: registry.listCredentials().passwords[0].value }
        { name: 'auth-secret', value: authSecret }
        { name: 'internal-key', value: internalKey }
      ], empty(entraClientSecret) ? [] : [{ name: 'entra-client-secret', value: entraClientSecret }])
    }
    template: {
      containers: [{
        name: 'web'
        image: webImage
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: concat([
          { name: 'AUTH_SECRET', secretRef: 'auth-secret' }
          { name: 'AUTH_TRUST_HOST', value: 'true' }
          { name: 'PLAYGROUND_API_URL', value: 'https://${prefix}-api.internal.${environmentAca.properties.defaultDomain}' }
          { name: 'PLAYGROUND_INTERNAL_KEY', secretRef: 'internal-key' }
          { name: 'ALLOW_DEV_LOGIN', value: environment == 'pilot' && empty(entraClientId) ? 'true' : 'false' }
        ], empty(entraClientId) ? [] : [
          { name: 'AUTH_MICROSOFT_ENTRA_ID_ID', value: entraClientId }
          { name: 'AUTH_MICROSOFT_ENTRA_ID_SECRET', secretRef: 'entra-client-secret' }
          { name: 'AUTH_MICROSOFT_ENTRA_ID_ISSUER', value: entraIssuer }
        ])
        // The health route pings the API; give the probe more than the one-second default so a slow API never restarts the web app.
        probes: [{ type: 'Liveness', httpGet: { path: '/api/health', port: 3000 }, periodSeconds: 30, timeoutSeconds: 5, initialDelaySeconds: 10, failureThreshold: 3 }]
      }]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

// ---------------------------------------------------------------- role assignments ----------------------------------------------------------------

// The API's managed identity may read Key Vault secrets (used when keys are rotated without a redeploy).
resource kvSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, api.id, 'kv-secrets-user')
  scope: vault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: api.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// The API executes notebook code in the sessions pool.
resource sessionsExecutor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(sessionsPool.id, api.id, 'sessions-executor')
  scope: sessionsPool
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0fb8eba5-a2bb-4abe-b1c1-49dfad359bb0')
    principalId: api.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output webUrl string = 'https://${web.properties.configuration.ingress.fqdn}'
output apiInternalUrl string = 'https://${prefix}-api.internal.${environmentAca.properties.defaultDomain}'
output registryLoginServer string = registry.properties.loginServer
output keyVaultName string = vault.name
output postgresHost string = postgres.properties.fullyQualifiedDomainName
output sessionsPoolEndpoint string = sessionsPool.properties.poolManagementEndpoint
