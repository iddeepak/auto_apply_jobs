# Login Credentials for LinkedIn (Optional)
username = "test"       # Enter your username in the quotes
password = "test"           # Enter your password in the quotes
keywords = "Java Developer"
location = "United States"

## Artificial Intelligence (Beta Not-Recommended)
# Use AI
use_AI = True                          # True or False, Note: True or False are case-sensitive

# Your Local LLM url or other AI api url and port
# llm_api_url = "https://api.openai.com/v1/"       # Examples: "https://api.openai.com/v1/", "http://127.0.0.1:1234/v1/", "http://localhost:1234/v1/"

# Your Local LLM API key or other AI API key 
# llm_api_key = ""              # Enter your API key in the quotes, make sure it's valid, if not will result in error.

# Your local LLM model name or other AI model name
# llm_model = "gpt-4o-mini"          # Examples: "gpt-3.5-turbo", "gpt-4o", "llama-3.2-3b-instruct"

# llm_spec = "openai"                # Examples: "openai", "openai-like", "openai-like-github", "openai-like-mistral"

# Do you want to stream AI output?
stream_output = True                    # Examples: True or False. (False is recommended for performance, True is recommended for user experience!)


llm_api_url = "http://localhost:11434/v1/"
llm_api_key = "ollama"
llm_model = "tinyllama:latest"
llm_spec = "openai-like"