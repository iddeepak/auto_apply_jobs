from config.secrets import *
from config.settings import showAiErrorAlerts
from config.questions import *

from modules.helpers import print_lg, critical_error_log, convert_to_json
from modules.prompts import *

from pyautogui import confirm
from openai import OpenAI
from openai.types.model import Model
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from typing import Iterator, Literal
import json, time, re
from copy import deepcopy


apiCheckInstructions = """

1. Make sure your AI API connection details like url, key, model names, etc are correct.
2. If you're using an local LLM, please check if the server is running.
3. Check if appropriate LLM and Embedding models are loaded and running.

Open `secret.py` in `/config` folder to configure your AI API connections.

ERROR:
"""

# Function to show an AI error alert
def ai_error_alert(message: str, stackTrace: str, title: str = "AI Connection Error") -> None:
    """
    Function to show an AI error alert and log it.
    """
    global showAiErrorAlerts
    if showAiErrorAlerts:
        if "Pause AI error alerts" == confirm(f"{message}{stackTrace}\n", title, ["Pause AI error alerts", "Okay Continue"]):
            showAiErrorAlerts = False
    critical_error_log(message, stackTrace)


# Function to check if an error occurred
def ai_check_error(response: ChatCompletion | ChatCompletionChunk) -> None:
    """
    Function to check if an error occurred.
    * Takes in `response` of type `ChatCompletion` or `ChatCompletionChunk`
    * Raises a `ValueError` if an error is found
    """
    if response.model_extra.get("error"):
        raise ValueError(
            f'Error occurred with API: "{response.model_extra.get("error")}"'
        )


# Function to create an OpenAI client
def ai_create_openai_client() -> OpenAI:
    """
    Function to create an OpenAI client.
    * Takes no arguments
    * Returns an `OpenAI` object
    """
    try:
        print_lg("Creating OpenAI client...")
        if not use_AI:
            raise ValueError("AI is not enabled! Please enable it by setting `use_AI = True` in `secrets.py` in `config` folder.")
        
        client = OpenAI(base_url=llm_api_url, api_key=llm_api_key)

        models = ai_get_models_list(client)
        if "error" in models:
            raise ValueError(models[1])
        if len(models) == 0:
            raise ValueError("No models are available!")
        if llm_model not in [model.id for model in models]:
            raise ValueError(f"Model `{llm_model}` is not found!")
        
        print_lg("---- SUCCESSFULLY CREATED OPENAI CLIENT! ----")
        print_lg(f"Using API URL: {llm_api_url}")
        print_lg(f"Using Model: {llm_model}")
        print_lg("Check './config/secrets.py' for more details.\n")
        print_lg("---------------------------------------------")

        return client
    except Exception as e:
        ai_error_alert(f"Error occurred while creating OpenAI client. {apiCheckInstructions}", e)


# Function to close an OpenAI client
def ai_close_openai_client(client: OpenAI) -> None:
    """
    Function to close an OpenAI client.
    * Takes in `client` of type `OpenAI`
    * Returns no value
    """
    try:
        if client:
            print_lg("Closing OpenAI client...")
            client.close()
    except Exception as e:
        ai_error_alert("Error occurred while closing OpenAI client.", e)



# Function to get list of models available in OpenAI API
def ai_get_models_list(client: OpenAI) -> list[ Model | str]:
    """
    Function to get list of models available in OpenAI API.
    * Takes in `client` of type `OpenAI`
    * Returns a `list` object
    """
    try:
        print_lg("Getting AI models list...")
        if not client: raise ValueError("Client is not available!")
        models = client.models.list()
        ai_check_error(models)
        print_lg("Available models:")
        print_lg(models.data, pretty=True)
        return models.data
    except Exception as e:
        critical_error_log("Error occurred while getting models list!", e)
        return ["error", e]

def model_supports_temperature(model_name: str) -> bool:
    """
    Checks if the specified model supports the temperature parameter.
    
    Args:
        model_name (str): The name of the AI model.
    
    Returns:
        bool: True if the model supports temperature adjustments, otherwise False.
    """
    return model_name in ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]

