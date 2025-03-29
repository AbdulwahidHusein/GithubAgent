#!/usr/bin/env python3

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import os
import logging
import traceback
import json
import time

from pydantic import BaseModel, Field, TypeAdapter
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage
from datetime import datetime
import github_utils
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("github_agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("github_agent")

load_dotenv()

os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))


# ==================== Dependency Models ====================

@dataclass
class GitHubDependencies:
    """Dependencies for the GitHub repository agent."""
    token: str
    repo_name: str  # Format: "username/repo"


# ==================== Output Models ====================

class CodeSearchResult(BaseModel):
    """Model for code search results."""
    matches: List[Dict[str, Any]] = Field(..., description="List of code matches found")
    summary: str = Field(..., description="A concise summary of the search results")


class IssueAnalysisResult(BaseModel):
    """Model for issue analysis results."""
    issues: List[Dict[str, Any]] = Field(..., description="List of relevant issues")
    summary: str = Field(..., description="Analysis summary of the issues")


class CommitAnalysisResult(BaseModel):
    """Model for commit analysis results."""
    commits: List[Dict[str, Any]] = Field(..., description="List of relevant commits")
    summary: str = Field(..., description="Analysis summary of the commits")


class RepositoryAnalysisResult(BaseModel):
    """Model for general repository analysis results."""
    answer: str = Field(..., description="Clear and concise answer to the user's question")
    sources: List[str] = Field(default_factory=list, description="Sources or references supporting the answer")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level in the answer provided")


# ==================== Agent Definition ====================

# Define the agent with the result type and a string-based system prompt
github_agent = Agent(
    'openai:gpt-4o',  # Using OpenAI GPT-4o by default
    deps_type=GitHubDependencies,
    result_type=RepositoryAnalysisResult,
    system_prompt="""
    You are a GitHub Repository Analysis Assistant specialized in analyzing GitHub repositories.

    Users got tired of navigating their github codebase to find the information they need here is where you came in!

    You help answer users questions and if you need additional information to answer use appropirate tools 
    GitHub repositories.
    
    As an assistant:
    1. Always be specific, accurate, and helpful
    2. When uncertain, acknowledge limitations rather than making assumptions
    3. Refer to specific files, issues, or commits when possible
    4. Structure your responses to be easy to read and understand
    5. Focus on providing factual information based on the repository data

    be intellegent in your tool usage do evrything you can to find relevant information for the users query
    use tools only when necessary if the user asks something generic that you can asnwer on your own dont use a tool.
    """
)


# ==================== System Prompts ====================

@github_agent.system_prompt
def repository_context(ctx: RunContext[GitHubDependencies]) -> str:
    """Adds repository-specific context to the system prompt."""
    repo_name = ctx.deps.repo_name
    username, repo = repo_name.split("/")
    
    try:
        repos = github_utils.list_user_repositories(token=ctx.deps.token, username=username)
        repo_info = next((r for r in repos if r["full_name"] == repo_name), None)
        
        if repo_info:
            return f"""
            if you need addtional information from the repository to answer the question here is the repository info
             
            Repository name: {repo_name}
            Repository details:
            - Description: {repo_info['description'] or 'No description provided'}
            - Primary language: {repo_info['language'] or 'Not specified'}
            - Stars: {repo_info['stargazers_count']}
            - Forks: {repo_info['forks_count']}
            - Last updated: {repo_info['updated_at']}
            


            today's date is {datetime.now().strftime("%Y-%m-%d")} and the time now is {datetime.now().strftime("%H:%M:%S")}
            """
        return f"You are currently answering questions about the repository: {repo_name}"
    except Exception as e:
        return f"You are currently answering questions about the repository: {repo_name}"


# ==================== Agent Tools ====================

@github_agent.tool
def get_repo_details(ctx: RunContext[GitHubDependencies]) -> Dict[str, Any]:
    """
    Get detailed information about the repository.
    
    Returns basic repository information like description, language, stars, etc.
    """
    repo_name = ctx.deps.repo_name
    logger.info(f"Tool called: get_repo_details for repository {repo_name}")
    
    try:
        username, repo = repo_name.split("/")
        
        repos = github_utils.list_user_repositories(token=ctx.deps.token, username=username)
        repo_info = next((r for r in repos if r["full_name"] == repo_name), None)
        
        if not repo_info:
            logger.error(f"Repository {repo_name} not found")
            raise ValueError(f"Repository {repo_name} not found")
        
        logger.info(f"Successfully retrieved details for repository {repo_name}")
        return repo_info
    except Exception as e:
        logger.error(f"Error in get_repo_details: {str(e)}")
        logger.debug(traceback.format_exc())
        raise


