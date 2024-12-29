import json
import logging

from langgraph.graph import StateGraph, START
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from agentorg.workers.tools.custom.apply_utils import JobApplicationActions, JobApplicationSchema
from agentorg.workers.worker import BaseWorker, register_worker
from agentorg.workers.prompts import database_action_prompt_formatted
from agentorg.workers.tools.RAG.utils import ToolGenerator
from agentorg.utils.utils import chunk_string
from agentorg.utils.graph_state import MessageState
from agentorg.utils.model_config import MODEL

logger = logging.getLogger(__name__)

json_parser = PydanticOutputParser(pydantic_object=JobApplicationSchema)

@register_worker
class JobApplicationWorker(BaseWorker):

    description = "Help the user create, delete, or check the status of a job application in the portal."

    def __init__(self):
        self.llm = ChatOpenAI(model=MODEL["model_type_or_path"], timeout=30000)
        self.actions = {
            "CreateApplication": "Create a new job application in the portal, requires - UserId, JobId, LinkedInUrl", 
            "DeleteApplication": "Delete a specified job application in the portal, requires - UserId, JobId", 
            "CheckApplicationStatus": "Check application status of a job in the portal, requires - UserId, JobId",
            "Others": "Other actions not mentioned above"
        }
        self.DBActions = JobApplicationActions()
        self.action_graph = self._create_action_graph()

    def create_application(self, state: MessageState):
        return self.DBActions.create_application(state, self.current_application_params)
    
    def delete_application(self, state: MessageState):
        return self.DBActions.delete_application(state, self.current_application_params)
    
    def check_application_status(self, state: MessageState):
        return self.DBActions.check_application_status(state, self.current_application_params)
    
    def perform_other_action(self, state: MessageState):
        return self.DBActions.other_actions(state)

    def verify_action(self, msg_state: MessageState):
        user_intent = msg_state["orchestrator_message"].attribute.get("task", "")
        # print(msg_state)
        actions_info = "\n".join([f"{name}: {description}" for name, description in self.actions.items()])
        actions_name = ", ".join(self.actions.keys())
        prompt_example = {
            "action_name": "CreateApplication",
            "job_id": "1234",
            "user_name": "John Doe",
            "linkedin_url": "https://www.linkedin.com/in/johndoe",
        }

        format_example_str = json.dumps(prompt_example, indent=2)
        prompt = PromptTemplate.from_template(database_action_prompt_formatted)
        input_prompt = prompt.invoke({"user_intent": user_intent, "actions_info": actions_info, "actions_name": actions_name, "example": format_example_str})
        chunked_prompt = chunk_string(input_prompt.text, tokenizer=MODEL["tokenizer"], max_length=MODEL["context"])
        logger.info(f"Chunked prompt for deciding choosing application action: {chunked_prompt}")
        # print(chunked_prompt)
        final_chain = self.llm | json_parser

        try:
            answer = final_chain.invoke(chunked_prompt)
            self.current_application_params = answer
            for action_name in self.actions.keys():
                if action_name in str(answer):
                    logger.info(f"Chosen action in the job application worker: {action_name}")
                    return action_name
            logger.info(f"Base action chosen in the job application worker: Others")
            return "Others"
        except Exception as e:
            logger.error(f"Error occurred while choosing action in the job application worker: {e}")
            return "Others"

        
    def _create_action_graph(self):
        workflow = StateGraph(MessageState)
        workflow.add_node("CreateApplication", self.create_application)
        workflow.add_node("DeleteApplication", self.delete_application)
        workflow.add_node("CheckApplicationStatus", self.check_application_status)
        workflow.add_node("Others", self.perform_other_action)
        workflow.add_node("tool_generator", ToolGenerator.context_generate)
        workflow.add_conditional_edges(START, self.verify_action)
        workflow.add_edge("CreateApplication", "tool_generator")
        workflow.add_edge("DeleteApplication", "tool_generator")
        workflow.add_edge("CheckApplicationStatus", "tool_generator")
        workflow.add_edge("Others", "tool_generator")
        return workflow

    def execute(self, msg_state: MessageState):
        graph = self.action_graph.compile()
        result = graph.invoke(msg_state)
        return result
