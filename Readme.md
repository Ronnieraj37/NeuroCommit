# AI Code Modification Agent

An AI-powered tool that automates code modifications for feature additions and bug fixes in GitHub repositories.


https://github.com/user-attachments/assets/e1819347-434d-467b-9c91-00ce86a8ff99


## Features

- Automatically implement new features in existing codebases
- Fix bugs based on descriptions
- Directly create pull requests with changes
- Supports multiple programming languages
- Runs tests to validate changes
- Understands project structure and coding patterns

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-code-agent.git
   cd ai-code-agent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your API keys:
   - Create a GitHub personal access token with repository access
   - Get a Claude API key from Anthropic
   - Add these to `config/default.json` or set as environment variables:
     ```bash
     export GITHUB_TOKEN="your_github_token"
     export CLAUDE_API_KEY="your_claude_api_key"
     ```

## Usage

### Implement a new feature

```bash
python main.py implement https://github.com/username/repo "Add a dark mode toggle to the user settings page"
```

### Fix a bug

```bash
python main.py fix https://github.com/username/repo "Fix the issue where user profile images don't load on mobile devices"
```

### Check task status

```bash
python main.py status
```

## How It Works

1. The agent forks and clones the target repository
2. It analyzes the project structure to understand the codebase
3. The AI generates a plan for implementing the feature or fixing the bug
4. The agent makes the necessary code modifications
5. Tests are run to validate the changes
6. If tests pass, a pull request is created with the changes

## Architecture

The agent uses a modular architecture with the following components:

- **Core Orchestrator**: Coordinates the entire process
- **Repository Manager**: Handles GitHub interactions and local Git operations
- **AI Connector**: Interfaces with Claude AI for code generation
- **Code Analyzer**: Understands code structure and patterns
- **Code Editor**: Makes precise code modifications
- **Test Runner**: Validates changes with existing tests

## Future Enhancements

- Support for more version control platforms (GitLab, Bitbucket)
- Integration with CI/CD pipelines
- Multimodal capabilities for understanding screenshots and diagrams
- Interactive code review mode

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.# NeuroCommit