@github_agent.tool
def search_code(
    ctx: RunContext[GitHubDependencies], 
    query: str = Field(..., description="Search term to find in the repository code")
) -> CodeSearchResult:
    """
    Search for code within the repository.
    
    This tool searches through the repository's code for specific terms or patterns.
    """
    repo_name = ctx.deps.repo_name
    logger.info(f"Tool called: search_code in {repo_name} with query: '{query}'")
    
    try:
        start_time = time.time()
        results = github_utils.search_code_in_repository(
            repo_name=repo_name,
            query=query,
            token=ctx.deps.token
        )
        
        # Create a summary based on the results
        if len(results) == 0:
            summary = f"No code matches found for '{query}' in the repository."
        else:
            summary = f"Found {len(results)} code matches for '{query}' in the repository."
        
        logger.info(f"search_code completed in {time.time() - start_time:.2f}s. {summary}")
        return CodeSearchResult(matches=results, summary=summary)
    except Exception as e:
        logger.error(f"Error in search_code: {str(e)}")
        logger.debug(traceback.format_exc())
        raise


@github_agent.tool
def list_issues(
    ctx: RunContext[GitHubDependencies],
    state: str = Field("all", description="Filter issues by state (open, closed, all)")
) -> List[Dict[str, Any]]:
    """
    List issues in the repository.
    
    This tool retrieves issues from the repository with optional filtering by state.
    """
    repo_name = ctx.deps.repo_name
    logger.info(f"Tool called: list_issues for {repo_name} with state: {state}")
    
    try:
        start_time = time.time()
        issues = github_utils.list_repository_issues(
            repo_name=repo_name,
            state=state,
            token=ctx.deps.token
        )
        
        logger.info(f"list_issues completed in {time.time() - start_time:.2f}s. Found {len(issues)} issues.")
        return issues
    except Exception as e:
        logger.error(f"Error in list_issues: {str(e)}")
        logger.debug(traceback.format_exc())
        raise


@github_agent.tool
def analyze_issues(
    ctx: RunContext[GitHubDependencies],
    query: str = Field(..., description="Query to analyze issues for"),
    state: str = Field("all", description="Filter issues by state (open, closed, all)")
) -> IssueAnalysisResult:
    """
    Analyze issues in the repository based on a query.
    
    This tool provides a deeper analysis of repository issues matching a specific query.
    """
    repo_name = ctx.deps.repo_name
    
    # Handle case where state is a FieldInfo object
    if state is not None and not isinstance(state, str):
        state = "all"
        
    logger.info(f"Tool called: analyze_issues for {repo_name} with query: '{query}', state: {state}")
    
    try:
        start_time = time.time()
        issues = github_utils.list_repository_issues(
            repo_name=repo_name,
            state=state,
            token=ctx.deps.token
        )
        
        # Filter issues that match the query (case-insensitive)
        query_lower = query.lower()
        matching_issues = [
            issue for issue in issues
            if query_lower in issue["title"].lower() or 
               any(query_lower in label.lower() for label in issue["labels"])
        ]
        
        # Create a summary based on the results
        if len(matching_issues) == 0:
            summary = f"No issues found matching '{query}' with state '{state}'."
        else:
            summary = f"Found {len(matching_issues)} issues matching '{query}' with state '{state}'."
        
        logger.info(f"analyze_issues completed in {time.time() - start_time:.2f}s. {summary}")
        return IssueAnalysisResult(issues=matching_issues, summary=summary)
    except Exception as e:
        logger.error(f"Error in analyze_issues: {str(e)}")
        logger.debug(traceback.format_exc())
        raise


@github_agent.tool
def list_commits(
    ctx: RunContext[GitHubDependencies],
    path: Optional[str] = Field(None, description="Optional path to filter commits by file or directory")
) -> List[Dict[str, Any]]:
    """
    List commits in the repository.
    
    This tool retrieves the commit history of the repository, optionally filtered by file path.
    """
    repo_name = ctx.deps.repo_name
    
    # Handle case where path is a FieldInfo object
    if path is not None and not isinstance(path, str):
        path = None
        
    path_str = f" with path: {path}" if path else ""
    logger.info(f"Tool called: list_commits for {repo_name}{path_str}")
    
    try:
        start_time = time.time()
        commits = github_utils.list_repository_commits(
            repo_name=repo_name,
            path=path,
            token=ctx.deps.token
        )
        
        logger.info(f"list_commits completed in {time.time() - start_time:.2f}s. Found {len(commits)} commits.")
        return commits
    except Exception as e:
        logger.error(f"Error in list_commits: {str(e)} - path type: {type(path)}")
        logger.debug(traceback.format_exc())
        raise


