import logging
import sqlite3
import os
from typing import Optional
from pydantic import BaseModel, Field

from agentorg.utils.graph_state import MessageState, StatusEnum

DBNAME = 'job_application_db.sqlite'
logger = logging.getLogger(__name__)

class JobApplicationSchema(BaseModel):
    action_name: str = Field(..., description = "The name of the action the user wants to perform")
    job_id: Optional[str] = Field(None, description = "The job id the user is referring to")
    user_name: Optional[str] = Field(None, description = "The username of the user")
    linkedin_url: Optional[str] = Field(None, description = "The linkedin profile url of the user (required only when applying)")

class JobApplicationActions:
    def __init__(self):
        self.db_path = os.path.join(os.environ.get("DATA_DIR"), DBNAME)

    def other_actions(self, msg_state: MessageState):
        logger.info("More information probably required to perform this action OR Action is not supported by the bot.")
        msg_state["status"] = StatusEnum.INCOMPLETE
        msg_state["message_flow"] = "More information probably required to perform this action OR Action is not supported by the bot."
        ## return "More information probably required to perform this action OR Action is not supported by the bot."

    def create_application(self, msg_state: MessageState, current_application: JobApplicationSchema):
        print(current_application)
        try:
            try:
                job_id = current_application["job_id"]
                user_name = current_application["user_name"]
                linkedin_url = current_application["linkedin_url"]
            except:
                job_id = "222"
                user_name = "John Doe"
                linkedin_url = "https://www.linkedin.com/in/johndoe"
            # Add the application to the database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            ## check if existing application - jobId, user_name exists.
            c.execute(f"SELECT * FROM applications WHERE job_id = '{job_id}' AND user_name = '{user_name}'")
            print("here 1")
            if c.fetchone():
                msg_state["status"] = StatusEnum.COMPLETE
                msg_state["message_flow"] = "Application already exists for job_id: {job_id} for user: {user_name}"
                logger.info(f"Application already exists for job_id: {job_id} for user: {user_name}")
                print("here 2")
                # return "Application already exists for job_id: {job_id} for user: {user_name}"
            c.execute(f"INSERT INTO applications (job_id, user_name, linkedin_url, status) VALUES ('{job_id}', '{user_name}', '{linkedin_url}', 'Applied')")
            print("here 3")
            msg_state["status"] = StatusEnum.COMPLETE
            msg_state["message_flow"] = "Application for job_id: {job_id} created successfully for user: {user_name}"
            logger.info(f"Application for job_id: {job_id} created successfully for user: {user_name}")
        except:
            msg_state["message_flow"] = "Error occurred while creating the application, Try providing a jobId and userName"
            logger.error("Error occurred while creating the application")
            return "Error occurred while creating the application"

    def delete_application(self, msg_state: MessageState, current_application: JobApplicationSchema):
        print(current_application)
        try:
            try:
                job_id = current_application["job_id"]
                user_name = current_application["user_name"]
                # linkedin_url = current_application["linkedin_url"]
            except:
                job_id = "222"
                user_name = "John Doe"
                # linkedin_url = "https://www.linkedin.com/in/johndoe"
            # Delete the application from the database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(f"DELETE FROM applications WHERE job_id = '{job_id}' AND user_name = '{user_name}'")
            msg_state["status"] = StatusEnum.COMPLETE
            msg_state["message_flow"] = "Application for job_id: {job_id} deleted successfully for user: {user_name}"
            logger.info(f"Application for job_id: {job_id} deleted successfully for user: {user_name}")
        except:
            msg_state["message_flow"] = "Error occurred while deleting the application, Try providing a jobId and userName"
            logger.error("Error occurred while deleting the application")
            return "Error occurred while deleting the application"

    def check_application_status(self, msg_state: MessageState, current_application: JobApplicationSchema):
        print(current_application)
        try:
            try:
                job_id = current_application["job_id"]
                user_name = current_application["user_name"]
                #linkedin_url = current_application["linkedin_url"]
            except:
                job_id = "222"
                user_name = "John Doe"
                #linkedin_url = "https://www.linkedin.com/in/johndoe"
            # Check the status of the application in the database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(f"SELECT status FROM applications WHERE job_id = '{job_id}' AND user_name = '{user_name}'")
            status = c.fetchone()
            if status:
                msg_state["status"] = StatusEnum.COMPLETE
                msg_state["message_flow"] = f"Application for job_id: {job_id} is {status[0]} for user: {user_name}"
                logger.info(f"Application for job_id: {job_id} is {status[0]} for user: {user_name}")
            else:
                msg_state["status"] = StatusEnum.COMPLETE
                msg_state["message_flow"] = f"No application found for job_id: {job_id} for user: {user_name}"
                logger.info(f"No application found for job_id: {job_id} for user: {user_name}")
        except:
            msg_state["message_flow"] = "Error occurred while checking the application status, Try providing a jobId and userName"
            logger.error("Error occurred while checking the application status")
            return "Error occurred while checking the application status"