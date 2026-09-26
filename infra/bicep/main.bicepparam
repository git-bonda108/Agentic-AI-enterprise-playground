using './main.bicep'

// Copy to main.local.bicepparam (gitignored) and fill in. Secrets can also come from the environment:
//   az deployment group create ... --parameters postgresPassword=$PG_PASSWORD internalKey=$INTERNAL_KEY ...

param prefix = 'aiplay'
param environment = 'pilot'
param apiImage = 'aiplayacr.azurecr.io/playground-api:latest'
param webImage = 'aiplayacr.azurecr.io/playground-web:latest'
param postgresAdmin = 'playground'
param postgresPassword = readEnvironmentVariable('PG_PASSWORD', '')
param internalKey = readEnvironmentVariable('PLAYGROUND_INTERNAL_KEY', '')
param authSecret = readEnvironmentVariable('AUTH_SECRET', '')
param entraClientId = readEnvironmentVariable('AUTH_MICROSOFT_ENTRA_ID_ID', '')
param entraClientSecret = readEnvironmentVariable('AUTH_MICROSOFT_ENTRA_ID_SECRET', '')
param entraIssuer = readEnvironmentVariable('AUTH_MICROSOFT_ENTRA_ID_ISSUER', '')
param anthropicApiKey = readEnvironmentVariable('ANTHROPIC_API_KEY', '')
param openaiApiKey = readEnvironmentVariable('OPENAI_API_KEY', '')
param geminiApiKey = readEnvironmentVariable('GEMINI_API_KEY', '')
param deepseekApiKey = readEnvironmentVariable('DEEPSEEK_API_KEY', '')
param nvidiaNimApiKey = readEnvironmentVariable('NVIDIA_NIM_API_KEY', '')
param mistralApiKey = readEnvironmentVariable('MISTRAL_API_KEY', '')
param xaiApiKey = readEnvironmentVariable('XAI_API_KEY', '')
param groqApiKey = readEnvironmentVariable('GROQ_API_KEY', '')
param keyEncryptionKey = readEnvironmentVariable('PLAYGROUND_KEY_ENCRYPTION_KEY', '')