@github_agent.tool
def analyze_commits(
    ctx: RunContext[GitHubDependencies],
    query: str = Field(..., description="Query to analyze commits for"),
    path: Optional[str] = Field(None, description="Optional path to filter commits by file or directory")
) -> CommitAnalysisResult:
    """
    Analyze commits in the repository based on a query.
    
    This tool provides a deeper analysis of repository commits matching a specific query.
    """
    repo_name = ctx.deps.repo_name
    
    # Handle case where path is a FieldInfo object instead of None
    if path is not None and not isinstance(path, str):
        path = None
        
    path_str = f", path: {path}" if path else ""
    logger.info(f"Tool called: analyze_commits for {repo_name} with query: '{query}'{path_str}")
    
    try:
        start_time = time.time()
        # Log parameter types for debugging
        logger.debug(f"Parameter types - path: {type(path)}, query: {type(query)}")
        
        commits = github_utils.list_repository_commits(
            repo_name=repo_name,
            path=path,
            token=ctx.deps.token
        )
        
        # Filter commits that match the query (case-insensitive)
        query_lower = query.lower()
        matching_commits = [
            commit for commit in commits
            if query_lower in commit["message"].lower()
        ]
        
        # Create a summary based on the results
        if len(matching_commits) == 0:
            summary = f"No commits found matching '{query}'" + (f" in path '{path}'" if path else "")
        else:
            summary = f"Found {len(matching_commits)} commits matching '{query}'" + (f" in path '{path}'" if path else "")
        
        logger.info(f"analyze_commits completed in {time.time() - start_time:.2f}s. {summary}")
        return CommitAnalysisResult(commits=matching_commits, summary=summary)
    except Exception as e:
        logger.error(f"Error in analyze_commits: {str(e)} - path type: {type(path)}")
        logger.debug(traceback.format_exc())
        raise


@github_agent.tool
def get_file_content(
    ctx: RunContext[GitHubDependencies],
    path: str = Field(..., description="Path to the file within the repository")
) -> Dict[str, Any]:
    """
    Get the content of a specific file in the repository.
    
    This tool retrieves the full content of a file at the specified path.
    """
    repo_name = ctx.deps.repo_name
    logger.info(f"Tool called: get_file_content for {repo_name} with path: {path}")
    
    try:
        start_time = time.time()
        content = github_utils.get_repository_content(
            repo_name=repo_name,
            path=path,
            token=ctx.deps.token
        )
        
        if not isinstance(content, dict) or 'type' not in content or content['type'] != 'file':
            logger.error(f"Path '{path}' does not point to a file")
            raise ValueError(f"Path '{path}' does not point to a file")
        
        logger.info(f"get_file_content completed in {time.time() - start_time:.2f}s. Successfully retrieved file content.")
        return content
    except Exception as e:
        logger.error(f"Error in get_file_content: {str(e)}")
        logger.debug(traceback.format_exc())
        raise


@github_agent.tool
def list_directory_contents(
    ctx: RunContext[GitHubDependencies],
    path: str = Field("", description="Path to the directory within the repository")
) -> List[Dict[str, Any]]:
    """
    List the contents of a directory in the repository.
    
    This tool retrieves the files and subdirectories within a specified directory path.
    """
    repo_name = ctx.deps.repo_name
    path_str = f" with path: {path}" if path else " at root directory"
    logger.info(f"Tool called: list_directory_contents for {repo_name}{path_str}")
    
    try:
        start_time = time.time()
        contents = github_utils.get_repository_content(
            repo_name=repo_name,
            path=path,
            token=ctx.deps.token
        )
        
        if not isinstance(contents, list):
            logger.error(f"Path '{path}' does not point to a directory")
            raise ValueError(f"Path '{path}' does not point to a directory")
        
        logger.info(f"list_directory_contents completed in {time.time() - start_time:.2f}s. Found {len(contents)} items.")
        return contents
    except Exception as e:
        logger.error(f"Error in list_directory_contents: {str(e)}")
        logger.debug(traceback.format_exc())
        raise


# ==================== Interface Functions ====================

