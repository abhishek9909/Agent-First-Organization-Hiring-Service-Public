import json
import logging
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agentorg.utils.model_config import MODEL
from agentorg.workers.prompts import retrieve_contextualize_q_prompt_formatted
from agentorg.utils.graph_state import MessageState
from enum import Enum
from pydantic import BaseModel, Field
import requests
import re
from typing import Optional
from urllib.parse import urlencode, urljoin

logger = logging.getLogger(__name__)

class ExperienceLevel(str, Enum):
    experienced = "Experienced Professionals"
    students_and_graduates = "Students and graduates"

class JobSearchQuery(BaseModel):
    role: str = Field(..., description = "The role or position the user is looking for")
    location: Optional[str] = Field(None, description = "The location where the user is looking for a job")
    experience: Optional[ExperienceLevel] = Field(None, description = "The experience level the user is looking for - 'experienced professionals' or 'students and graduates'")
    skills: Optional[str] = Field(None, description = "The skills that the user possesses")

json_parser = PydanticOutputParser(pydantic_object=JobSearchQuery)

class JobSearchEngine():
    def __init__(self):
        self.llm = ChatOpenAI(model=MODEL["model_type_or_path"], timeout=30000)

    def search_query(self, query: JobSearchQuery):
        base_url = "https://gcsservices.careers.microsoft.com/search/api/v1/search"
        converted_params = {
            "q": f"{query.role} {query.skills}",
            "lc": query.location,
            "exp": query.experience.value if query.experience else None,
            "l": "en_us",
            "pg": 1,
            "pgSz": 5,
            "o": "Relevance",
            "flt": True
        }
        ## remove None values
        converted_params = {k: v for k, v in converted_params.items() if v is not None}
        encoded_params = urlencode(converted_params)
        ## make the request
        request_url = urljoin(base_url, f"?{encoded_params}")
        response = requests.get(request_url)
        # print(response)
        if response.status_code == 200:
            return response.json()
        
        return None

    def clean_description(self, description):
        ## remove all HTML tags using regex
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', description)
        return cleantext


    def process_search_results(self, search_results):
        processed_results = []
        for job in search_results["operationResult"]["result"]["jobs"]:
            job_title = job["title"]
            job_location = str(job["locations"])
            job_description = self.clean_description(job["properties"]["description"])[0:100]
            job_id = job["jobId"]
            processed_results.append({
                "title": job_title,
                "location": job_location,
                "description": job_description,
                "id": job_id
            })
        return processed_results        

    def search(self, state: MessageState):
        contextualize_q_prompt = PromptTemplate.from_template(
            template = retrieve_contextualize_q_prompt_formatted,
            # input_variables = ["chat_history", "format"]
        )
        format_example = {
            "role": "Software Engineer",
            "location": "Redmond, WA",
            "skills": "Python, C++, Java"
        }
        ## convert the format example to a JSON string
        format_example_str = json.dumps(format_example, indent=2)
        ret_input_chain = contextualize_q_prompt | self.llm | json_parser
        ret_input = ret_input_chain.invoke({"chat_history": state["user_message"].history, "format": format_example_str})
        logger.info(f"Reformulated input for search engine: {ret_input}")
        search_results = self.search_query(ret_input)
        state["message_flow"] = search_results
        return state