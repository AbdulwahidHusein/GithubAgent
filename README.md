# GitHub Repository Assistant

A Streamlit application that allows you to browse GitHub repositories and interact with them through a chat interface.

## Features

- Load repositories from your GitHub account or any public user
- Browse repository details including description, language, stars, and more
- Select a repository to analyze (chat functionality coming soon)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/github-agent.git
   cd github-agent
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up your GitHub Personal Access Token:
   
   You'll need a GitHub Personal Access Token with the appropriate permissions to access repositories. You can create one at [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens).
   
   For this application, your token needs the following scopes:
   - `repo` (Full control of private repositories)
   - `read:org` (Read-only access to organization data)
   - `user` (Read-only access to user data)

   You can either:
   - Set it as an environment variable named `GITHUB_PERSONAL_ACCESS_TOKEN`
   - Enter it directly in the application interface

## Usage

1. Run the Streamlit application:
   ```
   streamlit run github_repo_assistant.py
   ```

2. Open your web browser and navigate to the URL shown in your terminal (typically http://localhost:8501)

3. Enter your GitHub Personal Access Token in the sidebar

4. Click "Load Repositories" to fetch repositories

5. Select a repository from the dropdown to view its details

## Current Limitations

- The chat interface is a placeholder and does not yet provide actual responses
- Only basic repository details are displayed
- Limited to 100 repositories per user (GitHub API pagination not implemented)

## Future Enhancements

- Fully functional chat interface using PydanticAI
- Repository content browser
- Issue and PR analysis
- Code search capabilities
- Visualization of repository statistics

## License

MIT 