import logging
from typing import Dict, List
from openai import AsyncOpenAI, OpenAIError
from datetime import datetime

from fastapi import HTTPException

from com.mhire.app.config.config import Config
from com.mhire.app.services.job_description.job_description_schema import ErrorResponse, JobDescriptionSection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobDescription:
    def __init__(self):
        self.config = Config()
        self.client = AsyncOpenAI(api_key=self.config.openai_api_key)
        self.model = self.config.openai_model
        
        if not self.config.openai_api_key:
            error = ErrorResponse(
                status_code=500, 
                detail="OpenAI API key not configured",
                error_type="ConfigurationError"
            )
            raise HTTPException(status_code=error.status_code, detail=error.dict())

    def _create_prompt(self, job_data: Dict) -> str:
        """Create a prompt for the OpenAI model"""
        prompt = "Create a professional job description with the following details. Format the response as ONE complete section using markdown formatting:\n\n"
        
        # Company Information
        prompt += "Company Information:\n"
        prompt += f"Company Name: {job_data['company_name']}\n"
        if job_data.get('company_details'):
            prompt += f"Company Details: {job_data['company_details']}\n"
        
        # Position Details
        prompt += "\nPosition Details:\n"
        prompt += f"Job Title: {job_data['job_title']}\n"
        prompt += f"Location: {job_data['job_location']}\n"
        prompt += f"Job Type: {job_data['job_type']}\n"
        prompt += f"Number of Vacancies: {job_data.get('vacancy', 1)}\n"
        
        if job_data.get('salary_range'):
            prompt += f"Salary Range: {job_data['salary_range']}\n"
        if job_data.get('work_hours'):
            prompt += f"Work Hours: {job_data['work_hours']}\n"
        if job_data.get('specialization'):
            prompt += f"Specialization: {job_data['specialization']}\n"
        
        # Requirements
        prompt += "\nRequirements:\n"
        if job_data.get('qualification'):
            prompt += f"Qualification: {job_data['qualification']}\n"
        if job_data.get('years_of_experience'):
            prompt += f"Experience Required: {job_data['years_of_experience']}\n"
        prompt += f"Skills & Requirements: {job_data['job_requirements']}\n"
        
        # Output Format Instructions
        prompt += "\nPlease create a SINGLE cohesive job description that includes:\n"
        prompt += "- Company overview and introduction\n"
        prompt += "- Position summary and importance\n"
        prompt += "- Key responsibilities and duties\n"
        prompt += "- Required qualifications and skills\n"
        prompt += "- Benefits and compensation\n"
        prompt += "- Application process\n\n"
        prompt += "Format the entire response as ONE section with markdown formatting for headers and lists.\n"
        prompt += "Important: DO NOT split the response into multiple sections with separate titles.\n"
        
        return prompt

    def _parse_sections(self, content: str) -> List[JobDescriptionSection]:
        """Parse the generated content into a single section"""
        return [JobDescriptionSection(
            title="Job Description",
            content=content.strip()
        )]

    async def generate_description(self, job_data: Dict) -> Dict:
        try:
            prompt = self._create_prompt(job_data)
            
            logger.info(f"Generating description for job: {job_data['job_title']}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional HR content writer. Create a clear, well-structured job description in a single cohesive section using markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            if not response.choices or not response.choices[0].message.content:
                error = ErrorResponse(
                    status_code=500,
                    detail="Failed to generate job description",
                    error_type="GenerationError"
                )
                raise HTTPException(status_code=error.status_code, detail=error.dict())
            
            description = response.choices[0].message.content.strip()
            sections = self._parse_sections(description)
            
            return {
                "status": "success",
                "message": "Job description generated successfully",
                "sections": sections
            }
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            error = ErrorResponse(
                status_code=500,
                detail=f"OpenAI API error: {str(e)}",
                error_type="APIError"
            )
            raise HTTPException(status_code=error.status_code, detail=error.dict())
            
        except Exception as e:
            logger.error(f"Error generating job description: {str(e)}")
            error = ErrorResponse(
                status_code=500,
                detail=f"Error generating job description: {str(e)}",
                error_type="UnexpectedError"
            )
            raise HTTPException(status_code=error.status_code, detail=error.dict())
