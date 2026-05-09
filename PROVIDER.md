# ai-contained-provider-template

A hello world provider for [AI-Contained](https://github.com/AI-Contained) demonstrating the provider architecture with a choose-your-own-adventure game.

## Using as a Template

Click **"Use this template"** on GitHub to create a new provider repo, then:

1. Rename `src/ai_contained/provider/template/` → `src/ai_contained/provider/<yourprovider>/`
2. Find-replace `template` → `<yourprovider>` in `pyproject.toml`
3. Replace the `play_adventure` tool in `__init__.py` with your own tools
4. Update the `# TODO` comments in `pyproject.toml`
5. Update `tests/test_play_adventure.py` with tests for your tools - use the existing tests as a reference for how to use `Client`, fixtures, and elicitation handlers

## Tools

- **`play_adventure`** - An interactive choose-your-own-adventure game using MCP elicitation

## Resources

- **`adventure://stats`** - Current player stats as JSON (`health`, `adventures`). Updated after each game.

## Prompts

- **`adventure_recap`** - Instructs the LLM to read `adventure://stats` and generate a dramatic story recap.
  > Note: Prompts are not currently discoverable in claude-cli but are accessible via the MCP protocol directly.

## Usage

Once connected via an MCP client (e.g. claude-cli):

1. **Play the game:** `"Play the adventure game"`
2. **Check your stats:** `"Read adventure://stats"`
3. **Get a recap:** `"Give me a recap of my adventure"`

## Installation

### Local Development

```bash
uv sync --extra dev
```

### Production

```bash
uv pip install "ai-contained-provider-template @ git+https://github.com/AI-Contained/ai-contained-provider-template.git@main"
```

## Running Tests

```bash
uv run --extra dev pytest -v
```