# Function to get chat completion from OpenAI API
def ai_completion(client: OpenAI, messages: list[dict], response_format: dict = None, temperature: float = 0, stream: bool = stream_output) -> dict | ValueError:
    """
    Function that completes a chat and prints and formats the results of the OpenAI API calls.
    * Takes in `client` of type `OpenAI`
    * Takes in `messages` of type `list[dict]`. Example: `[{"role": "user", "content": "Hello"}]`
    * Takes in `response_format` of type `dict` for JSON representation, default is `None`
    * Takes in `temperature` of type `float` for temperature, default is `0`
    * Takes in `stream` of type `bool` to indicate if it's a streaming call or not
    * Returns a `dict` object representing JSON response, will try to convert to JSON if `response_format` is given
    """
    if not client: raise ValueError("Client is not available!")

    params = {"model": llm_model, "messages": messages, "stream": stream}

    if model_supports_temperature(llm_model):
        params["temperature"] = temperature
    if response_format and llm_spec in ["openai", "openai-like"]:
        params["response_format"] = response_format

    completion = client.chat.completions.create(**params)

    result = ""
    
    # Log response
    if stream:
        print_lg("--STREAMING STARTED")
        for chunk in completion:
            ai_check_error(chunk)
            chunkMessage = chunk.choices[0].delta.content
            if chunkMessage != None:
                result += chunkMessage
            print_lg(chunkMessage, end="", flush=True)
        print_lg("\n--STREAMING COMPLETE")
    else:
        ai_check_error(completion)
        result = completion.choices[0].message.content
    
    if response_format:
        result = convert_to_json(result)
    
    print_lg("\nAI Answer to Question:\n")
    print_lg(result, pretty=response_format)
    return result


def ai_extract_skills(client: OpenAI, job_description: str, stream: bool = stream_output) -> dict | ValueError:
    """
    Function to extract skills from job description using OpenAI API.
    * Takes in `client` of type `OpenAI`
    * Takes in `job_description` of type `str`
    * Takes in `stream` of type `bool` to indicate if it's a streaming call
    * Returns a `dict` object representing JSON response
    """
    print_lg("-- EXTRACTING SKILLS FROM JOB DESCRIPTION")
    try:        
        prompt = extract_skills_prompt.format(job_description)

        messages = [{"role": "user", "content": prompt}]
        return ai_completion(client, messages, response_format=extract_skills_response_format, stream=stream)
    ##<
    except Exception as e:
        ai_error_alert(f"Error occurred while extracting skills from job description. {apiCheckInstructions}", e)


def ai_answer_question(
    client: OpenAI, 
    question: str, options: list[str] | None = None, question_type: Literal['text', 'textarea', 'single_select', 'multiple_select'] = 'text', 
    job_description: str = None, about_company: str = None, user_information_all: str = None,
    stream: bool = stream_output
) -> dict | ValueError:
    """
    Function to generate AI-based answers for questions in a form.
    
    Parameters:
    - `client`: OpenAI client instance.
    - `question`: The question being answered.
    - `options`: List of options (for `single_select` or `multiple_select` questions).
    - `question_type`: Type of question (text, textarea, single_select, multiple_select) It is restricted to one of four possible values.
    - `job_description`: Optional job description for context.
    - `about_company`: Optional company details for context.
    - `user_information_all`: information about you, AI cna use to answer question eg: Resume-like user information.
    - `stream`: Whether to use streaming AI completion.
    
    Returns:
    - `str`: The AI-generated answer.
    """

    print_lg("-- ANSWERING QUESTION using AI")
    try:
        prompt = ai_answer_prompt.format(user_information_all or "N/A", question)
         # Append optional details if provided
        if job_description and job_description != "Unknown":
            prompt += f"\nJob Description:\n{job_description}"
        if about_company and about_company != "Unknown":
            prompt += f"\nAbout the Company:\n{about_company}"

        messages = [{"role": "user", "content": prompt}]
        print_lg("Prompt we are passing to AI: ", prompt)
        response =  ai_completion(client, messages, stream=stream)
        # print_lg("Response from AI: ", response)
        return response
    except Exception as e:
        ai_error_alert(f"Error occurred while answering question. {apiCheckInstructions}", e)