async def analyze_repository(query: str, token: str, repo_name: str) -> RepositoryAnalysisResult:
    """
    Analyze a repository based on a user query.
    
    Args:
        query: The user's question about the repository
        token: GitHub personal access token
        repo_name: Repository name in format "username/repo"
    
    Returns:
        RepositoryAnalysisResult containing the answer and supporting information
    """
    logger.info(f"Starting async analysis for repository {repo_name}")
    logger.info(f"Query: '{query}'")
    
    try:
        # Create dependencies
        deps = GitHubDependencies(token=token, repo_name=repo_name)
        
        # Run the agent
        start_time = time.time()
        result = await github_agent.run(query, deps=deps)
        
        execution_time = time.time() - start_time
        logger.info(f"Completed async analysis in {execution_time:.2f}s")
        logger.info(f"Answer confidence: {result.data.confidence:.2f}")
        
        return result.data
    except Exception as e:
        logger.error(f"Error in analyze_repository: {str(e)}")
        logger.error(traceback.format_exc())
        raise


# Create a TypeAdapter for serializing/deserializing ModelMessages
ModelMessagesTypeAdapter = TypeAdapter(List[ModelMessage])

def analyze_repository_sync(query: str, token: str, repo_name: str, message_history: Optional[List[ModelMessage]] = None):
    """
    Synchronous version of analyze_repository for easier integration with Streamlit.
    
    Args:
        query: The user's question about the repository
        token: GitHub personal access token
        repo_name: Repository name in format "username/repo"
        message_history: Optional list of previous messages for conversation context
        
    Returns:
        RunResult object containing both the answer data and message history
    """
    logger.info(f"Starting sync analysis for repository {repo_name}")
    logger.info(f"Query: '{query}'")
    logger.info(f"Using message history: {bool(message_history)}")
    
    try:
        # Create dependencies
        deps = GitHubDependencies(token=token, repo_name=repo_name)
        
        # Run the agent
        start_time = time.time()
        
        # Use message history if provided
        if message_history:
            result = github_agent.run_sync(query, deps=deps, message_history=message_history)
        else:
            result = github_agent.run_sync(query, deps=deps)
        
        execution_time = time.time() - start_time
        logger.info(f"Completed sync analysis in {execution_time:.2f}s")
        logger.info(f"Answer confidence: {result.data.confidence:.2f}")
        
        # Log token usage - safely check if usage exists and has the expected structure
        try:
            # Check if usage exists and how to access it
            if hasattr(result, 'usage'):
                usage = result.usage
                # Check if usage is a function
                if callable(usage):
                    usage = usage()
                
                # Now log the metrics if they exist
                request_tokens = getattr(usage, 'request_tokens', None)
                response_tokens = getattr(usage, 'response_tokens', None)
                total_tokens = getattr(usage, 'total_tokens', None)
                
                logger.info(f"Token usage - Request: {request_tokens}, Response: {response_tokens}, Total: {total_tokens}")
            else:
                logger.info("No usage information available in the result")
        except Exception as usage_error:
            logger.warning(f"Could not extract token usage information: {str(usage_error)}")
        
        return result  # Return the full RunResult object, not just .data
    except Exception as e:
        logger.error(f"Error in analyze_repository_sync: {str(e)}")
        logger.error(traceback.format_exc())
        raise

# Function to save messages to JSON
def save_messages_to_json(messages: List[ModelMessage], filename: str) -> None:
    """
    Save message history to a JSON file for persistence.
    
    Args:
        messages: List of ModelMessage objects
        filename: Path to save the JSON file
    """
    try:
        from pydantic_core import to_jsonable_python
        
        # Convert messages to JSON-serializable Python objects
        serialized = to_jsonable_python(messages)
        
        # Write to file
        with open(filename, 'w') as f:
            json.dump(serialized, f)
            
        logger.info(f"Successfully saved {len(messages)} messages to {filename}")
    except Exception as e:
        logger.error(f"Error saving messages to JSON: {str(e)}")
        logger.debug(traceback.format_exc())

# Function to load messages from JSON
def load_messages_from_json(filename: str) -> List[ModelMessage]:
    """
    Load message history from a JSON file.
    
    Args:
        filename: Path to the JSON file
        
    Returns:
        List of ModelMessage objects
    """
    try:
        if not os.path.exists(filename):
            logger.warning(f"Message history file {filename} not found")
            return []
            
        # Read from file
        with open(filename, 'r') as f:
            serialized = json.load(f)
        
        # Deserialize using the TypeAdapter
        messages = ModelMessagesTypeAdapter.validate_python(serialized)
        
        logger.info(f"Successfully loaded {len(messages)} messages from {filename}")
        return messages
    except Exception as e:
        logger.error(f"Error loading messages from JSON: {str(e)}")
        logger.debug(traceback.format_exc())
        return []
