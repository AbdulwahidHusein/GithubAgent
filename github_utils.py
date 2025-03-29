#!/usr/bin/env python3

import os
from github import Github, Auth
from typing import List, Optional, Dict, Any, Generator


def get_github_client(token: str = None) -> Github:
    """
    Create and return a GitHub client using the provided token or from environment variable.
    
    Args:
        token: GitHub personal access token. If None, will try to get from GITHUB_PERSONAL_ACCESS_TOKEN env var.
        
    Returns:
        Github client instance
        
    Raises:
        ValueError: If no token is provided and no environment variable is set.
    """
    if token is None:
        token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if token is None:
            raise ValueError("GitHub token not provided and GITHUB_PERSONAL_ACCESS_TOKEN environment variable not set")
    
    auth = Auth.Token(token)
    return Github(auth=auth)


def list_user_repositories(token: str = None, username: str = None) -> List[Dict[str, Any]]:
    """
    List all repositories for a user.
    
    Args:
        token: GitHub personal access token
        username: GitHub username. If None, gets authenticated user's repositories
        
    Returns:
        List of repository information dictionaries
    """
    g = get_github_client(token)
    
    try:
        if username:
            repos = g.get_user(username).get_repos()
        else:
            repos = g.get_user().get_repos()
        
        result = []
        for repo in repos:
            result.append({
                'name': repo.name,
                'full_name': repo.full_name,
                'description': repo.description,
                'html_url': repo.html_url,
                'ssh_url': repo.ssh_url,
                'clone_url': repo.clone_url,
                'language': repo.language,
                'private': repo.private,
                'created_at': repo.created_at,
                'updated_at': repo.updated_at,
                'size': repo.size,
                'stargazers_count': repo.stargazers_count,
                'forks_count': repo.forks_count
            })
        return result
    finally:
        g.close()


def search_repositories(query: str, token: str = None, user: str = None) -> List[Dict[str, Any]]:
    """
    Search for repositories with a given query.
    
    Args:
        query: Search query
        token: GitHub personal access token
        user: Limit search to user (username)
        
    Returns:
        List of repository information dictionaries
    """
    g = get_github_client(token)
    
    try:
        if user:
            query = f"{query} user:{user}"
        
        repos = g.search_repositories(query)
        
        result = []
        for repo in repos:
            result.append({
                'name': repo.name,
                'full_name': repo.full_name,
                'description': repo.description,
                'html_url': repo.html_url,
                'ssh_url': repo.ssh_url,
                'clone_url': repo.clone_url,
                'language': repo.language,
                'private': repo.private,
                'created_at': repo.created_at,
                'updated_at': repo.updated_at,
                'size': repo.size,
                'stargazers_count': repo.stargazers_count,
                'forks_count': repo.forks_count
            })
        return result
    finally:
        g.close()


def search_code_in_repository(repo_name: str, query: str, token: str = None) -> List[Dict[str, Any]]:
    """
    Search for code within a repository.
    
    Args:
        repo_name: Repository name in format "username/repo"
        query: Search query
        token: GitHub personal access token
        
    Returns:
        List of code search result dictionaries
    """
    g = get_github_client(token)
    
    try:
        query = f"{query} repo:{repo_name}"
        code_results = g.search_code(query)
        
        result = []
        for code in code_results:
            result.append({
                'name': code.name,
                'path': code.path,
                'url': code.html_url,
                'repository': code.repository.full_name,
                'score': code.score
            })
        return result
    finally:
        g.close()


def list_repository_issues(repo_name: str, state: str = "all", token: str = None) -> List[Dict[str, Any]]:
    """
    List issues in a repository.
    
    Args:
        repo_name: Repository name in format "username/repo"
        state: Filter issues by state ("open", "closed", "all")
        token: GitHub personal access token
        
    Returns:
        List of issue dictionaries
    """
    g = get_github_client(token)
    
    try:
        repo = g.get_repo(repo_name)
        issues = repo.get_issues(state=state)
        
        result = []
        for issue in issues:
            result.append({
                'number': issue.number,
                'title': issue.title,
                'state': issue.state,
                'html_url': issue.html_url,
                'created_at': issue.created_at,
                'updated_at': issue.updated_at,
                'user': issue.user.login,
                'labels': [label.name for label in issue.labels],
                'comments': issue.comments
            })
        return result
    finally:
        g.close()