##<



def _get_resume_text() -> str:
        with open("resume/resume.txt", "r", encoding="utf-8") as fh:
            return fh.read()

    # ───── core: decide YES / NO for each job ────────────────────────────────
def ai_check_job_relevance(
        client: OpenAI,
        *,
        job_title: str,
        company: str,
        location: str,
        work_style: str,
        experience_required: int | str,
        job_skills: dict | str,
        job_description: str,
        stream: bool = stream_output,
    ) -> bool:
        """
        Returns
        -------
        True   → the bot should apply
        False  → the bot should skip
        """

        try:
            if not client:
                raise ValueError("OpenAI client is not initialised")

            prompt = f"""You are a screening assistant deciding whether \
        the candidate’s résumé is a good match for the job.

        RESUME
        ------
        {_get_resume_text()}

        JOB POSTING
        -----------
        Title      : {job_title}
        Company    : {company}
        Location   : {location}  ({work_style})
        Experience : {experience_required}
        Key skills : {job_skills}

        Full description:
        {job_description}

        Reply with **one word only**:
        YES  – if I should apply  
        NO   – if I should skip
        """

            messages = [{"role": "user", "content": prompt}]
            reply = ai_completion(client, messages, stream=stream).strip().upper()
            return "YES" in reply.upper()

        except Exception as exc:
            ai_error_alert("Error while checking job relevance.", exc)
            # Fail-open so we don’t mistakenly skip good jobs
            return True
    # ─────────────────────────────────────────────────────────────────────────



def generate_custom_resume_data(
    client: OpenAI,
    *,
    base_user: dict,
    base_summary: str,
    base_experience: list,
    base_projects: list,
    base_skills: list,
    job_title: str,
    job_description: str,
    job_skills: list[str] | dict,
) -> tuple[dict, str, list, list, list]:
    """
    Returns (user_details, summary, experience, projects, skills)
    tailored to the current posting.

    If the AI call fails → returns originals untouched.
    """

    try:
        if isinstance(job_skills, dict):
            for v in job_skills.values():
                if isinstance(v, list):
                    base_skills.extend(v)

        prompt = f"""
    You are a senior résumé writer.  Rewrite the candidate's résumé so it is a better
    match for the following job.  *Do not fabricate experience*, but you may re-order,
    shorten, emphasise relevant skills, and add a short “Relevant Tech Stack” project
    containing keywords.

    Return **only** valid JSON with this schema:

    {{
    "summary": "... one powerful sentence ...",
    "skills": ["skill1", "skill2", "..."],
    "add_project": {{
        "name": "Relevant Tech Stack",
        "description": "Stack drawn from job posting",
        "technologies": "comma, separated, keywords"
    }}
    }}

    #############  CURRENT RESUME  #############
    SUMMARY:
    {base_summary}

    SKILLS:
    {', '.join(base_skills)}

    EXPERIENCE (truncated):
    {'; '.join([e['company'] for e in base_experience])}

    #############  JOB POSTING  #############
    TITLE  : {job_title}
    SKILLS : {', '.join(base_skills[:15])}
    DESC   :
    {job_description}
    """

        messages = [{"role": "user", "content": prompt}]
        raw_json = ai_completion(
            client,
                messages,
                stream=False,
                temperature=0.5,
            )

        data = json.loads(raw_json)

            # ---------- merge into copies so originals stay unchanged  ----
        new_summary   = data.get("summary", base_summary)
        new_skills    = data.get("skills", []) + [
            s for s in base_skills if s not in data.get("skills", [])
            ]
        new_projects  = deepcopy(base_projects)
        add_proj      = data.get("add_project")
        if add_proj:
            new_projects.append(add_proj)

            return base_user, new_summary, base_experience, new_projects, new_skills

    except Exception as err:
        ai_error_alert("Failed to generate custom résumé; using original.", err)
        return base_user, base_summary, base_experience, base_projects, base_skills

#>