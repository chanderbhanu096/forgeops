# LLM providers and per-mission model selection

ForgeOps supports selecting an LLM provider and model separately for every mission.
API keys are configured on the server and are never sent to the browser or stored in
mission records.

## Supported providers

| Provider | Required configuration |
|---|---|
| Demo simulator | Nothing |
| OpenAI | `OPENAI_API_KEY` |
| Anthropic / Claude | `ANTHROPIC_API_KEY` |
| Groq | `GROQ_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| Ollama | `OLLAMA_BASE_URL` |
| Custom OpenAI-compatible API | `CUSTOM_OPENAI_BASE_URL` and optional `CUSTOM_OPENAI_API_KEY` |

Only configured providers are enabled in the New Mission form. Unconfigured providers
remain visible but disabled, together with the environment variable needed to enable them.

## Local setup

Copy the example file:

```bash
cp .env.example .env
```

Add one or more provider keys. For example, Groq:

```dotenv
GROQ_API_KEY=gsk_...
DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=openai/gpt-oss-20b
```

Or Anthropic:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_LLM_MODEL=claude-sonnet-4-20250514
```

Start or restart the stack:

```bash
docker compose up -d --build
```

## Model suggestions versus model IDs

The provider dropdown is fixed to the adapters supported by ForgeOps. The model field is
editable. Suggestions come from comma-separated environment variables such as
`GROQ_MODELS` or `OPENAI_MODELS`, but a user may type any valid chat-compatible model ID
accepted by the selected provider.

Example:

```dotenv
GROQ_MODELS=openai/gpt-oss-20b,openai/gpt-oss-120b
OPENAI_MODELS=gpt-5-mini,gpt-4.1-mini,gpt-4o-mini
OPENROUTER_MODELS=openrouter/auto,anthropic/claude-sonnet-4
```

Provider model catalogs change over time. Update these suggestion variables without
changing application code.

## Ollama

ForgeOps uses Ollama's OpenAI-compatible endpoint. When ForgeOps runs in Docker Desktop:

```dotenv
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
OLLAMA_MODELS=llama3.2,qwen2.5-coder
```

The requested model must already be pulled into Ollama.

## Custom OpenAI-compatible service

Any service implementing the OpenAI chat-completions contract can be added:

```dotenv
CUSTOM_OPENAI_NAME=Company LLM Gateway
CUSTOM_OPENAI_BASE_URL=https://llm.example.com/v1
CUSTOM_OPENAI_API_KEY=...
CUSTOM_OPENAI_MODELS=company-fast,company-reasoning
```

The API key may be left empty for trusted local services that do not require
authentication.

## GitHub Actions and Azure Container Apps

Add provider keys under **Repository settings → Secrets and variables → Actions → Secrets**:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
GROQ_API_KEY
OPENROUTER_API_KEY
CUSTOM_OPENAI_API_KEY
```

Only add the secrets you use. The Azure workflow stores them as Container App secrets and
maps them into the API container. Suggested defaults and endpoint overrides can be added as
repository variables:

```text
DEFAULT_LLM_PROVIDER
DEFAULT_LLM_MODEL
GROQ_BASE_URL
OPENROUTER_BASE_URL
OLLAMA_BASE_URL
CUSTOM_OPENAI_NAME
CUSTOM_OPENAI_BASE_URL
```

After deployment, check the catalog endpoint:

```bash
curl https://YOUR-WEB-DOMAIN/api/backend/api/v1/models
```

The response reports provider availability and model suggestions, but never secret values.

## Security model

- Provider keys stay in `.env`, a secret manager, or cloud deployment secrets.
- Keys are not accepted in mission requests.
- Keys are never returned by `/api/v1/models`.
- Each mission stores only `llm_provider` and `llm_model`.
- Mission execution uses an async context-local selection, so concurrent missions can use
  different providers safely.