def search_issues(query: str, token: str = None, user: str = None) -> List[Dict[str, Any]]:
    """
    Search for issues with a given query.
    
    Args:
        query: Search query
        token: GitHub personal access token
        user: Limit search to user's repositories (username)
        
    Returns:
        List of issue dictionaries
    """
    g = get_github_client(token)
    
    try:
        if user:
            query = f"{query} user:{user}"
        
        issues = g.search_issues(query)
        
        result = []
        for issue in issues:
            result.append({
                'number': issue.number,
                'title': issue.title,
                'state': issue.state,
                'html_url': issue.html_url,
                'created_at': issue.created_at,
                'updated_at': issue.updated_at,
                'user': issue.user.login,
                'repository': issue.repository.full_name,
                'labels': [label.name for label in issue.labels],
                'comments': issue.comments
            })
        return result
    finally:
        g.close()


def list_repository_commits(repo_name: str, path: str = None, token: str = None) -> List[Dict[str, Any]]:
    """
    List commits in a repository.
    
    Args:
        repo_name: Repository name in format "username/repo"
        path: Path to list commits for (optional)
        token: GitHub personal access token
        
    Returns:
        List of commit dictionaries
    """
    g = get_github_client(token)
    
    try:
        repo = g.get_repo(repo_name)
        # Only pass path parameter if it's not None
        if path is not None:
            commits = repo.get_commits(path=path)
        else:
            commits = repo.get_commits()
        
        result = []
        for commit in commits:
            result.append({
                'sha': commit.sha,
                'html_url': commit.html_url,
                'message': commit.commit.message,
                'author': commit.author.login if commit.author else None,
                'committer': commit.committer.login if commit.committer else None,
                'date': commit.commit.author.date,
                'stats': {
                    'additions': commit.stats.additions,
                    'deletions': commit.stats.deletions,
                    'total': commit.stats.total
                }
            })
        return result
    finally:
        g.close()


def search_commits(query: str, token: str = None, user: str = None) -> List[Dict[str, Any]]:
    """
    Search for commits with a given query.
    
    Args:
        query: Search query
        token: GitHub personal access token
        user: Limit search to user's repositories (username)
        
    Returns:
        List of commit dictionaries
    """
    g = get_github_client(token)
    
    try:
        if user:
            query = f"{query} author:{user}"
        
        commits = g.search_commits(query)
        
        result = []
        for commit in commits:
            result.append({
                'sha': commit.sha,
                'html_url': commit.html_url,
                'message': commit.commit.message,
                'author': commit.author.login if commit.author else None,
                'committer': commit.committer.login if commit.committer else None,
                'date': commit.commit.author.date,
                'repository': commit.repository.full_name
            })
        return result
    finally:
        g.close()


def get_repository_content(repo_name: str, path: str = "", token: str = None) -> List[Dict[str, Any]]:
    """
    Get contents of a directory or file in a repository.
    
    Args:
        repo_name: Repository name in format "username/repo"
        path: Path to get contents for (optional)
        token: GitHub personal access token
        
    Returns:
        List of content dictionaries or file content
    """
    g = get_github_client(token)
    
    try:
        repo = g.get_repo(repo_name)
        contents = repo.get_contents(path)
        
        if not isinstance(contents, list):
            # Single file
            return {
                'name': contents.name,
                'path': contents.path,
                'type': contents.type,
                'size': contents.size,
                'url': contents.html_url,
                'content': contents.decoded_content.decode('utf-8') if contents.encoding == 'base64' else None
            }
        
        # Directory
        result = []
        for content in contents:
            result.append({
                'name': content.name,
                'path': content.path,
                'type': content.type,
                'size': content.size,
                'url': content.html_url
            })
        return result
    finally:
        g.close() 