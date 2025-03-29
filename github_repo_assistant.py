#!/usr/bin/env python3

import streamlit as st
import os
from github_utils import get_github_client, list_user_repositories
from agent import analyze_repository_sync, save_messages_to_json, load_messages_from_json
import time
from datetime import datetime
import json

from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

# Set page configuration
st.set_page_config(
    page_title="GitHub Repository Chat",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better chat display
st.markdown("""

</style>
""", unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if "github_token" not in st.session_state:
    st.session_state.github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
if "username" not in st.session_state:
    st.session_state.username = ""
if "repositories" not in st.session_state:
    st.session_state.repositories = []
if "selected_repository" not in st.session_state:
    st.session_state.selected_repository = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False
if "pydantic_messages" not in st.session_state:
    st.session_state.pydantic_messages = {}  # Repository-specific message history
if "token_usage" not in st.session_state:
    st.session_state.token_usage = {
        "request_tokens": 0,
        "response_tokens": 0,
        "total_tokens": 0,
        "requests": 0
    }

# Message history directory
HISTORY_DIR = "chat_history"
os.makedirs(HISTORY_DIR, exist_ok=True)

def get_history_filename(repo_name):
    """Generate a filename for the repository chat history"""
    if not repo_name:
        return None
    # Replace slashes with underscores for filename safety
    safe_name = repo_name.replace("/", "_")
    return os.path.join(HISTORY_DIR, f"{safe_name}_history.json")

def load_repositories():
    """Load repositories for the given username and token"""
    try:
        repos = list_user_repositories(
            token=st.session_state.github_token, 
            username=st.session_state.username if st.session_state.username else None
        )
        st.session_state.repositories = repos
        return True
    except Exception as e:
        st.error(f"Error loading repositories: {str(e)}")
        return False

def on_repository_select():
    """Handle repository selection"""
    # Reset Streamlit chat history when repository changes
    st.session_state.chat_history = []
    st.session_state.conversation_started = False
    
    # Load previous PydanticAI message history for this repository if available
    load_pydantic_message_history(st.session_state.selected_repository)

def load_pydantic_message_history(repo_name):
    """Load PydanticAI message history for a specific repository"""
    if not repo_name:
        return
        
    history_file = get_history_filename(repo_name)
    if history_file and repo_name not in st.session_state.pydantic_messages:
        # Load messages from disk if they exist
        st.session_state.pydantic_messages[repo_name] = load_messages_from_json(history_file)

def add_message_with_timestamp(role, content):
    """Add a message to chat history with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.chat_history.append({
        "role": role, 
        "content": content,
        "timestamp": timestamp
    })

def format_sources(sources):
    """Format source links in a more readable way"""
    if not sources or len(sources) == 0:
        return ""
        
    formatted_sources = "\n\n**Sources:**\n"
    for i, source in enumerate(sources, 1):
        formatted_sources += f"{i}. {source}\n"
    return formatted_sources

def process_query(query):
    """Process a user query using the PydanticAI agent"""
    if not st.session_state.selected_repository:
        st.error("Please select a repository first")
        return
    
    # Add user message to chat history with timestamp
    add_message_with_timestamp("user", query)
    
    # Set conversation started flag
    if not st.session_state.conversation_started:
        st.session_state.conversation_started = True
    
    repo_name = st.session_state.selected_repository
    
    # Use a container for displaying the assistant's response
    with st.chat_message("assistant"):
        # Show loading indicator instead of typing animation
        with st.spinner("Thinking..."):
            try:
                # Get existing message history for this repository
                message_history = st.session_state.pydantic_messages.get(repo_name, [])
                
                # Process the query with the agent, passing message history
                agent_result = analyze_repository_sync(
                    query=query,
                    token=st.session_state.github_token,
                    repo_name=repo_name,
                    message_history=message_history if message_history else None
                )
                
                # Get the result data
                result = agent_result.data
                
                # Update token usage statistics
                if hasattr(agent_result, 'usage'):
                    try:
                        usage = agent_result.usage
                        # Check if usage is a function
                        if callable(usage):
                            usage = usage()
                            
                        # Increment request count
                        st.session_state.token_usage["requests"] += 1
                        
                        # Update request tokens
                        request_tokens = getattr(usage, 'request_tokens', None)
                        if request_tokens:
                            st.session_state.token_usage["request_tokens"] += request_tokens
                        
                        # Update response tokens
                        response_tokens = getattr(usage, 'response_tokens', None)
                        if response_tokens:
                            st.session_state.token_usage["response_tokens"] += response_tokens
                        
                        # Update total tokens
                        total_tokens = getattr(usage, 'total_tokens', None)
                        if total_tokens:
                            st.session_state.token_usage["total_tokens"] += total_tokens
                    except Exception as usage_error:
                        st.error(f"Error processing usage data: {str(usage_error)}")
                        # Continue with the flow, as this is not critical
                
                # Format the response with sources if available
                response_text = result.answer
                sources_text = format_sources(result.sources)
                
                # Add confidence but only if it's high enough to be meaningful
                if result.confidence > 0.7:
                    confidence_text = f"\n\n*Confidence: {result.confidence:.2f}*"
                else:
                    confidence_text = ""
                
                # Combine all parts
                full_response = f"{response_text}{sources_text}{confidence_text}"
                
                # Update the PydanticAI message history for this repository
                st.session_state.pydantic_messages[repo_name] = agent_result.all_messages()
                
                # Save updated message history to disk
                history_file = get_history_filename(repo_name)
                if history_file:
                    save_messages_to_json(st.session_state.pydantic_messages[repo_name], history_file)
                
            except Exception as e:
                # Handle errors
                error_message = f"Error: {str(e)}"
                st.error(error_message)
                full_response = f"I encountered an error while processing your query: {str(e)}"
        
        # Display the response
        st.markdown(full_response)
        
        # Show timestamp for the assistant message
        st.markdown("<div class='timestamp assistant-timestamp'>Just now</div>", unsafe_allow_html=True)
    
    # Add assistant message to chat history
    add_message_with_timestamp("assistant", full_response)
    
    # Force a rerun to update the UI immediately
    st.rerun()

# Main app interface - simplified title
st.title("GitHub Repository Chat")

# Sidebar for configuration
with st.sidebar:
    st.header("Settings")
    
    # GitHub token input
    token_input = st.text_input(
        "GitHub Personal Access Token",
        value=st.session_state.github_token,
        type="password",
        help="Enter your GitHub personal access token"
    )
    
    if token_input != st.session_state.github_token:
        st.session_state.github_token = token_input
    
    # Username input
    username_input = st.text_input(
        "GitHub Username (optional)",
        value=st.session_state.username,
        help="Enter a GitHub username to view their repositories, or leave blank for your own"
    )
    
    if username_input != st.session_state.username:
        st.session_state.username = username_input
    
    # Load repositories button
    if st.button("Load Repositories", type="primary"):
        with st.spinner("Loading repositories..."):
            success = load_repositories()
            if success:
                st.success(f"Loaded {len(st.session_state.repositories)} repositories")

    # Clear chat history option
    if st.session_state.chat_history and st.button("Clear Chat"):
        st.session_state.chat_history = []
        st.session_state.conversation_started = False
        
        # Also clear the PydanticAI message history for the current repository
        if st.session_state.selected_repository in st.session_state.pydantic_messages:
            st.session_state.pydantic_messages[st.session_state.selected_repository] = []
            
            # Remove the history file if it exists
            history_file = get_history_filename(st.session_state.selected_repository)
            if history_file and os.path.exists(history_file):
                try:
                    os.remove(history_file)
                except Exception as e:
                    st.error(f"Error removing history file: {str(e)}")
        
        st.rerun()
        
    # Simple model info
    st.caption("Using OpenAI GPT-4o")
    
    # Token usage statistics
    st.markdown("---")
    st.subheader("📊 Token Usage Statistics")
    
    # Calculate costs (accurate GPT-4o pricing)
    input_cost = st.session_state.token_usage["request_tokens"] * 0.0000025  # $2.50 per 1M tokens
    output_cost = st.session_state.token_usage["response_tokens"] * 0.00001  # $10.00 per 1M tokens
    total_cost = input_cost + output_cost
    
    # Format for better display
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Requests", st.session_state.token_usage["requests"])
        st.metric("Input Tokens", f"{st.session_state.token_usage['request_tokens']:,}")
    
    with col2:
        st.metric("Output Tokens", f"{st.session_state.token_usage['response_tokens']:,}")
        st.metric("Total Tokens", f"{st.session_state.token_usage['total_tokens']:,}")
    
    # Add usage efficiency metrics
    if st.session_state.token_usage["requests"] > 0:
        avg_tokens_per_request = int(st.session_state.token_usage["total_tokens"] / st.session_state.token_usage["requests"])
        st.caption(f"Average tokens per request: {avg_tokens_per_request:,}")
    
    # Cost breakdown
    st.caption(f"Estimated cost: ${total_cost:.4f} (GPT-4o: $2.50/1M input, $10.00/1M output tokens)")
    if st.session_state.token_usage["total_tokens"] > 0:
        # Show cost breakdown
        input_pct = (input_cost / total_cost) * 100 if total_cost > 0 else 0
        output_pct = (output_cost / total_cost) * 100 if total_cost > 0 else 0
        st.caption(f"Input cost: ${input_cost:.4f} ({input_pct:.1f}%) • Output cost: ${output_cost:.4f} ({output_pct:.1f}%)")
    
    # Usage warning if approaching limits
    token_limit = 128000  # GPT-4o context length
    if st.session_state.token_usage["total_tokens"] > token_limit * 0.7:
        st.warning(f"⚠️ High token usage: {st.session_state.token_usage['total_tokens']:,} tokens")
    
    # Reset usage stats button
    if st.button("Reset Usage Stats"):
        st.session_state.token_usage = {
            "request_tokens": 0,
            "response_tokens": 0,
            "total_tokens": 0,
            "requests": 0
        }
        st.rerun()

# Main content area
if not st.session_state.repositories:
    st.info("Enter your GitHub token in the sidebar and click 'Load Repositories' to start.")
else:
    # Create two columns with more space for chat
    col1, col2 = st.columns([1, 4])
    
    with col1:
        st.subheader("Repository")
        
        # Create a selection box with repository names
        repo_options = [repo["full_name"] for repo in st.session_state.repositories]
        selected_repo_name = st.selectbox(
            "Select a repository",
            options=repo_options,
            index=0 if st.session_state.selected_repository is None else repo_options.index(st.session_state.selected_repository),
            on_change=on_repository_select
        )
        
        # Update the selected repository in session state
        st.session_state.selected_repository = selected_repo_name
        
        # Find the selected repository details
        selected_repo = next(
            (repo for repo in st.session_state.repositories if repo["full_name"] == selected_repo_name),
            None
        )
        
        if selected_repo:
            # Display minimal repository details
            st.markdown("<div class='repo-info'>", unsafe_allow_html=True)
            if selected_repo['description']:
                st.write(f"**Description:** {selected_repo['description']}")
            st.write(f"**Language:** {selected_repo['language'] or 'Not specified'}")
            st.write(f"**Stars:** {selected_repo['stargazers_count']} • **Forks:** {selected_repo['forks_count']}")
            
            # Format date consistently
            updated_at = selected_repo['updated_at']
            if isinstance(updated_at, str) and 'T' in updated_at:
                formatted_date = updated_at.split('T')[0]
            elif hasattr(updated_at, 'strftime'):
                formatted_date = updated_at.strftime('%Y-%m-%d')
            else:
                formatted_date = str(updated_at)
            
            st.write(f"**Updated:** {formatted_date}")
            st.markdown(f"[View on GitHub]({selected_repo['html_url']})")
            
            # Show chat history status
            repo_name = st.session_state.selected_repository
            if repo_name in st.session_state.pydantic_messages and st.session_state.pydantic_messages[repo_name]:
                st.info(f"📝 Chat history is active ({len(st.session_state.pydantic_messages[repo_name])} messages)")
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        # Add the header for the chat area
        if st.session_state.selected_repository:
            st.subheader(f"Chat about {st.session_state.selected_repository}")
        else:
            st.subheader("Repository Chat")
            
        # Create a container for the entire chat area
        st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
        
        # Messages container with scrolling
        st.markdown("<div class='chat-messages'>", unsafe_allow_html=True)
        
        # Display welcome message if conversation hasn't started
        if not st.session_state.conversation_started and st.session_state.selected_repository:
            with st.chat_message("assistant"):
                st.markdown(f"""
                Hi there! I'm your GitHub Repository Assistant.
                Ask me any questions about the **{st.session_state.selected_repository}** repository.
                """)
                st.markdown("<div class='timestamp assistant-timestamp'>Just now</div>", unsafe_allow_html=True)
        
        # Display chat history using the standard chat API
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                timestamp_class = "user-timestamp" if message["role"] == "user" else "assistant-timestamp"
                st.markdown(f"<div class='timestamp {timestamp_class}'>{message.get('timestamp', '')}</div>", unsafe_allow_html=True)
        
        # Close the messages container
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Create a fixed input container at the bottom
        st.markdown("<div class='chat-input'>", unsafe_allow_html=True)
        if st.session_state.selected_repository:
            user_input = st.chat_input("Ask about the repository...")
            if user_input:
                process_query(user_input)
        else:
            st.info("Please select a repository to start chatting")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Close the chat area container
        st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.caption("GitHub Repository Chat • Built with Streamlit") 